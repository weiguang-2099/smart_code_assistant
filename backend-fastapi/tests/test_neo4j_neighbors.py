"""Unit tests for Neo4jClient.get_entity_neighbors (execute_query mocked)."""
from unittest.mock import AsyncMock

import pytest

from app.services.code_graph.neo4j_client import Neo4jClient


def _fake_execute_factory(rows_by_marker):
    async def fake_execute(query, params=None):
        for marker, rows in rows_by_marker.items():
            if marker in query:
                return rows
        return []
    return fake_execute


@pytest.mark.asyncio
async def test_function_seed_returns_callees_callers_and_imports():
    client = Neo4jClient()
    client.execute_query = _fake_execute_factory({
        "->(callee:Function)": [{"name": "do_work", "module_path": "app/a.py"}],
        "(caller:Function)-": [{"name": "handler", "module_path": "app/b.py"}],
        "HAS_IMPORT": [{"names": ["Neo4jClient", "ChromaDBClient"]}],
    })
    seeds = [{"name": "retrieve", "module_path": "app/r.py", "class_name": None,
              "type": "function", "relevance_score": 0.9}]
    out = await client.get_entity_neighbors(seeds, max_depth=2, limit=20)
    names = {r["name"] for r in out}
    assert {"do_work", "handler", "Neo4jClient", "ChromaDBClient"} <= names
    relations = {r["name"]: r["relation"] for r in out}
    assert relations["do_work"] == "callee"
    assert relations["handler"] == "caller"
    assert relations["Neo4jClient"] == "import"


@pytest.mark.asyncio
async def test_class_seed_returns_methods_and_parents():
    client = Neo4jClient()
    client.execute_query = _fake_execute_factory({
        "HAS_METHOD": [{"name": "build", "module_path": "app/g.py"}],
        "->(p:Class)": [{"name": "BaseBuilder", "module_path": "app/base.py"}],
        "HAS_IMPORT": [{"names": ["CodeEntityExtractor"]}],
    })
    seeds = [{"name": "CodeGraphBuilder", "module_path": "app/g.py", "class_name": None,
              "type": "class", "relevance_score": 0.8}]
    out = await client.get_entity_neighbors(seeds, max_depth=2, limit=20)
    relations = {r["name"]: r["relation"] for r in out}
    assert relations.get("build") == "method"
    assert relations.get("BaseBuilder") == "parent"
    assert relations.get("CodeEntityExtractor") == "import"


@pytest.mark.asyncio
async def test_dedup_keeps_first_and_cap_respected():
    client = Neo4jClient()
    client.execute_query = _fake_execute_factory({
        "->(callee:Function)": [{"name": "dup", "module_path": "app/a.py"}],
        "(caller:Function)-": [],
        "HAS_IMPORT": [{"names": ["dup", "x1", "x2", "x3"]}],
    })
    seeds = [{"name": "f", "module_path": "app/a.py", "class_name": None,
              "type": "function", "relevance_score": 0.5}]
    out = await client.get_entity_neighbors(seeds, max_depth=2, limit=3)
    names = [r["name"] for r in out]
    assert len(out) == 3
    assert names.count("dup") == 1
    kept = next(r for r in out if r["name"] == "dup")
    assert kept["relation"] == "callee"


@pytest.mark.asyncio
async def test_higher_relevance_seed_ranked_first():
    client = Neo4jClient()
    async def fake_execute(query, params=None):
        if "->(callee:Function)" in query:
            return [{"name": f"callee_of_{params['name']}", "module_path": "m"}]
        return []
    client.execute_query = fake_execute
    seeds = [
        {"name": "low", "module_path": "m", "class_name": None, "type": "function", "relevance_score": 0.1},
        {"name": "high", "module_path": "m", "class_name": None, "type": "function", "relevance_score": 0.9},
    ]
    out = await client.get_entity_neighbors(seeds, max_depth=1, limit=10)
    assert out[0]["name"] == "callee_of_high"
