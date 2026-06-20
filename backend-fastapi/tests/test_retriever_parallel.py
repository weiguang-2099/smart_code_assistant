"""Tests for the retriever graph branch (seeded from semantic hits)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def _func_hit(name, module_path, score):
    return {"metadata": {"name": name, "module_path": module_path,
                         "class_name": None, "type": "function"},
            "relevance_score": score}


class TestGraphSeededFromSemantic:
    @pytest.mark.asyncio
    async def test_graph_traversal_seeds_from_top_semantic_hits(self):
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()
        retriever._chromadb.search_all = MagicMock(return_value={
            "functions": [_func_hit("retrieve", "app/r.py", 0.9)],
            "classes": [],
        })
        captured = {}

        async def fake_neighbors(seeds, max_depth=2, limit=20):
            captured["seeds"] = seeds
            return [{"name": "do_work", "module_path": "app/a.py",
                     "relation": "callee", "source": "retrieve"}]

        with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
            with patch.object(retriever._neo4j, 'get_entity_neighbors', fake_neighbors):
                result = await retriever.retrieve(query="how does retrieval work",
                                                  project_id=1, include_graph_context=True)

        assert captured["seeds"][0]["name"] == "retrieve"
        assert captured["seeds"][0]["module_path"] == "app/r.py"
        assert result["graph_context"][0]["name"] == "do_work"

    @pytest.mark.asyncio
    async def test_graph_failure_keeps_semantic(self):
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._chromadb.search_all = MagicMock(return_value={
            "functions": [_func_hit("f", "m.py", 0.5)], "classes": []})
        with patch.object(retriever, '_get_neo4j', AsyncMock(side_effect=Exception("neo4j down"))):
            result = await retriever.retrieve(query="x", project_id=1, include_graph_context=True)
        assert result["semantic_results"] is not None
        assert result["graph_context"] is None

    @pytest.mark.asyncio
    async def test_semantic_failure_yields_empty_seeds(self):
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()
        retriever._chromadb.search_all = MagicMock(side_effect=Exception("chroma down"))
        seen = {}

        async def fake_neighbors(seeds, max_depth=2, limit=20):
            seen["seeds"] = seeds
            return []

        with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
            with patch.object(retriever._neo4j, 'get_entity_neighbors', fake_neighbors):
                result = await retriever.retrieve(query="x", project_id=1, include_graph_context=True)
        assert seen["seeds"] == []
        assert result["graph_context"] == []

    @pytest.mark.asyncio
    async def test_without_graph_context_skips_neo4j(self):
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._chromadb.search_all = MagicMock(return_value={"functions": [], "classes": []})
        with patch.object(retriever, '_get_neo4j', AsyncMock()) as mock_get_neo4j:
            result = await retriever.retrieve(query="x", project_id=1, include_graph_context=False)
        assert result["graph_context"] is None
        mock_get_neo4j.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_combined_context_string(self):
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()
        retriever._chromadb.search_all = MagicMock(return_value={
            "functions": [_func_hit("f", "m.py", 0.5)], "classes": []})
        with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
            with patch.object(retriever._neo4j, 'get_entity_neighbors',
                              AsyncMock(return_value=[{"name": "Helper", "module_path": "m.py",
                                                       "relation": "import", "source": "f"}])):
                result = await retriever.retrieve(query="x", project_id=1, include_graph_context=True)
        assert isinstance(result["combined_context"], str)
        assert "Helper" in result["combined_context"]
