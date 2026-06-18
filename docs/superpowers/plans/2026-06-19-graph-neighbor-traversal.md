# Graph-Neighbor Traversal (Phase 2a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the regex-driven graph branch of `CodeGraphRetriever.retrieve` with real neighbor traversal seeded from semantic-search hits, and store imported symbol names so import neighbors are reachable.

**Architecture:** Semantic search runs first; its top-N hits (mapped by `{name, module_path, class_name, type}` to graph nodes) seed a new `Neo4jClient.get_entity_neighbors` that returns callers/callees/methods/inheritance/imported-symbol neighbors as bare names. Indexing is extended to persist `ImportEntity.names` on `Import` nodes.

**Tech Stack:** Python 3.11, FastAPI, Neo4j (bolt), ChromaDB, pytest / pytest-asyncio. Backend tests run from `backend-fastapi/` via `venv\Scripts\python.exe -m pytest tests/ -q --no-cov`. Eval suite from repo root via `backend-fastapi\venv\Scripts\python.exe -m pytest evals/tests/ -q`.

**Spec:** `docs/superpowers/specs/2026-06-19-graph-neighbor-traversal-design.md`

---

## File Structure

- `backend-fastapi/app/services/code_graph/neo4j_client.py` — add `names` to `create_import`; add `get_entity_neighbors`.
- `backend-fastapi/app/services/code_graph/graph_builder.py` — pass `imp.names` to `create_import`.
- `backend-fastapi/app/services/code_graph/retriever.py` — add `GRAPH_SEED_COUNT`, `_seed_entities_from_semantic`; rewire `retrieve` graph branch to be sequential and seed from semantic hits; remove `_extract_entity_names` if unused; update `_build_combined_context` graph rendering.
- `backend-fastapi/tests/test_graph_builder.py` — assert `create_import` receives `names`.
- `backend-fastapi/tests/test_neo4j_neighbors.py` (new) — unit tests for `get_entity_neighbors`.
- `backend-fastapi/tests/test_retriever_parallel.py` — replace parallelism test; update graph-branch tests to the sequential, seed-from-semantic behavior.
- `evals/tests/test_runner_extract.py` — add a case for the new flat `graph_context` shape.
- `README.md` — Evaluation section before/after + known limitations.

---

## Task 1: Persist imported symbol names on Import nodes

**Files:**
- Modify: `backend-fastapi/app/services/code_graph/neo4j_client.py` (`create_import`)
- Modify: `backend-fastapi/app/services/code_graph/graph_builder.py` (import loop)
- Test: `backend-fastapi/tests/test_graph_builder.py`

- [ ] **Step 1: Write the failing test**

Add to `backend-fastapi/tests/test_graph_builder.py` inside `class TestBuildFromCode`:

```python
    @pytest.mark.asyncio
    async def test_import_names_passed_to_create_import(self, builder, mock_neo4j):
        # SAMPLE has "from typing import List" -> names ["List"], "import os" -> names []
        await builder.build_from_code(SAMPLE, "python", project_id=1, module_path="m.py")
        calls = mock_neo4j.create_import.await_args_list
        names_by_module = {c.kwargs["import_module"]: c.kwargs.get("names") for c in calls}
        assert names_by_module.get("typing") == ["List"]
        assert names_by_module.get("os") == []
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend-fastapi && venv\Scripts\python.exe -m pytest tests/test_graph_builder.py::TestBuildFromCode::test_import_names_passed_to_create_import -v --no-cov`
Expected: FAIL — `create_import` is called without `names` (KeyError / None), or the kwarg is absent.

- [ ] **Step 3: Pass `names` from the builder**

In `backend-fastapi/app/services/code_graph/graph_builder.py`, the import loop currently reads:

```python
            for imp in parse_result.imports:
                await neo4j.create_import(
                    module_path=module_path,
                    import_module=imp.module,
                    alias=imp.alias
                )
                stats["imports_created"] += 1
```

Change the call to also pass `names`:

```python
            for imp in parse_result.imports:
                await neo4j.create_import(
                    module_path=module_path,
                    import_module=imp.module,
                    alias=imp.alias,
                    names=imp.names,
                )
                stats["imports_created"] += 1
```

- [ ] **Step 4: Store `names` on the Import node**

In `backend-fastapi/app/services/code_graph/neo4j_client.py`, replace `create_import` with:

