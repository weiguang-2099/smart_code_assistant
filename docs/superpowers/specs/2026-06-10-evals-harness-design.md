# Smart Code Assistant — Phase 1 Evaluation Harness Design

Date: 2026-06-10
Status: Approved (brainstorming → ready for implementation plan)
Scope: Phase 1 of `smart-code-assistant-upgrade-checklist.md`, retrieval metrics only

## 1. Goal

Build a runnable evaluation harness for the GraphRAG retrieval system. The harness must produce numbers a reviewer can verify: retrieval recall/precision/MRR and graph traversal correctness on a fixed golden set, with results written to a timestamped JSON file and a stdout table.

The harness is the substrate for Phase 2 retrieval upgrades (BM25, reranker, fusion). Each upgrade must be evaluated against the same harness, and the delta is the story.

## 2. Non-goals (out of scope for v1)

The following are deferred and must not be implemented in this round:

- LLM-as-judge / generation metrics (faithfulness, relevance, correctness)
- Agent trajectory metrics (task_success_rate, step count, tool call correctness)
- CI regression gating (fail build on metric drop)
- Trend dashboards
- Cost / latency tracking inside evals
- Multi-retriever ablation harness
- Automatic PR comments
- RAGAS compatibility layer
- Embedding model ablation
- Per-metric formal documentation site

## 3. Decisions locked during brainstorming

| Decision | Choice |
|---|---|
| Corpus | Self-eval against `backend-fastapi/` locally + a small `mini_repo` fixture for CI |
| Scope of v1 | Retrieval metrics + GraphRAG traversal correctness only; generation/agent later |
| Golden set authoring | AI generates draft, human reviews and trims to 30-50 cases |
| CI integration mode | Smoke run on every PR, reports only, no fail gate in v1 |
| CI execution model | GitHub Actions service container (Neo4j + ChromaDB), index `mini_repo` on the fly |
| Package layout | Standalone top-level `evals/` package (Approach A) |
| Retriever access | Direct Python import of `CodeGraphRetriever`, not HTTP |
| Indexing | `evals.run` is read-only by default; opt-in `--index-corpus PATH` flag triggers `graph_builder` |
| Eval project isolation | Hard-coded `EVAL_PROJECT_ID = 99999` constant |
| New dependencies | None — no pip install, hand-roll table rendering |

## 4. Architecture

```
golden_set/*.jsonl          ┐
fixtures/mini_repo/         ├─►  evals/run.py  (argparse entry)
backend-fastapi/ (live)     ┘        │
                                     ▼
                            evals/runner.py
                                     │ direct import (no HTTP)
                                     ▼
                CodeGraphRetriever.retrieve(query, top_k, max_depth, project_id)
                      │                    │
                      ▼                    ▼
              ChromaDB (semantic)     Neo4j (graph traversal)
                      │
                      ▼
                evals/metrics/* (pure functions)
                      │
                      ▼
              evals/reporter.py
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
       stdout table     evals/results/{ISO timestamp}.json
```

Key boundaries:

- `evals/__init__.py` does `sys.path.insert(0, "backend-fastapi")` so `from app.services.code_graph.retriever import CodeGraphRetriever` works without packaging changes.
- `evals/` does not edit any file under `backend-fastapi/app/`.
- Evals assumes the index already exists in Neo4j+Chroma, unless `--index-corpus PATH` is passed (then `graph_builder` is invoked first).

## 5. Component layout

```
evals/
├── __init__.py               # sys.path setup
├── run.py                    # python -m evals.run entry, argparse
├── config.py                 # EVAL_PROJECT_ID, K_VALUES, defaults
├── runner.py                 # async per-case retrieve loop with semaphore
├── reporter.py               # table render + JSON dump
├── metrics/
│   ├── __init__.py
│   ├── retrieval.py          # hit_rate@k, precision@k, recall@k, mrr
│   └── graph.py              # graph_neighbor_recall/precision, traversal_correctness
├── golden_set/
│   ├── backend_fastapi.jsonl       # 30-50 cases, local self-eval
│   ├── mini_fixture.jsonl          # 10-15 cases, CI smoke
│   └── validate.py                 # schema/path validator
├── fixtures/
│   └── mini_repo/             # 8-10 Python files for CI indexing
├── results/                   # gitignored except .gitkeep
│   └── .gitkeep
└── tests/
    ├── test_metrics.py
    ├── test_validate.py
    └── test_reporter.py
```

