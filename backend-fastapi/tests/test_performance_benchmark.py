"""
Performance benchmark tests

Run with: pytest tests/test_performance_benchmark.py -v
"""
import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


class TestPerformanceBenchmarks:
    """Benchmark tests for performance optimization verification"""

    @pytest.mark.asyncio
    async def test_tool_analysis_parallel_performance(self):
        """Benchmark parallel tool analysis"""
        from app.api.agent import run_tool_analysis

        code = """
def calculate_sum(numbers):
    total = 0
    for n in numbers:
        total += n
    return total
"""

        # Warmup run
        await run_tool_analysis(code, "python")

        # Benchmark
        start = time.time()
        result = await run_tool_analysis(code, "python")
        elapsed = time.time() - start

        # Verify all tools returned results
        assert "analyze_code_structure" in result
        assert "detect_code_smells" in result

        # Should complete in less than 1.5 seconds
        assert elapsed < 1.5, f"Tool analysis took {elapsed:.2f}s, expected < 1.5s"

    @pytest.mark.asyncio
    async def test_retriever_parallel_performance(self):
        """Benchmark parallel GraphRAG retrieval"""
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()

        retriever._chromadb.search_all = MagicMock(return_value={
            "functions": [{"id": "1", "document": "test", "metadata": {}}],
            "classes": []
        })

        async def run_retrieve():
            with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
                with patch.object(retriever._neo4j, 'batch_get_entity_context', AsyncMock(return_value=[])):
                    return await retriever.retrieve("test query", project_id=1)

        # Warmup
        await run_retrieve()

        # Benchmark
        start = time.time()
        result = await run_retrieve()
        elapsed = time.time() - start

        assert result["query"] == "test query"
        # Should be fast due to mocking
        assert elapsed < 1.0, f"Retrieval took {elapsed:.2f}s"

    def test_conversation_compression_performance(self):
        """Benchmark conversation compression"""
        from app.services.conversation_manager import ConversationManager

        manager = ConversationManager()

        # Create large history
        history = []
        for i in range(50):
            history.append({"role": "user", "content": f"Question {i}" * 20})
            history.append({"role": "assistant", "content": f"Answer {i}" * 50})

        # Benchmark
        start = time.time()
        result = manager.compress_history(history)
        elapsed = time.time() - start

        # Should be compressed to max_turns
        assert len(result) <= 20

        # Should be very fast
        assert elapsed < 0.1, f"Compression took {elapsed:.3f}s, expected < 0.1s"


class TestLatencyRequirements:
    """Verify latency requirements are met"""

    @pytest.mark.asyncio
    async def test_tool_analysis_latency_under_1_5s(self):
        """Tool analysis should complete under 1.5s"""
        from app.api.agent import run_tool_analysis

        code = "def test():\n    pass"

        start = time.time()
        await run_tool_analysis(code, "python")
        elapsed = time.time() - start

        assert elapsed < 1.5, f"Tool analysis took {elapsed:.2f}s, expected < 1.5s"

    def test_conversation_compression_latency_under_100ms(self):
        """Compression should be fast"""
        from app.services.conversation_manager import ConversationManager

        manager = ConversationManager()
        history = [{"role": "user", "content": f"Message {i}"} for i in range(100)]

        start = time.time()
        manager.compress_history(history)
        elapsed = time.time() - start

        assert elapsed < 0.1, f"Compression took {elapsed:.3f}s, expected < 0.1s"

    def test_token_estimation_is_fast(self):
        """Token estimation should be fast"""
        from app.services.conversation_manager import ConversationManager

        manager = ConversationManager()
        history = [{"role": "user", "content": "x" * 1000} for _ in range(100)]

        start = time.time()
        tokens = manager.estimate_tokens(history)
        elapsed = time.time() - start

        assert tokens > 0
        assert elapsed < 0.01, f"Token estimation took {elapsed:.4f}s"