```python
    async def create_import(
        self,
        module_path: str,
        import_module: str,
        alias: Optional[str] = None,
        names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """创建导入节点"""
        # Neo4j refuses MERGE on a null property; imports without an alias
        # (the common case) merge on an empty-string alias instead so that
        # ``import os`` and ``import os as o`` remain distinct nodes.
        # ``names`` are the symbols of ``from X import a, b`` and are stored so
        # the retriever can surface imported symbols as graph neighbors.
        query = """
        MERGE (i:Import {module: $import_module, alias: $alias, module_path: $module_path})
        SET i.names = $names
        WITH i
        MERGE (m:Module {path: $module_path})
        MERGE (m)-[:HAS_IMPORT]->(i)
        RETURN i
        """
        result = await self.execute_query(query, {
            "module_path": module_path,
            "import_module": import_module,
            "alias": alias or "",
            "names": names or [],
        })
        return result[0] if result else None
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend-fastapi && venv\Scripts\python.exe -m pytest tests/test_graph_builder.py -v --no-cov`
Expected: PASS (all builder tests, including the new one).

- [ ] **Step 6: Live probe (real Neo4j) to confirm the Cypher stores and returns names**

Requires Docker services up. Run from `backend-fastapi/`:

```bash
venv/Scripts/python.exe -c "import asyncio; from app.services.code_graph.neo4j_client import Neo4jClient
async def main():
    c = Neo4jClient(); await c.connect()
    await c.create_import(module_path='app/probe.py', import_module='typing', alias=None, names=['List','Dict'])
    rows = await c.execute_query('MATCH (m:Module {path:\"app/probe.py\"})-[:HAS_IMPORT]->(i:Import) RETURN i.names AS names', {})
    print('stored names:', rows)
    await c.execute_query('MATCH (n) WHERE n.path=\"app/probe.py\" OR n.module_path=\"app/probe.py\" DETACH DELETE n', {})
asyncio.run(main())"
```

Expected: `stored names: [{'names': ['List', 'Dict']}]`

- [ ] **Step 7: Commit**

```bash
git add backend-fastapi/app/services/code_graph/neo4j_client.py backend-fastapi/app/services/code_graph/graph_builder.py backend-fastapi/tests/test_graph_builder.py
git commit -m "feat(graph): persist imported symbol names on Import nodes"
```

---

## Task 2: `get_entity_neighbors` traversal method

**Files:**
- Modify: `backend-fastapi/app/services/code_graph/neo4j_client.py` (add method)
- Test: `backend-fastapi/tests/test_neo4j_neighbors.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `backend-fastapi/tests/test_neo4j_neighbors.py`:

```python
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
    # Same name surfaced as both callee and import; importer-supplied dup names.
    client.execute_query = _fake_execute_factory({
        "->(callee:Function)": [{"name": "dup", "module_path": "app/a.py"}],
        "(caller:Function)-": [],
        "HAS_IMPORT": [{"names": ["dup", "x1", "x2", "x3"]}],
    })
    seeds = [{"name": "f", "module_path": "app/a.py", "class_name": None,
              "type": "function", "relevance_score": 0.5}]
    out = await client.get_entity_neighbors(seeds, max_depth=2, limit=3)
    names = [r["name"] for r in out]
    assert len(out) == 3                 # cap respected
    assert names.count("dup") == 1       # deduped
    # callee has higher relation priority than import, so the kept "dup" is the callee
    kept = next(r for r in out if r["name"] == "dup")
    assert kept["relation"] == "callee"


