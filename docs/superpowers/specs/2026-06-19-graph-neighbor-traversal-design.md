# Smart Code Assistant — Phase 2a: Real Graph-Neighbor Traversal from Semantic Hits

Status: approved (brainstorming, 2026-06-19)
Supersedes the graph branch of `CodeGraphRetriever.retrieve`; follows Phase 1b (evals).

## 1. Goal

Make the "graph" half of the GraphRAG pipeline actually traverse the code graph,
so that `graph_neighbor_recall` and `hybrid_hit_rate@k` reflect real neighbor
retrieval instead of regex noise. Drive the change with the existing eval harness
and record a before/after delta in the README.

Baseline to beat (git `0d297e4`, 50-case golden set, 2026-06-18):
`graph_neighbor_recall = 0.10`, `graph_traversal_correctness = 0.08`,
`hybrid_hit_rate@5 = 0.60`, `hit_rate@5 = 0.60`.

## 2. Non-goals (deferred)

- **Class instantiation / usage edges** (Option 3): modeling "function f uses class
  C" as a graph edge. Needed only for neighbors that are neither call-graph nodes
  nor imported symbols (e.g. a class defined and instantiated in the same file like
  `MetricsCollector`). Deferred and documented as a known limitation.
- **Cross-project graph isolation**: `Function`/`Class`/`Import` nodes do not all
  carry `project_id` (only `Module` does). The eval runs against an isolated
  single-project index, so this does not affect the numbers. Recorded as a known
  limitation, not fixed here.
- **Re-ranking / hybrid BM25** retrieval upgrades — separate later iteration.
- **Generation prompt changes**: `GEN_PROMPT_VERSION` stays `v1`. Only the *content*
  of `combined_context` changes (intended, so the generation delta is attributable
  to retrieval).

## 3. Context: why the graph branch currently reads ~0

Diagnosed 2026-06-19 (systematic debugging). The graph branch of
`CodeGraphRetriever.retrieve` does **not** traverse neighbors:

1. **Entity source is regex over the question.** `_extract_entity_names(query)`
   pulls snake_case then CamelCase tokens from the question text, floods the list
   with common words (and the stopword list omits `and`), and `retrieve` passes only
   the first 3 to the graph query. The meaningful identifier (usually CamelCase,
   e.g. `LLMService`) is pushed past the cutoff. Confirmed: for
   "How does LLMService defer..." the graph was queried with `['defer','construction','and']`.
2. **`batch_get_entity_context` returns no neighbors.** Its query matches nodes where
   `e.name CONTAINS <term>` and returns those matched entities themselves, plus
   scalar caller/callee *counts*. It never returns the *names* of callers, callees,
   imported symbols, or base classes.
3. **Format mismatch.** Module matches return path strings (`app/.../neo4j_client.py`)
   while the golden set expects bare names (`Neo4jClient`). The metric is an exact
   set intersection, so these never match.

Graph data is healthy (1 project, 67 modules, 199 classes, 334 functions, 463
imports, 1639 relationships); the problem is purely the retrieval path.

Of the 25 golden cases that specify `expected_graph_neighbors`, ~12 expect
function call-graph neighbors (reachable via `CALLS`), and ~13 expect class or
imported-symbol neighbors. The latter are unreachable today because
`ImportEntity.names` (the imported symbols, already parsed) is dropped at build
time — `create_import` stores only the module string. In Python these class
neighbors are almost always imported by name (verified: `retriever.py` does
`from ...neo4j_client import Neo4jClient`, etc.), so storing the parsed import
names unlocks the majority of them with one bounded indexing change.

## 4. Decisions locked during brainstorming

- Scope = **Option 2**: real traversal from semantic hits + import-symbol indexing.
  Not Option 1 (would require trimming the hard half of the golden set — rejected as
  a credibility risk). Not Option 3 (class-usage edges — deferred).
- Seed the graph traversal from the **top-N semantic hits** (N = 5, configurable),
  not from regex over the query.
