"""Async per-case retrieve loop. Calls CodeGraphRetriever directly (not HTTP)."""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from evals.config import (
    DEFAULT_CONCURRENCY,
    DEFAULT_PER_CASE_TIMEOUT_S,
    EVAL_PROJECT_ID,
    K_VALUES,
)

logger = logging.getLogger(__name__)


@dataclass
class CaseResult:
    id: str
    category: str
    expected_files: list[str]
    expected_graph_neighbors: Optional[list[str]]
    retrieved_files_ranked: list[str] = field(default_factory=list)
    retrieved_graph_neighbors: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


def load_golden_set(path: Path) -> list[dict]:
    """Read a JSONL file, skip blank lines, return list of case dicts."""
    cases: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def _flatten_semantic_results(semantic_results) -> list[dict]:
    """search_all() returns {"functions": [...], "classes": [...]}; merge the
    per-collection lists into one ranking by relevance_score (descending,
    chromadb_client.py:239 — higher is better). Flat lists (unit fixtures and
    any future pre-merged source) pass through with non-dict items dropped."""
    if not semantic_results:
        return []
    if isinstance(semantic_results, dict):
        merged = []
        for chunks in semantic_results.values():
            if isinstance(chunks, list):
                merged.extend(c for c in chunks if isinstance(c, dict))
        merged.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)
        return merged
    return [c for c in semantic_results if isinstance(c, dict)]


def extract_files_from_retrieval(semantic_results) -> list[str]:
    """Extract chunk file paths in rank order.

    Accepts either search_all()'s dict shape (merged by relevance_score via
    _flatten_semantic_results) or a pre-flattened chunk list.

    Per TBD #1 (resolved Section 16 of the v1 spec): each chunk stores its
    path under ``metadata.module_path``. The storage layer applies no
    normalization — the harness strips a leading ``backend-fastapi/`` so
    paths line up with golden cases' ``app/...`` convention.
    """
    files: list[str] = []
    for chunk in _flatten_semantic_results(semantic_results):
        metadata = chunk.get("metadata") or {}
        module_path = metadata.get("module_path")
        if not module_path:
            continue
        if module_path.startswith("backend-fastapi/"):
            module_path = module_path[len("backend-fastapi/"):]
        files.append(module_path)
    return files


def extract_neighbors_from_graph(graph_context: Optional[dict]) -> list[str]:
    """Extract neighbor node identifiers from graph_context.

    Per TBD #3 (resolved): entity entries store the identifier under ``name``;
    call-count summary entries store it under ``entity``. Both keys must be
    collected for full coverage. Identifiers are bare unqualified strings
    (e.g., ``"CodeGraphRetriever"``, NOT ``"app.services.code_graph.retriever.CodeGraphRetriever"``).

    The exact shape of ``graph_context`` is determined by ``retriever.py``;
    when implementing, open retriever.py and confirm the iteration shape before
    finalizing the walker. The defensive recursive walk below handles list/dict
    nesting without making strong shape assumptions.
    """
    if not graph_context:
        return []
    neighbors: list[str] = []
    seen: set[str] = set()

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            for key in ("name", "entity"):
                value = obj.get(key)
                if isinstance(value, str) and value and value not in seen:
                    seen.add(value)
                    neighbors.append(value)
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(graph_context)
    return neighbors


def _compute_case_metrics(
    retrieved_files: list[str],
    retrieved_neighbors: list[str],
    expected_files: list[str],
    expected_neighbors: Optional[list[str]],
) -> dict[str, Any]:
    from evals.metrics.retrieval import (
        hit_rate_at_k,
        precision_at_k,
        recall_at_k,
        mrr,
    )
    from evals.metrics.graph import (
        graph_neighbor_recall,
        graph_neighbor_precision,
        graph_traversal_correctness,
        hybrid_hit_rate_at_k,
    )

    metrics: dict[str, Any] = {}
    for k in K_VALUES:
        metrics[f"hit_rate@{k}"] = hit_rate_at_k(retrieved_files, expected_files, k)
        metrics[f"recall@{k}"] = recall_at_k(retrieved_files, expected_files, k)
        metrics[f"precision@{k}"] = precision_at_k(retrieved_files, expected_files, k)
        metrics[f"hybrid_hit_rate@{k}"] = hybrid_hit_rate_at_k(
            retrieved_files, expected_files,
            retrieved_neighbors, expected_neighbors, k,
        )
    metrics["mrr"] = mrr(retrieved_files, expected_files)
    metrics["graph_neighbor_recall"] = graph_neighbor_recall(
        set(retrieved_neighbors), expected_neighbors
    )
    metrics["graph_neighbor_precision"] = graph_neighbor_precision(
        set(retrieved_neighbors), expected_neighbors
    )
    metrics["graph_traversal_correctness"] = graph_traversal_correctness(
        set(retrieved_neighbors), expected_neighbors
    )
    return metrics


async def run_one_case(
    case: dict,
    retriever,
    *,
    top_k: int,
    max_depth: int,
    project_id: int,
    timeout_s: float,
) -> CaseResult:
    expected_files = case["expected_files"]
    expected_neighbors = case.get("expected_graph_neighbors")

    try:
        raw = await asyncio.wait_for(
            retriever.retrieve(
                query=case["question"],
                project_id=project_id,
                top_k=top_k,
                include_graph_context=True,
                max_depth=max_depth,
            ),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        return CaseResult(
            id=case["id"], category=case["category"],
            expected_files=expected_files,
            expected_graph_neighbors=expected_neighbors,
            error="timeout",
        )
    except Exception as exc:
        return CaseResult(
            id=case["id"], category=case["category"],
            expected_files=expected_files,
            expected_graph_neighbors=expected_neighbors,
            error=f"{type(exc).__name__}: {exc}",
        )

    retrieved_files = extract_files_from_retrieval(raw.get("semantic_results", []))
    retrieved_neighbors = extract_neighbors_from_graph(raw.get("graph_context"))
    metrics = _compute_case_metrics(
        retrieved_files, retrieved_neighbors, expected_files, expected_neighbors
    )
    return CaseResult(
        id=case["id"], category=case["category"],
        expected_files=expected_files,
        expected_graph_neighbors=expected_neighbors,
        retrieved_files_ranked=retrieved_files,
        retrieved_graph_neighbors=retrieved_neighbors,
        metrics=metrics,
    )


async def run_corpus(
    cases: list[dict],
    retriever,
    *,
    top_k: int = 10,
    max_depth: int = 2,
    project_id: int = EVAL_PROJECT_ID,
    concurrency: int = DEFAULT_CONCURRENCY,
    timeout_s: float = DEFAULT_PER_CASE_TIMEOUT_S,
) -> list[CaseResult]:
    """Run every case in ``cases`` against ``retriever`` with bounded concurrency."""
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(case: dict) -> CaseResult:
        async with semaphore:
            return await run_one_case(
                case, retriever,
                top_k=top_k, max_depth=max_depth,
                project_id=project_id, timeout_s=timeout_s,
            )

    return await asyncio.gather(*(bounded(c) for c in cases))