## 6. Golden case schema

JSONL, one case per line. Required fields: `id`, `question`, `category`, `expected_files`. Optional: `expected_symbols`, `expected_graph_neighbors`, `notes`.

```json
{
  "id": "rate-limiter-001",
  "question": "How is per-user rate limiting wired into FastAPI?",
  "category": "feature_lookup",
  "expected_files": ["app/core/rate_limiter.py", "app/main.py"],
  "expected_symbols": ["setup_rate_limiting"],
  "expected_graph_neighbors": ["slowapi.Limiter"],
  "notes": "main.py wires it via setup_rate_limiting(app)"
}
```

### Field semantics

- `id`: stable kebab-case slug. Never changes even if question text is edited.
- `category`: one of `definition_lookup`, `feature_lookup`, `dependency_trace`, `impact_analysis`, `cross_file_flow`. Used for per-category report breakdown.
- `expected_files`: list of repo-relative paths starting with `app/`. v1 primary matching axis.
- `expected_symbols`: optional. v1 collects but does not score; reserved for symbol-level metrics in a later iteration.
- `expected_graph_neighbors`: optional. Set of Neo4j neighbor node names (caller, callee, import target).
- `notes`: human comment; metrics never read this.

### Matching policy

Strict string equality on `expected_files`. No fuzzy/regex/parent-path matching. Same for `expected_graph_neighbors`. Rationale: fuzzy matching makes future metric deltas (e.g., after BM25) ambiguous — was the win real, or did the match relax? Strict matching keeps the goalposts fixed.

### Authoring workflow

1. Claude scans `backend-fastapi/app/` and produces ~50 candidate cases per category distribution below.
2. Each candidate's `expected_files` is verified by opening the file and confirming the symbol exists.
3. `expected_graph_neighbors` is inferred statically (imports, call sites) — flagged as low-confidence until Neo4j is available.
4. Output to `evals/golden_set/backend_fastapi.draft.jsonl`.
5. Human reviewer trims/corrects to 30-50 keepers, saves to `evals/golden_set/backend_fastapi.jsonl`.
6. `evals/golden_set/mini_fixture.jsonl` follows the same workflow for the CI fixture, 10-15 cases.

Distribution target for the draft:

| category | candidates |
|---|---|
| definition_lookup | 12 |
| feature_lookup | 12 |
| dependency_trace | 10 |
| impact_analysis | 8 |
| cross_file_flow | 8 |

### Validation script

`evals/golden_set/validate.py` runs in CI and locally before any eval:

- Every `id` is unique
- Every path in `expected_files` exists in the working tree (`os.path.exists`)
- `category` is in the whitelist
- Required fields present
- `expected_symbols` / `expected_graph_neighbors` produce warnings (not errors) when missing — encourages filling without blocking

## 7. Metrics (formal definitions)

Retriever is called with `top_k=10`, `include_graph_context=True`, `max_depth=2`, `project_id=EVAL_PROJECT_ID`.

Notation:
- `C = [c1, c2, ..., c10]` — ranked ChromaDB chunks from `semantic_results`. Each `c.file_path` is the chunk's file.
- `E` = `expected_files` set
- `G` = set of neighbor node names extracted from `graph_context`
- `N` = `expected_graph_neighbors` set

`k ∈ {1, 3, 5, 10}` for all `@k` metrics.

### 7.1 Chunk-ranked metrics

| Metric | Definition |
|---|---|
| `hit_rate@k` | `1 if any c ∈ C[:k] has c.file_path ∈ E else 0` |
| `precision@k` | `|{c ∈ C[:k] : c.file_path ∈ E}| / k` (chunk-based, no dedup, denominator is `k` not `|C[:k]|`) |
| `mrr` | `1 / rank(first c in C with c.file_path ∈ E)`, or 0 if none |

`mrr` searches the entire returned list C (not capped at k); chunks are the ranking unit.

### 7.2 File-coverage metric

| Metric | Definition |
|---|---|
| `recall@k` | `|unique(file_path of c ∈ C[:k]) ∩ E| / |E|` |

Recall uses unique files in the top-k chunks because it measures coverage of the expected set; same file appearing twice doesn't increase coverage.

### 7.3 Graph metrics (no `k` — graph is a set, not a ranking)

