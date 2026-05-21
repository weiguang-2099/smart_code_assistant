"""
Print real performance numbers used in the project README.

Run from backend-fastapi/:
    python scripts/benchmark.py

This script does not need any external service - it benchmarks the pure-Python
hot paths (tool execution, GraphRAG retrieval shape, conversation compression,
AST parsing, cache hit-rate) with everything else mocked.
"""
import asyncio
import statistics
import time
from typing import Callable, Awaitable, List
from unittest.mock import AsyncMock, MagicMock, patch

# Make sure 'app' imports work when this script is run directly.
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("SECRET_KEY", "benchmark-secret")
os.environ.setdefault("ZHIPUAI_API_KEY", "benchmark-key")
os.environ.setdefault("DATALAB_API_KEY", "benchmark-key")


REPEATS = 20  # samples per measurement
WARMUP = 3


async def _measure(name: str, coro_factory: Callable[[], Awaitable]) -> dict:
    """Run coro_factory() REPEATS times, return p50/p95/avg in ms."""
    for _ in range(WARMUP):
        await coro_factory()
    samples: List[float] = []
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        await coro_factory()
        samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    return {
        "name": name,
        "avg_ms": round(statistics.mean(samples), 2),
        "p50_ms": round(samples[len(samples) // 2], 2),
        "p95_ms": round(samples[int(len(samples) * 0.95)], 2),
        "min_ms": round(samples[0], 2),
        "max_ms": round(samples[-1], 2),
    }


def _measure_sync(name: str, fn: Callable[[], None]) -> dict:
    for _ in range(WARMUP):
        fn()
    samples: List[float] = []
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    return {
        "name": name,
        "avg_ms": round(statistics.mean(samples), 2),
        "p50_ms": round(samples[len(samples) // 2], 2),
        "p95_ms": round(samples[int(len(samples) * 0.95)], 2),
        "min_ms": round(samples[0], 2),
        "max_ms": round(samples[-1], 2),
    }


SAMPLE_PY = (
    "import os\n"
    "from typing import List\n\n"
    "class Calculator:\n"
    "    def add(self, a: int, b: int) -> int:\n"
    "        return a + b\n\n"
    "def process(values):\n"
    "    result = 0\n"
    "    for v in values:\n"
    "        if v > 0:\n"
    "            result += v\n"
    "    return result\n"
)


async def benchmark_tool_parallel():
    """Each iteration uses unique code to bypass the per-snippet cache."""
    from app.api.agent import run_tool_analysis
    counter = {"i": 0}

    async def _run():
        counter["i"] += 1
        await run_tool_analysis(SAMPLE_PY + f"\n# variant {counter['i']}\n", "python")

    return await _measure("Parallel code-analysis tools (4 tools, asyncio.gather)", _run)


async def benchmark_tool_sequential():
    """
    Baseline for the parallel-tools win: invoke the same 4 tools serially.
    No cache - each iteration uses unique code, mirroring benchmark_tool_parallel.
    """
    from app.services.code_tools import (
        analyze_code_structure,
        detect_code_smells,
        calculate_code_complexity,
        check_security_issues,
    )
    tools = [
        analyze_code_structure,
        detect_code_smells,
        calculate_code_complexity,
        check_security_issues,
    ]
    counter = {"i": 0}

    async def _run():
        counter["i"] += 1
        code = SAMPLE_PY + f"\n# seq variant {counter['i']}\n"
        for tool in tools:
            tool.invoke({"code": code, "language": "python"})

    return await _measure("Sequential code-analysis tools (4 tools, baseline)", _run)


async def benchmark_retriever():
    from app.services.code_graph.retriever import CodeGraphRetriever
    retriever = CodeGraphRetriever()
    retriever._chromadb = MagicMock()
    retriever._neo4j = MagicMock()
    retriever._chromadb.search_all = MagicMock(return_value={
        "functions": [{"id": str(i), "document": f"f{i}", "metadata": {}} for i in range(10)],
        "classes": [],
    })

    async def _run():
        with patch.object(retriever, "_get_neo4j", AsyncMock(return_value=retriever._neo4j)):
            with patch.object(retriever._neo4j, "batch_get_entity_context", AsyncMock(return_value=[])):
                await retriever.retrieve("hello", project_id=1)

    return await _measure("GraphRAG retrieval (mocked stores)", _run)


def benchmark_compression():
    from app.services.conversation_manager import ConversationManager
    mgr = ConversationManager()
    history = []
    for i in range(50):
        history.append({"role": "user", "content": f"Question {i}" * 20})
        history.append({"role": "assistant", "content": f"Answer {i}" * 50})

    return _measure_sync(
        "Conversation compression (100 messages)",
        lambda: mgr.compress_history(history),
    )


def benchmark_ast_parser():
    from app.services.code_graph.ast_parser import ASTParser
    parser = ASTParser()
    big = SAMPLE_PY * 20  # ~200 lines

    return _measure_sync(
        f"AST parsing ({len(big.splitlines())} lines of Python)",
        lambda: parser.parse(big, "python"),
    )


async def benchmark_cache_hit_throughput():
    """1000 LRU lookups per iteration - amortises sub-microsecond per-op timing."""
    from app.core.cache import CacheManager
    cache = CacheManager(l1_max_size=2000)
    for i in range(1000):
        await cache.set(f"k{i}", {"payload": "x" * 200})

    async def _run():
        for i in range(1000):
            await cache.get(f"k{i}")

    return await _measure("LRU cache: 1000 sequential GETs", _run)


async def main():
    print("=" * 70)
    print("Smart Code Assistant - performance benchmark")
    print(f"Samples per measurement: {REPEATS} (after {WARMUP} warmups)")
    print("=" * 70)

    results = []
    results.append(await benchmark_tool_sequential())
    results.append(await benchmark_tool_parallel())
    results.append(await benchmark_retriever())
    results.append(benchmark_compression())
    results.append(benchmark_ast_parser())
    results.append(await benchmark_cache_hit_throughput())

    print()
    print(f"{'Benchmark':<55} {'avg':>8} {'p50':>8} {'p95':>8}")
    print(f"{'-' * 55} {'-' * 8} {'-' * 8} {'-' * 8}")
    for r in results:
        print(
            f"{r['name']:<55} "
            f"{r['avg_ms']:>6.2f}ms {r['p50_ms']:>6.2f}ms {r['p95_ms']:>6.2f}ms"
        )
    print()


if __name__ == "__main__":
    asyncio.run(main())