- Traversal becomes **sequential** (semantic first, then graph from its hits),
  replacing the current `asyncio.gather` parallelism. Accepted trade-off.
- Neighbor set is **typed and bounded**, ranked by the seeding hit's
  `relevance_score`, capped (default 20) to protect precision.
- Do **not** over-fit traversal to eval categories.
- Golden reconciliation happens **after** measurement, case by case, distinguishing
  genuine system gaps (documented) from genuinely-wrong expectations (transparently
  corrected). No wholesale trimming.

## 5. Architecture / data flow

`CodeGraphRetriever.retrieve` graph branch, new flow:

1. `semantic_search()` runs unchanged → `{"functions": [...], "classes": [...]}`,
   each chunk carrying `metadata = {name, module_path, class_name?, type}` and a
   `relevance_score`.
2. Merge + rank the hits by `relevance_score` (same logic the eval already uses),
   take the top **N = 5** as seed entities:
   `{name, module_path, class_name, type, relevance_score}`.
3. `graph_context = await neo4j.get_entity_neighbors(seeds, max_depth)`.
4. `_build_combined_context` renders the new `graph_context` shape into the text
   context used for generation.

Because the graph branch now consumes the semantic results, the two no longer run
concurrently; `retrieve` awaits semantic search, then traversal.

## 6. Neighbor definition: `Neo4jClient.get_entity_neighbors`

New method:

```
async def get_entity_neighbors(
    self, seeds: list[dict], max_depth: int = 2, limit: int = 20
) -> list[dict]
```

`seeds` is the list of semantic-hit descriptors `{name, module_path, class_name, type, relevance_score}`.

For each seed, collect typed neighbors (all returning bare `name`):

- seed is a **function** (`type == "function"`):
  - callees: `(f:Function {name, module_path, class_name})-[:CALLS*1..max_depth]->(callee:Function)`
  - callers: `(caller:Function)-[:CALLS*1..max_depth]->(f:Function {name, module_path, class_name})`
- seed is a **class** (`type == "class"`):
  - methods: `(c:Class {name, module_path})-[:HAS_METHOD]->(m:Function)`
  - parents: `(c)-[:INHERITS_FROM*1..max_depth]->(p:Class)`
  - children: `(child:Class)-[:INHERITS_FROM*1..max_depth]->(c)`
- seed's **module** (any seed, keyed by `module_path`):
  - imported symbols: `(m:Module {path: module_path})-[:HAS_IMPORT]->(i:Import)` then
    flatten `i.names`. Only the imported symbol names are returned (not the module
    path string), since the golden set expects bare symbol names.

Each returned record: `{"name": <bare>, "module_path": <str|None>, "relation": "callee"|"caller"|"method"|"parent"|"child"|"import", "source": <seed name>}`.

Implementation may compose the existing `get_function_callers` / `get_function_callees`
/ `get_class_methods` / impact queries, or use dedicated batched Cypher. Existing
methods are kept (still used by the API endpoints).

## 7. Import indexing change

- `ast_parser` already produces `ImportEntity.names` (the `a, b, c` of
  `from X import a, b, c`). No parser change.
- `graph_builder` passes `imp.names` to `create_import`.
- `Neo4jClient.create_import` gains a `names: list[str]` parameter and stores it:
  `SET i.names = $names` (alongside the existing `module`/`alias`/`module_path`).
  Neo4j supports list-of-string properties. The MERGE key is unchanged
  (`module`, `alias`, `module_path`); `names` is a SET property.
- **Reindex required**: the eval re-indexes via `--index-corpus backend-fastapi/app`
  before re-baselining, so existing Import nodes pick up `names`.

## 8. Output shape + precision control

- `graph_context` becomes `list[dict]` of the neighbor records in section 6.
- Dedup by `name` (first occurrence wins).
- Rank: by the `relevance_score` of the source seed (descending), then by a fixed
  relation priority (`callee`/`caller`/`import` before `method`/`parent`/`child`).
