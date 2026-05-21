"""
Tests for the code knowledge graph builder.

Neo4j and ChromaDB clients are mocked so these stay unit-level.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.code_graph.graph_builder import CodeGraphBuilder, get_graph_builder


@pytest.fixture
def mock_neo4j():
    """Mock async Neo4j client with the methods the builder calls."""
    m = MagicMock()
    m.create_project = AsyncMock()
    m.clear_module_graph = AsyncMock()
    m.create_module = AsyncMock()
    m.create_class = AsyncMock()
    m.create_function = AsyncMock()
    m.create_import = AsyncMock()
    m.create_call_relationship = AsyncMock()
    m.create_inheritance_relationship = AsyncMock()
    m.get_graph_stats = AsyncMock(return_value={"nodes": 0, "relationships": 0})
    m.clear_project_graph = AsyncMock()
    return m


@pytest.fixture
def mock_chroma():
    """Mock ChromaDB client."""
    c = MagicMock()
    c.index_functions = MagicMock()
    c.index_classes = MagicMock()
    c.get_collection_stats = MagicMock(return_value={"vectors": 0})
    c.delete_project_collections = MagicMock()
    return c


@pytest.fixture
def builder(mock_neo4j, mock_chroma):
    b = CodeGraphBuilder(neo4j_client=mock_neo4j, chromadb_client=mock_chroma)
    return b


SAMPLE = (
    "import os\n"
    "from typing import List\n\n"
    "class Foo(Base):\n"
    "    def m(self):\n"
    "        helper()\n\n"
    "def top():\n"
    "    return Foo()\n"
)


class TestBuildFromCode:
    @pytest.mark.asyncio
    async def test_builds_creates_module_and_returns_counts(self, builder, mock_neo4j):
        result = await builder.build_from_code(SAMPLE, "python", project_id=1, module_path="m.py")
        assert result["success"] is True
        mock_neo4j.create_module.assert_awaited()
        mock_neo4j.create_class.assert_awaited()
        mock_neo4j.create_function.assert_awaited()
        mock_neo4j.create_import.assert_awaited()
        assert result["entities"]["classes"] == 1
        assert result["entities"]["functions"] == 2

    @pytest.mark.asyncio
    async def test_invalid_code_returns_error_block(self, builder):
        result = await builder.build_from_code("def broken(:::", "python", module_path="bad.py")
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_neo4j_failure_returns_unsuccess(self, builder, mock_neo4j):
        mock_neo4j.create_module = AsyncMock(side_effect=RuntimeError("neo4j down"))
        result = await builder.build_from_code(SAMPLE, "python", module_path="m.py")
        assert result["success"] is False
        assert "neo4j down" in result["error"]

    @pytest.mark.asyncio
    async def test_chroma_failure_does_not_break_build(self, builder, mock_chroma, mock_neo4j):
        mock_chroma.index_functions = MagicMock(side_effect=RuntimeError("chroma down"))
        result = await builder.build_from_code(SAMPLE, "python", project_id=1, module_path="m.py")
        # Neo4j writes succeeded; build result should still be successful.
        assert result["success"] is True
        # vector_indexed should be 0 because the chroma error was swallowed.
        assert result["stats"].get("vector_indexed", 0) == 0


class TestBuildFromFiles:
    @pytest.mark.asyncio
    async def test_aggregates_stats_across_files(self, builder):
        files = [
            {"path": "a.py", "content": "def f(): pass", "language": "python"},
            {"path": "b.py", "content": "def g(): pass", "language": "python"},
        ]
        result = await builder.build_from_files(files, project_id=1)
        assert result["success"] is True
        assert result["stats"]["files_processed"] == 2
        assert result["stats"]["functions_created"] == 2

    @pytest.mark.asyncio
    async def test_file_with_error_records_failure(self, builder):
        files = [
            {"path": "bad.py", "content": "def broken(:::", "language": "python"},
            {"path": "ok.py", "content": "def f(): pass", "language": "python"},
        ]
        result = await builder.build_from_files(files, project_id=1)
        assert result["success"] is False
        assert len(result["stats"]["errors"]) == 1
        assert result["stats"]["files_processed"] == 1


class TestStatsAndClear:
    @pytest.mark.asyncio
    async def test_get_graph_statistics_with_project(self, builder, mock_neo4j, mock_chroma):
        stats = await builder.get_graph_statistics(project_id=1)
        mock_neo4j.get_graph_stats.assert_awaited_once()
        mock_chroma.get_collection_stats.assert_called_once()
        # merged dict has both 'nodes' and 'vectors'
        assert "nodes" in stats and "vectors" in stats

    @pytest.mark.asyncio
    async def test_get_graph_statistics_without_project(self, builder, mock_neo4j, mock_chroma):
        await builder.get_graph_statistics(project_id=None)
        mock_neo4j.get_graph_stats.assert_awaited_once()
        mock_chroma.get_collection_stats.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_graph_calls_both_backends(self, builder, mock_neo4j, mock_chroma):
        await builder.clear_graph(7)
        mock_neo4j.clear_project_graph.assert_awaited_once_with(7)
        mock_chroma.delete_project_collections.assert_called_once_with(7)


class TestSingleton:
    def test_get_graph_builder_is_idempotent(self):
        a = get_graph_builder()
        b = get_graph_builder()
        assert a is b