| Metric | Definition |
|---|---|
| `graph_neighbor_recall` | `|G ∩ N| / |N|` |
| `graph_neighbor_precision` | `|G ∩ N| / |G|`, 0 if `G = ∅` |
| `graph_traversal_correctness` | `1 if G ⊇ N else 0` (strict superset, all neighbors must be hit) |

### 7.4 Hybrid metric

| Metric | Definition |
|---|---|
| `hybrid_hit_rate@k` | `1 if (any c ∈ C[:k] has c.file_path ∈ E) OR (G ∩ N ≠ ∅) else 0` |

This is the single metric that captures GraphRAG's complementary value. It is the primary headline number for Phase 2 deltas.

### 7.5 Aggregation

- Macro average: per-case score, then arithmetic mean.
- Cases where `expected_graph_neighbors` is null/missing: graph metrics record `null` and are excluded from the denominator. Reporter shows `(graph cases: n=X)` next to the aggregated graph metric so the sample size is visible.
- Cases where the retriever throws: every metric records `null`. They contribute to `error_rate = error_count / total_count`; they do not contribute to any metric's mean.

### 7.6 Report shape (example)

```
==== Overall (n=42, errors=1) ====
hit_rate@1            0.52
hit_rate@5            0.81
recall@5              0.64
precision@5           0.21
mrr                   0.49
graph_neighbor_recall 0.58  (graph cases: n=30)
graph_traversal_correctness 0.20  (graph cases: n=30)
hybrid_hit_rate@5     0.88

==== By category ====
                       n   hit_rate@5  recall@5  mrr
definition_lookup     10        0.90     0.85   0.78
feature_lookup        10        0.80     0.62   0.45
dependency_trace       9        0.78     0.55   0.42
impact_analysis        7        0.71     0.48   0.35
cross_file_flow        6        0.83     0.58   0.41
```

## 8. CLI

```
python -m evals.run [options]

Required:
  --golden PATH              golden set JSONL path

Optional:
  --index-corpus PATH        if given, run graph_builder on this directory before evals
  --project-id INT           overrides EVAL_PROJECT_ID (default 99999); for advanced use only
  --top-k INT                retriever top_k (default 10)
  --max-depth INT            graph traversal depth (default 2)
  --categories CSV           filter by category (e.g. definition_lookup,feature_lookup)
  --limit INT                only run first N cases (debug)
  --output-dir PATH          results dir (default evals/results)
  --concurrency INT          parallel retrieve calls (default 5)
  --quiet                    only print JSON path
```

Exit codes:
- `0` — eval completed (regardless of metric values)
- `2` — config / golden-set error (file missing, schema invalid, bad CLI args)
- `3` — infrastructure error (Neo4j/Chroma unreachable, `--index-corpus` failed)

v1 never returns non-zero on low metrics. Threshold gating is deferred.

## 9. Run flows

### 9.1 Local self-eval

Prerequisite: backend-fastapi/ already indexed once into Neo4j+Chroma under `project_id=99999`. The user runs `graph_builder` separately.

```
python -m evals.run --golden evals/golden_set/backend_fastapi.jsonl
```

### 9.2 Local debug

```
python -m evals.run \
  --golden evals/golden_set/backend_fastapi.jsonl \
  --limit 3 --categories definition_lookup
```

### 9.3 CI smoke

```
python -m evals.run \
  --golden evals/golden_set/mini_fixture.jsonl \
  --index-corpus evals/fixtures/mini_repo
```

## 10. JSON result schema

`evals/results/{ISO timestamp Z}.json`:

```json
{
  "meta": {
    "timestamp": "2026-06-10T14:23:01Z",
    "git_sha": "c15ab6e",
    "git_dirty": true,
    "golden_set": "evals/golden_set/backend_fastapi.jsonl",
    "indexed_corpus": null,
    "case_count": 42,
    "config": {"top_k": 10, "max_depth": 2, "project_id": 99999, "concurrency": 5}
  },
  "cases": [
    {
      "id": "rate-limiter-001",
      "category": "feature_lookup",
      "expected_files": ["app/core/rate_limiter.py"],
      "expected_graph_neighbors": ["slowapi.Limiter"],
      "retrieved_files_ranked": ["app/core/rate_limiter.py", "app/main.py"],
      "retrieved_graph_neighbors": ["slowapi.Limiter", "RateLimitExceeded"],
      "metrics": {
        "hit_rate@1": 1, "hit_rate@3": 1, "hit_rate@5": 1, "hit_rate@10": 1,
        "recall@1": 1.0, "recall@3": 1.0, "recall@5": 1.0, "recall@10": 1.0,
        "precision@1": 1.0, "precision@5": 0.2,
        "mrr": 1.0,
        "graph_neighbor_recall": 1.0,
        "graph_neighbor_precision": 0.5,
        "graph_traversal_correctness": 1,
        "hybrid_hit_rate@5": 1
      },
      "error": null
    }
  ],
  "aggregate": {
    "overall": {"n": 42, "errors": 1, "hit_rate@5": 0.81, "recall@5": 0.64},
    "by_category": {
      "definition_lookup": {"n": 10, "hit_rate@5": 0.90}
    }
  }
}
```