- Cap at `limit` (default 20) total neighbors.
- `evals/runner.py::extract_neighbors_from_graph` already collects `"name"` (and
  `"entity"`) values from the graph_context structure; the new flat shape keeps
  neighbor names under `"name"` and paths under `"module_path"` (not collected), so
  **no change to `extract_neighbors_from_graph` is required**. This is verified by a
  test, not assumed.
- `_build_combined_context` updates its graph-rendering loop to the new shape
  (`name` + `relation` + `module_path`), replacing the old `name`/`entity` branch.

## 9. Golden set reconciliation (post-measurement)

After implementing, reindexing, and re-running the eval:

1. List cases still at `graph_neighbor_recall == 0`.
2. For each, classify:
   - **System gap** (e.g. neighbor is a same-file class like `MetricsCollector`, or
     only reachable via a factory import like `get_retriever` rather than the class):
     leave the case as-is, record under "known limitations" / Option 3.
   - **Wrong expectation** (e.g. expecting a class name `TokenBlacklist` when the
     import is of the instance `token_blacklist`): correct the case's
     `expected_graph_neighbors`, with a one-line note in the case explaining why.
3. Re-run; the published numbers use the reconciled golden set, and the README/spec
   state plainly which cases were corrected and which remain known limitations.

## 10. Error handling / compatibility

- Graph traversal failure (Neo4j down, bad seed) is caught and degrades to an empty
  `graph_context` with a warning — semantic results still return. (Same posture as
  today.)
- `retrieve` is consumed by the live API (`/code-graph/search` and related). The
  `graph_context` shape change must be reconciled with those consumers and with
  `_build_combined_context`; this is part of the implementation, checked explicitly.
- Retrieval caching (`global_cache_manager`, keyed on query+project+params) is
  unaffected; the new code path simply caches the new result shape.

## 11. Testing strategy

- **Unit** (no live services): `get_entity_neighbors` against a small seeded fake /
  fixture graph — callees, callers, methods, parents, and imported `names` come back
  as bare names with correct `relation`. Dedup, ranking, and cap behavior tested.
- **Unit**: `retrieve` graph branch seeds from semantic hits and no longer calls
  `_extract_entity_names` (mock chromadb + neo4j).
- **Unit**: `extract_neighbors_from_graph` returns the bare neighbor names from the
  new flat `graph_context` shape and does not pick up `module_path`.
- **Live probe** (like the import-alias fix): `create_import` stores and returns
  `names`; `get_entity_neighbors` returns expected neighbors for one known entity.
- **Integration / measurement**: reindex + full eval run (services up), record the
  before/after table. Not in CI.
- Backend suite (`tests/`) and evals suite (`evals/tests/`) stay green.

## 12. Expected outcome / measurement

- `graph_neighbor_recall` rises substantially from 0.10 (target: the majority of the
  25 graph-neighbor cases recovered, minus documented Option-3 gaps).
- `graph_traversal_correctness` and `hybrid_hit_rate@5` rise correspondingly.
- README "By category" and headline numbers updated from the new result JSON, with a
  one-line before/after callout and a short "known limitations" note (Option 3,
  cross-project isolation).

## 13. Suggested commit order

1. `create_import` stores `names` + graph_builder passes `imp.names` (+ live probe / unit).
2. `get_entity_neighbors` traversal method (+ unit tests).
3. `retrieve` graph branch rewired to seed from semantic hits; `_build_combined_context`
   updated; old `_extract_entity_names` / `batch_get_entity_context` left in place only
   if still used elsewhere, otherwise removed (+ unit tests; verify API consumers).
4. Reindex + re-baseline; golden reconciliation pass.
5. README update with before/after numbers and known limitations.

## 14. Option 3 preview (separate spec, not designed here)

Model class instantiation / attribute usage as edges (e.g. `USES`), so neighbors
that are neither call-graph nodes nor imported symbols become reachable. Would
recover the residual same-file-class and factory-import cases. Larger AST work;
its own spec, plan, and measurement cycle.
