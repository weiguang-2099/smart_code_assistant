"""Tests for parallel retriever operations"""
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock


class TestParallelRetriever:
    """Test parallel retrieval execution"""

    @pytest.mark.asyncio
    async def test_retrieve_runs_semantic_and_graph_in_parallel(self):
        """Semantic and graph queries should run concurrently"""
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()

        # Mock methods with artificial delay
        def slow_search(*args, **kwargs):
            time.sleep(0.1)
            return {"functions": [], "classes": []}

        async def slow_graph(*args, **kwargs):
            time.sleep(0.1)
            return []

        retriever._chromadb.search_all = slow_search

        with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
            with patch.object(retriever._neo4j, 'batch_get_entity_context', slow_graph):
                start = time.time()
                await retriever.retrieve(
                    query="test function",
                    project_id=1,
                    include_graph_context=True
                )
                elapsed = time.time() - start

                # If parallel, should be ~0.1s, not ~0.2s
                assert elapsed < 0.25, f"Retrieval took {elapsed}s, expected < 0.25s"

    @pytest.mark.asyncio
    async def test_retrieve_handles_semantic_failure_gracefully(self):
        """Should still return graph results if semantic search fails"""
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()

        retriever._chromadb.search_all = MagicMock(side_effect=Exception("ChromaDB error"))

        with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
            with patch.object(retriever._neo4j, 'batch_get_entity_context', AsyncMock(return_value=[{"entity": "test"}])):
                result = await retriever.retrieve(
                    query="test",
                    project_id=1,
                    include_graph_context=True
                )

                # Should have graph results even if semantic failed
                assert result.get("graph_context") is not None

    @pytest.mark.asyncio
    async def test_retrieve_handles_graph_failure_gracefully(self):
        """Should still return semantic results if graph traversal fails"""
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()

        retriever._chromadb.search_all = MagicMock(return_value={"functions": [{"name": "test_func"}], "classes": []})

        with patch.object(retriever, '_get_neo4j', AsyncMock(side_effect=Exception("Neo4j error"))):
            result = await retriever.retrieve(
                query="test",
                project_id=1,
                include_graph_context=True
            )

            # Should have semantic results even if graph failed
            assert result.get("semantic_results") is not None

    @pytest.mark.asyncio
    async def test_retrieve_without_graph_context(self):
        """Should skip graph traversal when disabled"""
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._chromadb.search_all = MagicMock(return_value={"functions": [], "classes": []})

        with patch.object(retriever, '_get_neo4j', AsyncMock()) as mock_get_neo4j:
            result = await retriever.retrieve(
                query="test",
                project_id=1,
                include_graph_context=False
            )

            # Graph context should be None when disabled
            assert result.get("graph_context") is None
            # Neo4j should not be called when graph context is disabled
            mock_get_neo4j.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_without_project_id_skips_semantic(self):
        """Should skip semantic search when project_id is None"""
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()

        retriever._chromadb.search_all = MagicMock(side_effect=Exception("Should not be called"))

        with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
            with patch.object(retriever._neo4j, 'batch_get_entity_context', AsyncMock(return_value=[])):
                result = await retriever.retrieve(
                    query="test",
                    project_id=None,
                    include_graph_context=True
                )

                # Semantic results should be empty when project_id is None
                assert result.get("semantic_results") == {}

    @pytest.mark.asyncio
    async def test_retrieve_returns_combined_context(self):
        """Should return combined context string"""
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()

        retriever._chromadb.search_all = MagicMock(return_value={
            "functions": [{"metadata": {"name": "test_func", "module_path": "test.py"}}],
            "classes": []
        })

        with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
            with patch.object(retriever._neo4j, 'batch_get_entity_context', AsyncMock(return_value=[
                {"name": "TestClass", "module_path": "test.py"}
            ])):
                result = await retriever.retrieve(
                    query="test",
                    project_id=1,
                    include_graph_context=True
                )

                # Combined context should be built
                assert "combined_context" in result
                assert isinstance(result["combined_context"], str)