`git_dirty` is true if `git status --porcelain` produces any output at run time. Critical for distinguishing "this number came from a clean commit" vs "this number came from work-in-progress."

## 11. Error handling

| Failure | Behavior | Exit |
|---|---|---|
| Neo4j connection failure | print clear error, no JSON written | 3 |
| Chroma connection failure | same | 3 |
| Golden set file missing | print path error + list available golden sets | 2 |
| Golden set schema invalid | print every violation with line number, do not run eval | 2 |
| `--index-corpus` failure (graph_builder raises) | print full traceback, do not run eval | 3 |
| Single-case retriever exception | `error` field set with stack summary, all metrics null, continue | 0 |
| Single-case timeout (>30s) | same, error = "timeout" | 0 |
| Result file write failure | print error, computed metrics still printed to stdout | 0 |
| Git not available | `git_sha=null, git_dirty=null`, continue | 0 |

Framework errors halt the run. Data errors are isolated to the case and reported as `error_rate`.

## 12. Concurrency

- `asyncio.Semaphore(concurrency)` limits parallel `retrieve()` calls, default 5.
- Empirical guard: if Neo4j/Chroma show errors under load, reduce default to 3 in `config.py`. The choice is a knob, not a forever decision.
- Per-case timeout 30s, enforced with `asyncio.wait_for`.

## 13. Testing strategy

All evals tests live in `evals/tests/`. They must run without Neo4j/Chroma — pure functions only.

### `test_metrics.py`

For each metric, at least three cases: full hit, partial hit, no hit. Plus `null`/empty inputs and dedup edge cases (same file appearing twice in retrieved). Approximately 20-30 test functions.

### `test_validate.py`

- Minimal valid case passes
- Missing required field fails
- Bad category fails
- Path-not-found in `expected_files` fails
- Duplicate `id` across multiple cases fails
- Missing optional fields produce warnings, not errors

### `test_reporter.py`

- Snapshot test for stdout table formatting on a fixed aggregate fixture
- JSON serialization round-trip
- `git_dirty=true` is preserved through write+read

### What is not tested

End-to-end runner test. That requires real Neo4j+Chroma; covered by CI smoke job and local manual runs.

## 14. Dependencies

evals introduces **no new Python dependencies**. The harness uses only stdlib (`json`, `asyncio`, `argparse`, `dataclasses`, `pathlib`, `subprocess` for git_sha) plus the existing `backend-fastapi` requirements (already in CI). Table formatting is implemented in `reporter.py` as a ~30-line function.

This is a deliberate engineering signal: the eval harness should not have a heavier supply chain than the system it evaluates.

## 15. CI integration

A new job `evals-smoke` is appended to `.github/workflows/ci.yml`. It runs in parallel with the existing `backend` and `frontend` jobs. It does not block the backend job — both pass/fail independently.

The `ZHIPUAI_API_KEY: ci-test-key` line below is provisional pending TBD #5 (does indexing actually need the ZhipuAI API, or only the local bge model?). If TBD #5 resolves to "local only," the env line stays as a no-op stub; if it resolves to "API required," the env value moves to `${{ secrets.ZHIPUAI_API_KEY }}` and a `if:` guard skips the job on fork PRs.