@pytest.mark.asyncio
async def test_higher_relevance_seed_ranked_first():
    client = Neo4jClient()
    async def fake_execute(query, params=None):
        if "->(callee:Function)" in query:
            # return a callee named after the seed so we can tell them apart
            return [{"name": f"callee_of_{params['name']}", "module_path": "m"}]
        return []
    client.execute_query = fake_execute
    seeds = [
        {"name": "low", "module_path": "m", "class_name": None, "type": "function", "relevance_score": 0.1},
        {"name": "high", "module_path": "m", "class_name": None, "type": "function", "relevance_score": 0.9},
    ]
    out = await client.get_entity_neighbors(seeds, max_depth=1, limit=10)
    assert out[0]["name"] == "callee_of_high"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend-fastapi && venv\Scripts\python.exe -m pytest tests/test_neo4j_neighbors.py -v --no-cov`
Expected: FAIL — `Neo4jClient` has no attribute `get_entity_neighbors`.

- [ ] **Step 3: Implement `get_entity_neighbors`**

In `backend-fastapi/app/services/code_graph/neo4j_client.py`, add this method (place it after `batch_get_entity_context`). Note: Neo4j cannot parameterize a variable-length path bound, so `max_depth` is interpolated into the query string the same way `get_impact_analysis` already does; `max_depth` is an int from config, never user input.

```python
    async def get_entity_neighbors(
        self,
        seeds: List[Dict[str, Any]],
        max_depth: int = 2,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return real graph neighbors of semantic-hit seed entities.

        ``seeds`` are descriptors {name, module_path, class_name, type,
        relevance_score} taken from the top semantic hits. Returns flat records
        {name, module_path, relation, source} where ``relation`` is one of
        callee/caller/method/parent/child/import. Results are deduped by name,
        ranked by the seeding hit's relevance_score (then relation priority),
        and capped at ``limit``.
        """
        relation_priority = {
            "callee": 0, "caller": 1, "import": 2,
            "method": 3, "parent": 4, "child": 5,
        }
        candidates: List[tuple] = []  # (score, priority, record)

        def add(score, relation, name, module_path, source):
            if not name:
                return
            candidates.append((
                score, relation_priority[relation],
                {"name": name, "module_path": module_path,
                 "relation": relation, "source": source},
            ))

        for seed in seeds:
            name = seed.get("name")
            module_path = seed.get("module_path")
            stype = seed.get("type")
            score = seed.get("relevance_score") or 0.0
            if not name:
                continue

            try:
                if stype == "function":
                    callees = await self.execute_query(
                        f"""
                        MATCH (f:Function {{name: $name, module_path: $module_path}})
                              -[:CALLS*1..{max_depth}]->(callee:Function)
                        RETURN DISTINCT callee.name AS name, callee.module_path AS module_path
                        """,
                        {"name": name, "module_path": module_path},
                    )
                    for r in callees:
                        add(score, "callee", r.get("name"), r.get("module_path"), name)

                    callers = await self.execute_query(
                        f"""
                        MATCH (caller:Function)-[:CALLS*1..{max_depth}]->
                              (f:Function {{name: $name, module_path: $module_path}})
                        RETURN DISTINCT caller.name AS name, caller.module_path AS module_path
                        """,
                        {"name": name, "module_path": module_path},
                    )
                    for r in callers:
                        add(score, "caller", r.get("name"), r.get("module_path"), name)

                elif stype == "class":
                    methods = await self.execute_query(
                        """
                        MATCH (c:Class {name: $name, module_path: $module_path})-[:HAS_METHOD]->(m:Function)
                        RETURN DISTINCT m.name AS name, m.module_path AS module_path
                        """,
                        {"name": name, "module_path": module_path},
                    )
                    for r in methods:
                        add(score, "method", r.get("name"), r.get("module_path"), name)

                    parents = await self.execute_query(
                        f"""
                        MATCH (c:Class {{name: $name, module_path: $module_path}})
                              -[:INHERITS_FROM*1..{max_depth}]->(p:Class)
                        RETURN DISTINCT p.name AS name, p.module_path AS module_path
                        """,
                        {"name": name, "module_path": module_path},
                    )
                    for r in parents:
                        add(score, "parent", r.get("name"), r.get("module_path"), name)

                    children = await self.execute_query(
                        f"""
                        MATCH (child:Class)-[:INHERITS_FROM*1..{max_depth}]->
                              (c:Class {{name: $name, module_path: $module_path}})
                        RETURN DISTINCT child.name AS name, child.module_path AS module_path
                        """,
                        {"name": name, "module_path": module_path},
                    )
                    for r in children:
                        add(score, "child", r.get("name"), r.get("module_path"), name)

                if module_path:
                    imports = await self.execute_query(
                        """
                        MATCH (m:Module {path: $module_path})-[:HAS_IMPORT]->(i:Import)
                        RETURN i.names AS names
                        """,
                        {"module_path": module_path},
                    )
                    for r in imports:
                        for sym in (r.get("names") or []):
                            add(score, "import", sym, None, name)
            except Exception as e:  # pragma: no cover - defensive per-seed isolation
                logger.warning(f"Neighbor query failed for seed {name}: {e}")

        candidates.sort(key=lambda t: (-t[0], t[1]))
        out: List[Dict[str, Any]] = []
        seen = set()
        for _, _, rec in candidates:
            if rec["name"] in seen:
                continue
            seen.add(rec["name"])
            out.append(rec)
            if len(out) >= limit:
                break
        return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend-fastapi && venv\Scripts\python.exe -m pytest tests/test_neo4j_neighbors.py -v --no-cov`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend-fastapi/app/services/code_graph/neo4j_client.py backend-fastapi/tests/test_neo4j_neighbors.py
git commit -m "feat(graph): get_entity_neighbors traversal returning bare neighbor names"
```

---

## Task 3: Rewire `retrieve` to seed graph traversal from semantic hits

**Files:**
- Modify: `backend-fastapi/app/services/code_graph/retriever.py`
- Modify: `backend-fastapi/tests/test_retriever_parallel.py`

- [ ] **Step 1: Replace the retriever tests for the new sequential behavior**

Replace the entire body of `backend-fastapi/tests/test_retriever_parallel.py` with:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend-fastapi && venv\Scripts\python.exe -m pytest tests/test_retriever_parallel.py -v --no-cov`
Expected: FAIL — `retrieve` still calls `batch_get_entity_context` / regex path; `get_entity_neighbors` not invoked, seeds not captured.

- [ ] **Step 3: Add the seed constant and helper**

In `backend-fastapi/app/services/code_graph/retriever.py`, near the top-level constants (after the existing imports/constants), add:

```python
GRAPH_SEED_COUNT = 5  # number of top semantic hits used to seed graph traversal
```

Add this method to `CodeGraphRetriever` (next to the other private helpers, e.g. above `_build_combined_context`):

```python
    def _seed_entities_from_semantic(self, semantic_results, n: int) -> list:
        """Pick the top-n semantic hits (merged across collections, ranked by
        relevance_score) and map each to a graph-node seed descriptor."""
        chunks = []
        if isinstance(semantic_results, dict):
            for lst in semantic_results.values():
                if isinstance(lst, list):
                    chunks.extend(c for c in lst if isinstance(c, dict))
        elif isinstance(semantic_results, list):
            chunks = [c for c in semantic_results if isinstance(c, dict)]
        chunks.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)

        seeds = []
        for c in chunks[:n]:
            md = c.get("metadata") or {}
            seeds.append({
                "name": md.get("name"),
                "module_path": md.get("module_path"),
                "class_name": md.get("class_name"),
                "type": md.get("type"),
                "relevance_score": c.get("relevance_score", 0),
            })
        return seeds
```

- [ ] **Step 4: Rewire the `retrieve` graph branch to be sequential and seed from semantic hits**

In `retrieve`, the current body builds `semantic_search()` and `graph_traversal()` inner coroutines and runs them with `asyncio.gather`. Replace that block (from the `async def semantic_search()` definition through the `result["graph_context"] = graph_context` assignment) with:

```python
        async def semantic_search():
            if project_id and self.config.enable_semantic_search:
                try:
                    chromadb = self._get_chromadb()
                    return await asyncio.to_thread(
                        chromadb.search_all, query, project_id, top_k
                    )
                except Exception as e:
                    logger.warning(f"Semantic search failed: {e}")
            return {}

        # Semantic search first; the graph branch seeds from its hits.
        semantic_results = await semantic_search()
        result["semantic_results"] = semantic_results

        graph_context = None
        if include_graph_context:
            try:
                neo4j = await self._get_neo4j()
                seeds = self._seed_entities_from_semantic(semantic_results, GRAPH_SEED_COUNT)
                graph_context = await neo4j.get_entity_neighbors(seeds, max_depth=max_depth)
            except Exception as e:
                logger.warning(f"Graph traversal failed: {e}")
                graph_context = None
        result["graph_context"] = graph_context
```

Remove the now-unused `asyncio.gather(...)` call and the old `graph_traversal()` inner coroutine. Keep the rest of `retrieve` (cache handling, `combined_context`, caching) unchanged.

- [ ] **Step 5: Update `_build_combined_context` graph rendering**

In `_build_combined_context`, replace the graph-context rendering block (the loop over `graph_ctx` that branches on `"name"` / `"entity"`) with the flat-shape renderer:

```python
        # 添加图上下文
        graph_ctx = result.get("graph_context")
        if graph_ctx:
            context_parts.append("图谱关系:")
            for ctx in graph_ctx[:10]:
                relation = ctx.get("relation", "related")
                module_path = ctx.get("module_path") or ""
                context_parts.append(
                    f"  - {ctx.get('name')} [{relation}] ({module_path})"
                )
```

- [ ] **Step 6: Remove the now-dead regex path if unused**

Run: `cd backend-fastapi && grep -rn "_extract_entity_names\|batch_get_entity_context" app/ tests/`
- If `_extract_entity_names` is referenced only by the old (now-removed) graph branch, delete the `_extract_entity_names` method from `retriever.py`.
- `batch_get_entity_context` in `neo4j_client.py`: if `grep` shows no remaining references in `app/`, delete it; if other code still uses it, leave it. (Do not delete on assumption — act on the grep result.)

- [ ] **Step 7: Run the retriever tests**

Run: `cd backend-fastapi && venv\Scripts\python.exe -m pytest tests/test_retriever_parallel.py -v --no-cov`
Expected: PASS (5 tests).

- [ ] **Step 8: Run the full backend suite for regressions**

Run: `cd backend-fastapi && venv\Scripts\python.exe -m pytest tests/ -q --no-cov`
Expected: all PASS. If a test that referenced `batch_get_entity_context` now fails, it belongs to a consumer you must reconcile — investigate before proceeding.

- [ ] **Step 9: Commit**

```bash
git add backend-fastapi/app/services/code_graph/retriever.py backend-fastapi/tests/test_retriever_parallel.py
git commit -m "feat(graph): seed neighbor traversal from semantic hits (sequential retrieve)"
```

---

## Task 4: Confirm the eval extractor handles the new graph_context shape

**Files:**
- Test: `evals/tests/test_runner_extract.py`

`extract_neighbors_from_graph` (in `evals/runner.py`) recursively collects `"name"` and `"entity"` string values. The new flat records use `"name"` for the neighbor and `"module_path"` for the path, so neighbor names are collected and paths are not. This task proves that with a test (no production change expected).

- [ ] **Step 1: Write the test**

Add to `evals/tests/test_runner_extract.py`:

```python
from evals.runner import extract_neighbors_from_graph


class TestNeighborExtractionNewShape:
    def test_extracts_names_not_module_paths(self):
        graph_context = [
            {"name": "do_work", "module_path": "app/a.py", "relation": "callee", "source": "retrieve"},
            {"name": "Neo4jClient", "module_path": None, "relation": "import", "source": "retrieve"},
        ]
        out = extract_neighbors_from_graph(graph_context)
        assert "do_work" in out
        assert "Neo4jClient" in out
        assert "app/a.py" not in out  # module paths are not neighbor names
```

- [ ] **Step 2: Run it**

Run (repo root): `backend-fastapi\venv\Scripts\python.exe -m pytest evals/tests/test_runner_extract.py -v`
Expected: PASS. If it fails (e.g. `extract_neighbors_from_graph` also collects `source`), adjust the extractor minimally so it returns only neighbor names, and note the change in the commit.

- [ ] **Step 3: Commit**

```bash
git add evals/tests/test_runner_extract.py
git commit -m "test(evals): neighbor extraction handles new flat graph_context shape"
```

---

## Task 5: Reindex, re-baseline, and reconcile the golden set

This task produces the before/after numbers. It needs Docker services up and `ZHIPUAI_API_KEY` set. It is a measurement + judgment task, not TDD.

- [ ] **Step 1: Reindex the corpus (graph now stores import names)**

Run (repo root):

```bash
backend-fastapi\venv\Scripts\python.exe -m evals.run --golden evals/golden_set/backend_fastapi.jsonl --index-corpus backend-fastapi/app
```

Expected: table printed, 0 errors, JSON written under `evals/results/`. Record the new retrieval numbers (especially `graph_neighbor_recall`, `graph_traversal_correctness`, `hybrid_hit_rate@5`).

- [ ] **Step 2: Inspect residual zero-recall cases**

Create `evals/_tmp_neighbor_probe.py` (delete after this task), then run it as a module from the repo root (`backend-fastapi\venv\Scripts\python.exe -m evals._tmp_neighbor_probe`):

```python
"""TEMP: per-case graph-neighbor recall after the traversal change. Delete after use."""
import asyncio
import json

import evals  # noqa: F401  sys.path setup for app.*
from app.services.code_graph.retriever import CodeGraphRetriever
from evals.runner import extract_neighbors_from_graph
from evals.metrics.graph import graph_neighbor_recall

EVAL_PROJECT_ID = 99999


async def main():
    cases = [json.loads(l) for l in open("evals/golden_set/backend_fastapi.jsonl", encoding="utf-8") if l.strip()]
    withn = [c for c in cases if c.get("expected_graph_neighbors")]
    retriever = CodeGraphRetriever()
    zero = []
    for c in withn:
        raw = await retriever.retrieve(query=c["question"], project_id=EVAL_PROJECT_ID,
                                       top_k=10, include_graph_context=True, max_depth=2)
        retrieved = extract_neighbors_from_graph(raw.get("graph_context"))
        rec = graph_neighbor_recall(set(retrieved), c["expected_graph_neighbors"])
        print(c["id"], "recall=", rec, "expected=", c["expected_graph_neighbors"], "got=", retrieved[:8])
        if not rec:
            zero.append(c["id"])
    print("\nSTILL ZERO:", zero)


asyncio.run(main())
```

Expected: most cases now show non-zero recall; the printed `STILL ZERO` list is the input to Step 3.

- [ ] **Step 3: Reconcile per the spec (section 9)**

For each still-zero case, classify and act:
- **System gap** (neighbor only reachable via a factory import like `get_retriever`, or a same-file class like `MetricsCollector`): leave the case unchanged; collect it for the README "known limitations" list (Option 3 territory).
- **Wrong expectation** (e.g. case expects class `TokenBlacklist` but the import is of instance `token_blacklist`): correct that case's `expected_graph_neighbors` in `evals/golden_set/backend_fastapi.jsonl` and append a one-line `notes` explanation. Do not trim cases to inflate the score.

Re-validate: `backend-fastapi\venv\Scripts\python.exe -c "from pathlib import Path; from evals.golden_set.validate import validate_golden_set; e,w=validate_golden_set(Path('evals/golden_set/backend_fastapi.jsonl'),Path('.')); print('errors',len(e),'warnings',len(w))"` (expect `errors 0`).

- [ ] **Step 4: Final retrieval + generation baseline on the reconciled set**

```bash
backend-fastapi\venv\Scripts\python.exe -m evals.run --golden evals/golden_set/backend_fastapi.jsonl --with-generation --quiet
```

Record the final numbers from the new `evals/results/*.json`. Delete any throwaway probe script.

- [ ] **Step 5: Commit golden-set corrections (if any)**

```bash
git add evals/golden_set/backend_fastapi.jsonl
git commit -m "fix(evals): reconcile graph-neighbor expectations after real traversal"
```

(If no case needed correction, skip this commit and note that in Task 6.)

---

## Task 6: Update the README with before/after numbers and known limitations

**Files:**
- Modify: `README.md` (Evaluation section)

- [ ] **Step 1: Update the numbers**

In the `## Evaluation` section, update the Retrieval and By-category tables with the new result JSON values from Task 5. Add a one-line before/after callout for the graph metrics, e.g.:

```markdown
Graph traversal now starts from the semantic hits and walks real CALLS / inheritance / import edges: graph_neighbor_recall rose from 0.10 to <new>, and hybrid_hit_rate@5 from 0.60 to <new> (git <sha>, <date>).
```

- [ ] **Step 2: Add a "Known limitations" note**

Add (or extend) a short note under the Evaluation section listing what is still not modeled, from Task 5's reconciliation:

```markdown
Known limitations: neighbors that are only reachable through factory imports (e.g. `get_retriever` rather than the class) or classes defined and used in the same file (e.g. `MetricsCollector`) are not yet edges in the graph; modeling class instantiation/usage is the next retrieval iteration. Eval graph nodes are indexed under `project_id=99999`; cross-project node isolation in Neo4j is a known limitation.
```

- [ ] **Step 3: Verify both test suites are green**

Run:
```bash
cd backend-fastapi && venv\Scripts\python.exe -m pytest tests/ -q --no-cov && cd ..
backend-fastapi\venv\Scripts\python.exe -m pytest evals/tests/ -q
```
Expected: both green.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README graph-traversal before/after numbers and known limitations"
```

---

## Self-Review notes (for the executor)

- Spec coverage: Task 1 = import indexing (spec 7); Task 2 = neighbor traversal (spec 6); Task 3 = retrieve rewire + combined_context + API-consumer check (spec 5, 8, 10); Task 4 = extractor compatibility (spec 8); Task 5 = reindex/re-baseline/reconciliation (spec 9, 12); Task 6 = README + known limitations (spec 2, 12).
- The only intentional behavior change to existing tests is in `test_retriever_parallel.py` (parallel → sequential, `batch_get_entity_context` → `get_entity_neighbors`). This is expected, not a regression.
- `api/code_graph.py:semantic_search` passes `result["graph_context"]` straight into a JSON response; the new list-of-dicts shape is JSON-serializable, so the endpoint keeps working with a richer response body. No code change required there, but confirm during Task 3 Step 8.
```