```yaml
  evals-smoke:
    name: Evals - retrieval smoke
    runs-on: ubuntu-latest
    timeout-minutes: 5
    services:
      neo4j:
        image: neo4j:5.15-community
        env:
          NEO4J_AUTH: neo4j/test-password
        ports: ['7687:7687', '7474:7474']
        options: >-
          --health-cmd "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 10
      chromadb:
        image: chromadb/chroma:latest
        ports: ['8001:8000']
        options: >-
          --health-cmd "curl -f http://localhost:8000/api/v1/heartbeat || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: backend-fastapi/requirements.txt
      - name: Install backend deps
        working-directory: backend-fastapi
        run: pip install -r requirements.txt
      - name: Eval unit tests
        run: pytest evals/tests/ -v
      - name: Run smoke eval
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          NEO4J_PASSWORD: test-password
          CHROMADB_HOST: localhost
          CHROMADB_PORT: 8001
          ZHIPUAI_API_KEY: ci-test-key
        run: |
          python -m evals.run \
            --golden evals/golden_set/mini_fixture.jsonl \
            --index-corpus evals/fixtures/mini_repo
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: evals-results
          path: evals/results/*.json
          retention-days: 30
```

Runtime budget: 5 minutes hard cap. Expected actual ~90-180s (service startup ~30s + index 10 files ~20s + run 10 cases ~30s + buffer).

No automatic PR comments in v1. Reviewers download the artifact or read the job logs. PR description manually quotes headline numbers.

## 16. Implementation-time TBDs

These must be resolved on Day 1 of implementation by reading existing source, not by guessing:

1. **Chunk metadata field name and path format** — open `backend-fastapi/app/services/code_graph/chromadb_client.py` and `graph_builder.py` to find what key on the chunk dict stores the file path, and what root the path is relative to (repo root, `backend-fastapi/`, or `backend-fastapi/app/`). Choose the eval matching convention to match what is actually stored. Update Section 6 path convention if it differs from "starts with `app/`".

2. **graph_builder public interface** — read `backend-fastapi/app/services/code_graph/graph_builder.py` to learn the sync/async signature and what it expects (directory path? list of files? project_id required?). Update the `--index-corpus` implementation to call it correctly.

3. **Graph neighbor node identity** — open `neo4j_client.py` and `entity_extractor.py` to determine whether neighbors are identified by `name`, `qualified_name`, or `id` in the returned `graph_context`. Update `expected_graph_neighbors` documentation in Section 6 with the canonical form.

4. **project_id filtering effectiveness** — read the retriever and the Chroma/Neo4j query code to verify that `project_id=99999` actually scopes queries (not just tags inserted data). If it does not filter on read, the EVAL_PROJECT_ID isolation is a lie and we need a different isolation mechanism (separate Chroma collection name, separate Neo4j database).

5. **Embedding generation path during indexing** — the config sets `CODE_GRAPH_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"` (a local Hugging Face model). Confirm whether `graph_builder` uses this local model end-to-end during indexing or also calls the ZhipuAI API somewhere. Two implications:
   - If purely local: CI does not need a real `ZHIPUAI_API_KEY`, and we must arrange to cache the bge model weights between CI runs (~100MB, otherwise CI cold start downloads it every time and may exceed the 5-minute budget).
   - If ZhipuAI API is required: CI needs `ZHIPUAI_API_KEY` as a repository secret, fork PRs will not have access to it, and the `evals-smoke` job must gracefully skip with a clear message on forks.

All five TBDs must be resolved before any metric code is written. Resolution updates this spec inline.

## 17. README additions (Phase 0 housekeeping, done alongside this)

A new "Evaluation" section in the project README explaining:

- What evals measures (retrieval quality only in v1)
- How to run locally (one command)
- Where to find results (`evals/results/`)
- Why EVAL_PROJECT_ID=99999 means a separate index from your dev work
- One-paragraph note that generation and agent metrics are planned but not in v1

## 18. Suggested commit order

1. Spec + scaffolding (this doc + empty package skeleton + `.gitkeep`s)
2. `validate.py` + `test_validate.py` (the schema guardrail comes first; everything else depends on golden cases existing)
3. Pure-function metrics module + `test_metrics.py`
4. `reporter.py` + `test_reporter.py` (table + JSON, no I/O surprises)
5. `runner.py` + `run.py` (the wiring; no new logic)
6. AI-drafted `backend_fastapi.draft.jsonl` (50 candidates)
7. Human-reviewed `backend_fastapi.jsonl` (final 30-50)
8. `mini_fixture/` code + `mini_fixture.jsonl`
9. `--index-corpus` implementation (depends on TBD #2 being resolved)
10. CI `evals-smoke` job in `.github/workflows/ci.yml`
11. README evaluation section

Each step is independently testable; steps 1-5 require no real Neo4j/Chroma.
