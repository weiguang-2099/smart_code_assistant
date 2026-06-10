# Phase 1 Evaluation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable `evals/` package that measures retrieval and graph-traversal quality of the GraphRAG system against a golden set, writes timestamped JSON results, and runs as a CI smoke job with zero new Python dependencies.

**Architecture:** Standalone top-level `evals/` package that imports `CodeGraphRetriever` directly (no HTTP). Pure-function metrics in `evals/metrics/`, async per-case runner with `asyncio.Semaphore`, hand-rolled table+JSON reporter. CI uses GHA service containers for Neo4j 5.15 + ChromaDB and indexes a tiny `evals/fixtures/mini_repo/` on the fly.

**Tech Stack:** Python 3.11, stdlib only (json, asyncio, argparse, dataclasses, pathlib, subprocess), pytest 8.3, existing backend-fastapi requirements transitively.

**Spec reference:** `docs/superpowers/specs/2026-06-10-evals-harness-design.md`

---

## Task 1: Resolve the 5 implementation-time TBDs

**Goal:** Read existing source to lock down chunk metadata format, graph_builder signature, neighbor identity, project_id filter semantics, and embedding path. Update the spec inline with findings before any code is written.

**Files:**
- Read: `backend-fastapi/app/services/code_graph/retriever.py`
- Read: `backend-fastapi/app/services/code_graph/chromadb_client.py`
- Read: `backend-fastapi/app/services/code_graph/graph_builder.py`
- Read: `backend-fastapi/app/services/code_graph/neo4j_client.py`
- Read: `backend-fastapi/app/services/code_graph/entity_extractor.py`
- Read: `backend-fastapi/app/services/code_graph/config.py`
- Modify: `docs/superpowers/specs/2026-06-10-evals-harness-design.md` (Section 16)

- [ ] **Step 1: Resolve TBD #1 (chunk metadata + path format)**

Open `backend-fastapi/app/services/code_graph/chromadb_client.py` and the part of `retriever.py` that processes `semantic_results`. Find:
- What key on each returned chunk dict holds the file path (`metadata.file_path`? `metadata.path`? `metadata.source`? top-level `file_path`?)
- What root the stored path is relative to (`/abs/.../backend-fastapi/app/main.py`? `backend-fastapi/app/main.py`? `app/main.py`? `main.py`?)

Record both as a single concrete answer.

- [ ] **Step 2: Resolve TBD #2 (graph_builder interface)**

Open `backend-fastapi/app/services/code_graph/graph_builder.py`. Find:
- The public function used to index a directory (name, sync/async, signature)
- Required arguments (path? project_id? any embedding model handle?)
- Any side effects on Neo4j+Chroma the eval harness must know about (does it wipe existing data? does it idempotently upsert?)

- [ ] **Step 3: Resolve TBD #3 (graph neighbor identity)**

Open `neo4j_client.py` and `entity_extractor.py`. For each neighbor node returned in `graph_context`, find which field is the canonical name (`name`, `qualified_name`, `id`, or a tuple). Record the field name and an example string format (e.g., `"app.core.rate_limiter.setup_rate_limiting"` vs `"setup_rate_limiting"`).

- [ ] **Step 4: Resolve TBD #4 (project_id filter scope)**

In `chromadb_client.py` and `neo4j_client.py`, trace how `project_id` parameter flows through query calls. Confirm whether:
- ChromaDB queries include `where={"project_id": ...}` on retrieve, OR
- Neo4j Cypher includes `WHERE n.project_id = $project_id`, OR
- Filtering happens nowhere (data is just tagged, retrieve returns global results)

If filtering is absent on read, EVAL_PROJECT_ID isolation is broken — record what alternative isolation (separate Chroma collection name, separate Neo4j database) would work.

- [ ] **Step 5: Resolve TBD #5 (embedding path)**

Open `chromadb_client.py` and `graph_builder.py`. Find what generates embeddings during index time:
- Local: a `sentence_transformers.SentenceTransformer("BAAI/bge-small-zh-v1.5")` loaded once and reused, OR
- Remote: a ZhipuAI Embedding API call (e.g., `client.embeddings.create(model="embedding-2", input=text)`)

Record which one. If local: note the model size for CI caching planning. If remote: note that CI needs a real key.

- [ ] **Step 6: Update spec Section 16**

Edit `docs/superpowers/specs/2026-06-10-evals-harness-design.md`. Replace the bullet items in Section 16 with the concrete findings. Each former TBD becomes a "Resolved:" paragraph stating the answer and citing the source file:line.

Example resolution format:

```markdown
1. **Chunk metadata field name and path format — Resolved**:
   In `chromadb_client.py:NNN`, chunks return as dicts with `metadata.file_path` holding repo-relative paths starting with `backend-fastapi/`. Eval harness will strip the `backend-fastapi/` prefix when comparing against `expected_files` in golden cases (which start with `app/`).
```

- [ ] **Step 7: Commit the spec update**

```bash
git add docs/superpowers/specs/2026-06-10-evals-harness-design.md
git commit -m "docs(evals): resolve 5 implementation-time TBDs in spec"
```

---

## Task 2: Scaffold the evals package

**Goal:** Create the directory tree and stub files so `python -c "import evals"` succeeds and subsequent TDD tasks can place code in the right place.

**Files:**
- Create: `evals/__init__.py`
- Create: `evals/config.py`
- Create: `evals/run.py` (stub)
- Create: `evals/runner.py` (stub)
- Create: `evals/reporter.py` (stub)
- Create: `evals/metrics/__init__.py`
- Create: `evals/metrics/retrieval.py` (stub)
- Create: `evals/metrics/graph.py` (stub)
- Create: `evals/golden_set/__init__.py`
- Create: `evals/golden_set/validate.py` (stub)
- Create: `evals/fixtures/__init__.py`
- Create: `evals/results/.gitkeep`
- Create: `evals/tests/__init__.py`
- Create: `evals/tests/conftest.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create `evals/__init__.py`**

```python
"""Evaluation harness for Smart Code Assistant's GraphRAG retrieval.

This package imports ``app.services.code_graph.*`` from ``backend-fastapi/`` and
needs that directory on sys.path before any submodule loads it. The path
manipulation is done here in __init__ so every entry into the package (CLI,
tests, library import) sees the same path setup.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_PATH = _REPO_ROOT / "backend-fastapi"
if str(_BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PATH))
```

- [ ] **Step 2: Create `evals/config.py`**

```python
"""Constants for the evaluation harness. Edit here, not in CLI defaults."""

EVAL_PROJECT_ID = 99999

K_VALUES = (1, 3, 5, 10)

DEFAULT_TOP_K = 10
DEFAULT_MAX_DEPTH = 2
DEFAULT_CONCURRENCY = 5
DEFAULT_PER_CASE_TIMEOUT_S = 30.0
DEFAULT_OUTPUT_DIR = "evals/results"

CATEGORIES = (
    "definition_lookup",
    "feature_lookup",
    "dependency_trace",
    "impact_analysis",
    "cross_file_flow",
)
```

- [ ] **Step 3: Create stub modules**

Each stub contains only a docstring so imports succeed:

`evals/run.py`:
```python
"""Argparse entry point. Implemented in Task 8."""
```

`evals/runner.py`:
```python
"""Async per-case retrieve loop. Implemented in Task 7."""
```

`evals/reporter.py`:
```python
"""Table + JSON output. Implemented in Task 6."""
```

`evals/metrics/__init__.py`:
```python
"""Pure-function metric implementations. Implemented in Tasks 3-4."""
```

`evals/metrics/retrieval.py`:
```python
"""Retrieval metrics. Implemented in Task 3."""
```

`evals/metrics/graph.py`:
```python
"""Graph traversal metrics. Implemented in Task 4."""
```

`evals/golden_set/__init__.py`:
```python
"""Golden set storage + validation. Implemented in Task 5."""
```

`evals/golden_set/validate.py`:
```python
"""Golden set schema validator. Implemented in Task 5."""
```

`evals/fixtures/__init__.py`:
```python
"""Minimal code fixture for CI. Populated in Task 9."""
```

`evals/tests/__init__.py`:
```python
```

(Empty file is fine.)

- [ ] **Step 4: Create `evals/tests/conftest.py`**

```python
"""Shared pytest fixtures for evals unit tests.

Evals tests must not require Neo4j/ChromaDB to run. Any fixture defined here
should be in-memory only.
"""
```

- [ ] **Step 5: Create `evals/results/.gitkeep`**

Empty file — keeps the directory in git while letting runs write JSON to it.

```bash
touch evals/results/.gitkeep
```

(On Windows PowerShell: `New-Item -ItemType File evals/results/.gitkeep`)

- [ ] **Step 6: Update `.gitignore`**

Append to `.gitignore`:

```
# Evals runtime output
evals/results/*.json
evals/golden_set/*.draft.jsonl
```

- [ ] **Step 7: Verify imports work**

Run from repo root:

```bash
python -c "import evals; import evals.config; import evals.runner; import evals.reporter; import evals.metrics.retrieval; import evals.metrics.graph; import evals.golden_set.validate; print('ok')"
```

Expected output: `ok`

- [ ] **Step 8: Commit scaffold**

```bash
git add evals/ .gitignore
git commit -m "feat(evals): scaffold package structure and config constants"
```

---

## Task 3: Implement retrieval metrics with TDD

**Goal:** Pure-function `hit_rate_at_k`, `precision_at_k`, `recall_at_k`, `mrr` in `evals/metrics/retrieval.py`. Tests run without Neo4j/ChromaDB.

**Files:**
- Modify: `evals/metrics/retrieval.py`
- Create: `evals/tests/test_retrieval_metrics.py`

- [ ] **Step 1: Write failing tests for `hit_rate_at_k`**

Create `evals/tests/test_retrieval_metrics.py`:

```python
import pytest

from evals.metrics.retrieval import hit_rate_at_k, precision_at_k, recall_at_k, mrr


class TestHitRateAtK:
    def test_top1_hit(self):
        assert hit_rate_at_k(["a.py", "b.py", "c.py"], ["a.py"], k=1) == 1

    def test_top1_miss(self):
        assert hit_rate_at_k(["x.py", "a.py"], ["a.py"], k=1) == 0

    def test_top5_hit_at_rank3(self):
        assert hit_rate_at_k(["x.py", "y.py", "a.py", "z.py"], ["a.py"], k=5) == 1

    def test_no_hit_in_topk(self):
        assert hit_rate_at_k(["x.py", "y.py", "z.py"], ["a.py"], k=2) == 0

    def test_empty_expected(self):
        # Schema validation should reject this case, but the metric must be safe.
        assert hit_rate_at_k(["a.py"], [], k=1) == 0

    def test_multiple_expected_any_match(self):
        assert hit_rate_at_k(["a.py", "b.py"], ["c.py", "b.py"], k=2) == 1
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
pytest evals/tests/test_retrieval_metrics.py::TestHitRateAtK -v
```

Expected: All tests fail with `ImportError: cannot import name 'hit_rate_at_k' from 'evals.metrics.retrieval'`.

- [ ] **Step 3: Implement `hit_rate_at_k`**

Replace `evals/metrics/retrieval.py`:

```python
"""Retrieval metrics. Chunk-ranked (hit_rate/precision/mrr) and file-coverage (recall)."""
from typing import Sequence


def hit_rate_at_k(retrieved_files: Sequence[str], expected: Sequence[str], k: int) -> int:
    """1 if any of top-k retrieved chunks has a file_path in expected, else 0."""
    expected_set = set(expected)
    if not expected_set:
        return 0
    return int(any(f in expected_set for f in retrieved_files[:k]))
```

- [ ] **Step 4: Run tests, confirm they pass**

```bash
pytest evals/tests/test_retrieval_metrics.py::TestHitRateAtK -v
```

Expected: 6 passed.

- [ ] **Step 5: Append failing tests for `precision_at_k`**

Append to `evals/tests/test_retrieval_metrics.py`:

```python
class TestPrecisionAtK:
    def test_all_hits(self):
        assert precision_at_k(["a.py", "b.py"], ["a.py", "b.py"], k=2) == 1.0

    def test_half_hits(self):
        assert precision_at_k(["a.py", "x.py"], ["a.py"], k=2) == 0.5

    def test_denominator_is_k_not_returned(self):
        # Even when retriever returns only 2 chunks, precision@5 divides by 5.
        assert precision_at_k(["a.py", "b.py"], ["a.py", "b.py"], k=5) == pytest.approx(0.4)

    def test_no_hit(self):
        assert precision_at_k(["x.py", "y.py"], ["a.py"], k=2) == 0.0

    def test_duplicates_count_separately(self):
        # Same file appearing twice in top-k is NOT deduplicated for precision.
        assert precision_at_k(["a.py", "a.py", "b.py"], ["a.py"], k=3) == pytest.approx(2 / 3)
```

- [ ] **Step 6: Run tests, confirm they fail**

```bash
pytest evals/tests/test_retrieval_metrics.py::TestPrecisionAtK -v
```

Expected: `ImportError: cannot import name 'precision_at_k'`.

- [ ] **Step 7: Implement `precision_at_k`**

Append to `evals/metrics/retrieval.py`:

```python
def precision_at_k(retrieved_files: Sequence[str], expected: Sequence[str], k: int) -> float:
    """Chunk-based, no dedup. Denominator is k (not the actual returned count)."""
    if k <= 0:
        return 0.0
    expected_set = set(expected)
    hits = sum(1 for f in retrieved_files[:k] if f in expected_set)
    return hits / k
```

- [ ] **Step 8: Run tests, confirm they pass**

```bash
pytest evals/tests/test_retrieval_metrics.py::TestPrecisionAtK -v
```

Expected: 5 passed.

- [ ] **Step 9: Append failing tests for `recall_at_k`**

Append to `evals/tests/test_retrieval_metrics.py`:

```python
class TestRecallAtK:
    def test_full_recall_single_expected(self):
        assert recall_at_k(["a.py", "b.py"], ["a.py"], k=2) == 1.0

    def test_partial_recall_multi_expected(self):
        # Found a.py but not b.py.
        assert recall_at_k(["a.py", "x.py"], ["a.py", "b.py"], k=2) == 0.5

    def test_recall_dedupes_files_in_topk(self):
        # 3 chunks all from a.py — recall over {a, c} is still 0.5, not 1.
        assert recall_at_k(["a.py", "a.py", "a.py"], ["a.py", "c.py"], k=3) == 0.5

    def test_recall_chunks_beyond_k_ignored(self):
        # c.py is at rank 5, k=3, so it shouldn't count.
        assert recall_at_k(["a.py", "x.py", "y.py", "z.py", "c.py"], ["a.py", "c.py"], k=3) == 0.5

    def test_empty_expected_returns_zero(self):
        assert recall_at_k(["a.py"], [], k=1) == 0.0

    def test_recall_full_with_duplicates(self):
        # Both expected files appear; duplicates don't penalize.
        assert recall_at_k(["a.py", "b.py", "a.py"], ["a.py", "b.py"], k=3) == 1.0
```

- [ ] **Step 10: Run tests, confirm they fail**

```bash
pytest evals/tests/test_retrieval_metrics.py::TestRecallAtK -v
```

Expected: `ImportError`.

- [ ] **Step 11: Implement `recall_at_k`**

Append to `evals/metrics/retrieval.py`:

```python
def recall_at_k(retrieved_files: Sequence[str], expected: Sequence[str], k: int) -> float:
    """File-coverage recall: unique files in top-k chunks vs expected set."""
    expected_set = set(expected)
    if not expected_set:
        return 0.0
    unique_topk = set(retrieved_files[:k])
    return len(unique_topk & expected_set) / len(expected_set)
```

- [ ] **Step 12: Run tests, confirm they pass**

```bash
pytest evals/tests/test_retrieval_metrics.py::TestRecallAtK -v
```

Expected: 6 passed.

- [ ] **Step 13: Append failing tests for `mrr`**

Append to `evals/tests/test_retrieval_metrics.py`:

```python
class TestMRR:
    def test_first_chunk_hit(self):
        assert mrr(["a.py", "b.py"], ["a.py"]) == 1.0

    def test_third_chunk_hit(self):
        assert mrr(["x.py", "y.py", "a.py"], ["a.py"]) == pytest.approx(1 / 3)

    def test_no_hit_returns_zero(self):
        assert mrr(["x.py", "y.py"], ["a.py"]) == 0.0

    def test_no_cap_at_k(self):
        # MRR searches the entire list, not truncated to k.
        retrieved = ["x.py"] * 20 + ["a.py"]
        assert mrr(retrieved, ["a.py"]) == pytest.approx(1 / 21)

    def test_empty_expected(self):
        assert mrr(["a.py", "b.py"], []) == 0.0
```

- [ ] **Step 14: Run tests, confirm they fail, implement, confirm they pass**

```bash
pytest evals/tests/test_retrieval_metrics.py::TestMRR -v
```

Expected: `ImportError`.

Append to `evals/metrics/retrieval.py`:

```python
def mrr(retrieved_files: Sequence[str], expected: Sequence[str]) -> float:
    """First relevant chunk's reciprocal rank. Chunks are the ranking unit; no dedup."""
    expected_set = set(expected)
    if not expected_set:
        return 0.0
    for rank, f in enumerate(retrieved_files, start=1):
        if f in expected_set:
            return 1.0 / rank
    return 0.0
```

Re-run:

```bash
pytest evals/tests/test_retrieval_metrics.py -v
```

Expected: 22 passed (6 + 5 + 6 + 5).

- [ ] **Step 15: Commit**

```bash
git add evals/metrics/retrieval.py evals/tests/test_retrieval_metrics.py
git commit -m "feat(evals): retrieval metrics (hit_rate, precision, recall, mrr) with tests"
```

---

## Task 4: Implement graph metrics with TDD

**Goal:** Pure-function `graph_neighbor_recall`, `graph_neighbor_precision`, `graph_traversal_correctness`, `hybrid_hit_rate_at_k` in `evals/metrics/graph.py`. Null-safe for cases without `expected_graph_neighbors`.

**Files:**
- Modify: `evals/metrics/graph.py`
- Create: `evals/tests/test_graph_metrics.py`

- [ ] **Step 1: Write failing tests for graph metrics**

Create `evals/tests/test_graph_metrics.py`:

```python
import pytest

from evals.metrics.graph import (
    graph_neighbor_recall,
    graph_neighbor_precision,
    graph_traversal_correctness,
    hybrid_hit_rate_at_k,
)


class TestGraphNeighborRecall:
    def test_full_recall(self):
        assert graph_neighbor_recall({"a", "b", "c"}, {"a", "b"}) == 1.0

    def test_half_recall(self):
        assert graph_neighbor_recall({"a", "x"}, {"a", "b"}) == 0.5

    def test_zero_recall(self):
        assert graph_neighbor_recall({"x"}, {"a", "b"}) == 0.0

    def test_none_expected_returns_none(self):
        # Case without expected_graph_neighbors: skip aggregation.
        assert graph_neighbor_recall({"a"}, None) is None

    def test_empty_expected_returns_none(self):
        assert graph_neighbor_recall({"a"}, set()) is None

    def test_none_retrieved_with_expected(self):
        assert graph_neighbor_recall(None, {"a", "b"}) == 0.0


class TestGraphNeighborPrecision:
    def test_full_precision(self):
        assert graph_neighbor_precision({"a", "b"}, {"a", "b"}) == 1.0

    def test_half_precision(self):
        # Retrieved 4 nodes, 2 are expected.
        assert graph_neighbor_precision({"a", "b", "x", "y"}, {"a", "b"}) == 0.5

    def test_empty_retrieved_returns_zero(self):
        assert graph_neighbor_precision(set(), {"a"}) == 0.0

    def test_none_expected_returns_none(self):
        assert graph_neighbor_precision({"a"}, None) is None


class TestGraphTraversalCorrectness:
    def test_strict_superset_passes(self):
        assert graph_traversal_correctness({"a", "b", "extra"}, {"a", "b"}) == 1

    def test_exact_match_passes(self):
        assert graph_traversal_correctness({"a", "b"}, {"a", "b"}) == 1

    def test_missing_one_fails(self):
        assert graph_traversal_correctness({"a"}, {"a", "b"}) == 0

    def test_none_expected_returns_none(self):
        assert graph_traversal_correctness({"a"}, None) is None


class TestHybridHitRateAtK:
    def test_file_hit_only(self):
        assert hybrid_hit_rate_at_k(
            retrieved_files=["a.py", "b.py"], expected_files={"a.py"},
            retrieved_neighbors=set(), expected_neighbors={"foo"}, k=5,
        ) == 1

    def test_graph_hit_only(self):
        assert hybrid_hit_rate_at_k(
            retrieved_files=["x.py"], expected_files={"a.py"},
            retrieved_neighbors={"foo"}, expected_neighbors={"foo"}, k=5,
        ) == 1

    def test_neither_hits(self):
        assert hybrid_hit_rate_at_k(
            retrieved_files=["x.py"], expected_files={"a.py"},
            retrieved_neighbors=set(), expected_neighbors={"foo"}, k=5,
        ) == 0

    def test_none_expected_neighbors_falls_back_to_file(self):
        # No graph expectation; file hit alone is enough.
        assert hybrid_hit_rate_at_k(
            retrieved_files=["a.py"], expected_files={"a.py"},
            retrieved_neighbors=None, expected_neighbors=None, k=5,
        ) == 1
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
pytest evals/tests/test_graph_metrics.py -v
```

Expected: ImportError for the four functions.

- [ ] **Step 3: Implement `evals/metrics/graph.py`**

Replace contents:

```python
"""Graph traversal metrics. All accept ``None`` expected sets and return ``None`` in
that case, so the aggregator can skip them rather than averaging zeros."""
from typing import Iterable, Optional, Sequence


def graph_neighbor_recall(
    retrieved: Optional[Iterable[str]],
    expected: Optional[Iterable[str]],
) -> Optional[float]:
    """|retrieved ∩ expected| / |expected|, or None if expected is null/empty."""
    if expected is None:
        return None
    expected_set = set(expected)
    if not expected_set:
        return None
    retrieved_set = set(retrieved or [])
    return len(retrieved_set & expected_set) / len(expected_set)


def graph_neighbor_precision(
    retrieved: Optional[Iterable[str]],
    expected: Optional[Iterable[str]],
) -> Optional[float]:
    """|retrieved ∩ expected| / |retrieved|, 0 when retrieved is empty, None when expected is null."""
    if expected is None:
        return None
    retrieved_set = set(retrieved or [])
    if not retrieved_set:
        return 0.0
    expected_set = set(expected)
    return len(retrieved_set & expected_set) / len(retrieved_set)


def graph_traversal_correctness(
    retrieved: Optional[Iterable[str]],
    expected: Optional[Iterable[str]],
) -> Optional[int]:
    """1 if retrieved is a superset of expected, else 0; None if expected is null/empty."""
    if expected is None:
        return None
    expected_set = set(expected)
    if not expected_set:
        return None
    retrieved_set = set(retrieved or [])
    return int(expected_set.issubset(retrieved_set))


def hybrid_hit_rate_at_k(
    retrieved_files: Sequence[str],
    expected_files: Iterable[str],
    retrieved_neighbors: Optional[Iterable[str]],
    expected_neighbors: Optional[Iterable[str]],
    k: int,
) -> int:
    """1 if EITHER top-k chunk file matches expected_files OR retrieved graph
    neighbors overlap expected_neighbors. Used as the GraphRAG headline metric."""
    e_files = set(expected_files)
    file_hit = any(f in e_files for f in retrieved_files[:k])

    if expected_neighbors:
        e_neighbors = set(expected_neighbors)
        r_neighbors = set(retrieved_neighbors or [])
        graph_hit = bool(e_neighbors & r_neighbors)
    else:
        graph_hit = False

    return int(file_hit or graph_hit)
```

- [ ] **Step 4: Run tests, confirm they pass**

```bash
pytest evals/tests/test_graph_metrics.py -v
```

Expected: 18 passed (6 + 4 + 4 + 4).

- [ ] **Step 5: Commit**

```bash
git add evals/metrics/graph.py evals/tests/test_graph_metrics.py
git commit -m "feat(evals): graph metrics + hybrid_hit_rate with null-safe semantics"
```

---

## Task 5: Implement golden set validator with TDD

**Goal:** `evals/golden_set/validate.py` parses JSONL, enforces schema, checks expected_files exist on disk, warns on missing optional fields. Used by CLI before any eval runs and as a standalone CI sanity check.

**Note:** This task assumes Task 1 (TBD #1) has confirmed the path-resolution convention. If TBD #1 reveals expected_files do not use the `app/` prefix, adjust the `_resolve_repo_path` helper accordingly.

**Files:**
- Modify: `evals/golden_set/validate.py`
- Create: `evals/tests/test_validate.py`

- [ ] **Step 1: Write failing tests**

Create `evals/tests/test_validate.py`:

```python
import json
from pathlib import Path

import pytest

from evals.golden_set.validate import validate_case, validate_golden_set


@pytest.fixture
def fake_repo(tmp_path):
    """Layout matching backend-fastapi/app/<file> so paths like
    ``app/core/rate_limiter.py`` resolve under the temp repo root."""
    (tmp_path / "backend-fastapi" / "app" / "core").mkdir(parents=True)
    (tmp_path / "backend-fastapi" / "app" / "core" / "rate_limiter.py").write_text("# stub")
    (tmp_path / "backend-fastapi" / "app" / "main.py").write_text("# stub")
    return tmp_path


def valid_case():
    return {
        "id": "test-001",
        "question": "How does X work?",
        "category": "feature_lookup",
        "expected_files": ["app/core/rate_limiter.py"],
    }


class TestValidateCase:
    def test_minimal_valid_case_passes(self, fake_repo):
        errors, warnings = validate_case(valid_case(), fake_repo, line_number=1)
        assert errors == []

    def test_missing_required_field_fails(self, fake_repo):
        case = valid_case()
        del case["category"]
        errors, _ = validate_case(case, fake_repo, line_number=1)
        assert any("category" in e for e in errors)

    def test_bad_category_fails(self, fake_repo):
        case = valid_case()
        case["category"] = "something_random"
        errors, _ = validate_case(case, fake_repo, line_number=1)
        assert any("category" in e for e in errors)

    def test_missing_expected_file_on_disk_fails(self, fake_repo):
        case = valid_case()
        case["expected_files"] = ["app/does_not_exist.py"]
        errors, _ = validate_case(case, fake_repo, line_number=1)
        assert any("does_not_exist" in e for e in errors)

    def test_expected_files_must_be_list(self, fake_repo):
        case = valid_case()
        case["expected_files"] = "app/main.py"  # string instead of list
        errors, _ = validate_case(case, fake_repo, line_number=1)
        assert any("list" in e.lower() for e in errors)

    def test_unknown_field_fails(self, fake_repo):
        case = valid_case()
        case["random_field"] = "x"
        errors, _ = validate_case(case, fake_repo, line_number=1)
        assert any("random_field" in e for e in errors)

    def test_missing_optional_fields_warn(self, fake_repo):
        errors, warnings = validate_case(valid_case(), fake_repo, line_number=1)
        assert errors == []
        assert any("expected_symbols" in w for w in warnings)
        assert any("expected_graph_neighbors" in w for w in warnings)

    def test_empty_expected_files_fails(self, fake_repo):
        case = valid_case()
        case["expected_files"] = []
        errors, _ = validate_case(case, fake_repo, line_number=1)
        assert any("expected_files" in e for e in errors)


class TestValidateGoldenSet:
    def test_valid_file_passes(self, fake_repo, tmp_path):
        jsonl = tmp_path / "golden.jsonl"
        jsonl.write_text(json.dumps(valid_case()) + "\n", encoding="utf-8")
        errors, _ = validate_golden_set(jsonl, fake_repo)
        assert errors == []

    def test_duplicate_id_across_lines_fails(self, fake_repo, tmp_path):
        case_a = valid_case()
        case_b = valid_case()  # same id
        jsonl = tmp_path / "golden.jsonl"
        jsonl.write_text(json.dumps(case_a) + "\n" + json.dumps(case_b) + "\n", encoding="utf-8")
        errors, _ = validate_golden_set(jsonl, fake_repo)
        assert any("duplicate" in e for e in errors)

    def test_invalid_json_line_reports_line_number(self, fake_repo, tmp_path):
        jsonl = tmp_path / "golden.jsonl"
        jsonl.write_text(json.dumps(valid_case()) + "\n{not valid json\n", encoding="utf-8")
        errors, _ = validate_golden_set(jsonl, fake_repo)
        assert any("line 2" in e for e in errors)

    def test_blank_lines_skipped(self, fake_repo, tmp_path):
        jsonl = tmp_path / "golden.jsonl"
        jsonl.write_text(json.dumps(valid_case()) + "\n\n", encoding="utf-8")
        errors, _ = validate_golden_set(jsonl, fake_repo)
        assert errors == []
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
pytest evals/tests/test_validate.py -v
```

Expected: `ImportError: cannot import name 'validate_case'`.

- [ ] **Step 3: Implement `evals/golden_set/validate.py`**

Replace contents:

```python
"""Golden set schema validator. Run before any eval to fail fast on bad input."""
import json
from pathlib import Path
from typing import Iterable

from evals.config import CATEGORIES

REQUIRED_FIELDS = ("id", "question", "category", "expected_files")
OPTIONAL_FIELDS = ("expected_symbols", "expected_graph_neighbors", "notes")
ALLOWED_FIELDS = set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)


def _resolve_repo_path(expected_path: str, repo_root: Path) -> Path:
    """Map a golden case path (e.g. 'app/core/rate_limiter.py') to a file on disk.

    Adjust this function if Task 1 (TBD #1) reveals a different path convention.
    """
    return repo_root / "backend-fastapi" / expected_path


def validate_case(
    case: dict, repo_root: Path, line_number: int
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a single case. Caller decides how to report."""
    errors: list[str] = []
    warnings: list[str] = []
    prefix = f"line {line_number}"

    # required field presence
    for field in REQUIRED_FIELDS:
        if field not in case:
            errors.append(f"{prefix}: missing required field '{field}'")
            continue
        value = case[field]
        if value in (None, "", []):
            errors.append(f"{prefix}: required field '{field}' is empty")

    # type checks (only run if field exists)
    if isinstance(case.get("id"), str) is False and "id" in case:
        errors.append(f"{prefix}: 'id' must be a string")

    if "category" in case and case["category"] not in CATEGORIES:
        errors.append(
            f"{prefix}: invalid category '{case['category']}'; "
            f"must be one of {CATEGORIES}"
        )

    if "expected_files" in case:
        value = case["expected_files"]
        if not isinstance(value, list):
            errors.append(f"{prefix}: 'expected_files' must be a list")
        else:
            for path_str in value:
                if not isinstance(path_str, str):
                    errors.append(f"{prefix}: expected_files entries must be strings")
                    continue
                full_path = _resolve_repo_path(path_str, repo_root)
                if not full_path.exists():
                    errors.append(
                        f"{prefix}: expected_files path not found on disk: {path_str}"
                    )

    # optional-field warnings
    if "expected_symbols" not in case:
        warnings.append(f"{prefix}: 'expected_symbols' missing (optional in v1)")
    if "expected_graph_neighbors" not in case:
        warnings.append(
            f"{prefix}: 'expected_graph_neighbors' missing (optional in v1)"
        )

    # unknown fields
    unknown = set(case.keys()) - ALLOWED_FIELDS
    if unknown:
        errors.append(f"{prefix}: unknown fields: {sorted(unknown)}")

    return errors, warnings


def validate_golden_set(
    jsonl_path: Path, repo_root: Path
) -> tuple[list[str], list[str]]:
    """Validate every case in a JSONL file. Returns aggregated (errors, warnings)."""
    all_errors: list[str] = []
    all_warnings: list[str] = []
    seen_ids: set[str] = set()

    with jsonl_path.open(encoding="utf-8") as f:
        for line_number, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                case = json.loads(raw)
            except json.JSONDecodeError as e:
                all_errors.append(f"line {line_number}: invalid JSON: {e.msg}")
                continue

            case_id = case.get("id")
            if isinstance(case_id, str):
                if case_id in seen_ids:
                    all_errors.append(
                        f"line {line_number}: duplicate id '{case_id}'"
                    )
                else:
                    seen_ids.add(case_id)

            case_errors, case_warnings = validate_case(case, repo_root, line_number)
            all_errors.extend(case_errors)
            all_warnings.extend(case_warnings)

    return all_errors, all_warnings
```

- [ ] **Step 4: Run tests, confirm they pass**

```bash
pytest evals/tests/test_validate.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add evals/golden_set/validate.py evals/tests/test_validate.py
git commit -m "feat(evals): golden set schema validator (errors + optional-field warnings)"
```

---

## Task 6: Implement reporter (compute_aggregate + render_table + write_json) with TDD

**Goal:** `evals/reporter.py` aggregates per-case metrics into overall + per-category means, renders the stdout table from Section 7.6 of the spec, and writes the JSON result schema from Section 10.

**Files:**
- Modify: `evals/reporter.py`
- Create: `evals/tests/test_reporter.py`

- [ ] **Step 1: Write failing tests**

Create `evals/tests/test_reporter.py`:

```python
import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from evals.reporter import compute_aggregate, render_table, write_json


@dataclass
class FakeCaseResult:
    """Mirrors runner.CaseResult shape just enough for reporter tests."""
    id: str
    category: str
    expected_files: list = field(default_factory=list)
    expected_graph_neighbors: list | None = None
    retrieved_files_ranked: list = field(default_factory=list)
    retrieved_graph_neighbors: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    error: str | None = None


def make_case(category="feature_lookup", metrics=None, error=None):
    return FakeCaseResult(
        id=f"case-{id(metrics)}",
        category=category,
        metrics=metrics or {},
        error=error,
    )


class TestComputeAggregate:
    def test_macro_average_overall(self):
        results = [
            make_case(metrics={"hit_rate@5": 1, "mrr": 1.0}),
            make_case(metrics={"hit_rate@5": 0, "mrr": 0.5}),
        ]
        agg = compute_aggregate(results)
        assert agg["overall"]["n"] == 2
        assert agg["overall"]["errors"] == 0
        assert agg["overall"]["hit_rate@5"] == 0.5
        assert agg["overall"]["mrr"] == 0.75

    def test_null_metrics_excluded_from_denominator(self):
        results = [
            make_case(metrics={"graph_neighbor_recall": None, "hit_rate@5": 1}),
            make_case(metrics={"graph_neighbor_recall": 0.5, "hit_rate@5": 1}),
        ]
        agg = compute_aggregate(results)
        assert agg["overall"]["graph_neighbor_recall"] == 0.5  # only 1 contributed
        assert agg["overall"]["hit_rate@5"] == 1.0

    def test_errored_cases_counted_but_metrics_excluded(self):
        results = [
            make_case(metrics={"hit_rate@5": 1}),
            make_case(error="timeout"),
        ]
        agg = compute_aggregate(results)
        assert agg["overall"]["n"] == 2
        assert agg["overall"]["errors"] == 1
        assert agg["overall"]["hit_rate@5"] == 1.0

    def test_by_category_breakdown(self):
        results = [
            make_case(category="definition_lookup", metrics={"hit_rate@5": 1}),
            make_case(category="definition_lookup", metrics={"hit_rate@5": 1}),
            make_case(category="feature_lookup", metrics={"hit_rate@5": 0}),
        ]
        agg = compute_aggregate(results)
        assert agg["by_category"]["definition_lookup"]["n"] == 2
        assert agg["by_category"]["definition_lookup"]["hit_rate@5"] == 1.0
        assert agg["by_category"]["feature_lookup"]["n"] == 1
        assert agg["by_category"]["feature_lookup"]["hit_rate@5"] == 0.0


class TestRenderTable:
    def test_table_includes_overall_and_categories(self):
        agg = {
            "overall": {"n": 3, "errors": 0, "hit_rate@5": 0.667, "mrr": 0.5},
            "by_category": {
                "definition_lookup": {"n": 2, "hit_rate@5": 1.0, "mrr": 0.75},
            },
        }
        out = render_table(agg)
        assert "Overall" in out
        assert "n=3" in out
        assert "hit_rate@5" in out
        assert "definition_lookup" in out

    def test_table_handles_missing_metric_keys(self):
        # Aggregate may not have every metric key (e.g., no graph cases at all).
        agg = {
            "overall": {"n": 1, "errors": 0, "hit_rate@5": 1.0},
            "by_category": {"feature_lookup": {"n": 1, "hit_rate@5": 1.0}},
        }
        out = render_table(agg)  # must not raise
        assert "graph_neighbor_recall" not in out  # only present keys rendered


class TestWriteJson:
    def test_roundtrip(self, tmp_path):
        meta = {
            "timestamp": "2026-06-10T14:00:00Z",
            "git_sha": "abc1234",
            "git_dirty": True,
            "golden_set": "evals/golden_set/test.jsonl",
            "indexed_corpus": None,
            "case_count": 1,
            "config": {"top_k": 10, "max_depth": 2, "project_id": 99999, "concurrency": 5},
        }
        results = [make_case(metrics={"hit_rate@5": 1, "mrr": 0.5})]
        aggregate = compute_aggregate(results)
        out_path = tmp_path / "result.json"

        write_json(out_path, meta, results, aggregate)

        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        assert loaded["meta"]["git_sha"] == "abc1234"
        assert loaded["meta"]["git_dirty"] is True
        assert len(loaded["cases"]) == 1
        assert loaded["cases"][0]["metrics"]["hit_rate@5"] == 1
        assert loaded["aggregate"]["overall"]["n"] == 1
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
pytest evals/tests/test_reporter.py -v
```

Expected: ImportError for `compute_aggregate`, `render_table`, `write_json`.

- [ ] **Step 3: Implement `evals/reporter.py`**

Replace contents:

```python
"""Aggregate per-case results, render the stdout table, write the JSON result file."""
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def compute_aggregate(case_results: Iterable[Any]) -> dict:
    """Macro-average metrics across cases.

    - errored cases contribute to ``errors`` but not to any metric mean
    - ``None`` metric values are excluded from per-metric denominators
    """
    results = list(case_results)
    total = len(results)
    errors = sum(1 for r in results if r.error)

    overall_metrics: dict[str, list] = defaultdict(list)
    by_category_metrics: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    by_category_n: dict[str, int] = defaultdict(int)

    for r in results:
        if r.error:
            continue
        by_category_n[r.category] += 1
        for name, value in r.metrics.items():
            if value is None:
                continue
            overall_metrics[name].append(value)
            by_category_metrics[r.category][name].append(value)

    overall = {"n": total, "errors": errors}
    for name, values in overall_metrics.items():
        overall[name] = round(sum(values) / len(values), 4)

    by_category: dict[str, dict] = {}
    for cat, n in by_category_n.items():
        cat_block: dict[str, Any] = {"n": n}
        for name, values in by_category_metrics[cat].items():
            cat_block[name] = round(sum(values) / len(values), 4)
        by_category[cat] = cat_block

    return {"overall": overall, "by_category": by_category}


# Order matters for the stdout table; entries not present in aggregate are skipped.
_OVERALL_KEY_ORDER = (
    "hit_rate@1",
    "hit_rate@5",
    "recall@5",
    "precision@5",
    "mrr",
    "graph_neighbor_recall",
    "graph_traversal_correctness",
    "hybrid_hit_rate@5",
)

_CATEGORY_COLUMNS = ("hit_rate@5", "recall@5", "mrr")


def render_table(aggregate: dict) -> str:
    """Render aggregate as the human-readable table from spec Section 7.6."""
    overall = aggregate["overall"]
    lines = [
        f"==== Overall (n={overall['n']}, errors={overall.get('errors', 0)}) ====",
    ]
    for key in _OVERALL_KEY_ORDER:
        if key in overall:
            lines.append(f"{key:<28}  {overall[key]}")

    if aggregate["by_category"]:
        lines.append("")
        lines.append("==== By category ====")
        header = f"{'category':<22}{'n':>4}"
        for col in _CATEGORY_COLUMNS:
            header += f"  {col:>10}"
        lines.append(header)
        for cat, vals in aggregate["by_category"].items():
            row = f"{cat:<22}{vals['n']:>4}"
            for col in _CATEGORY_COLUMNS:
                cell = vals.get(col, "-")
                row += f"  {cell!s:>10}"
            lines.append(row)

    return "\n".join(lines)


def write_json(out_path: Path, meta: dict, results: Iterable[Any], aggregate: dict) -> None:
    """Write the full result JSON to ``out_path``. Caller must ensure parent dir exists."""
    payload = {
        "meta": meta,
        "cases": [
            {
                "id": r.id,
                "category": r.category,
                "expected_files": r.expected_files,
                "expected_graph_neighbors": r.expected_graph_neighbors,
                "retrieved_files_ranked": r.retrieved_files_ranked,
                "retrieved_graph_neighbors": r.retrieved_graph_neighbors,
                "metrics": r.metrics,
                "error": r.error,
            }
            for r in results
        ],
        "aggregate": aggregate,
    }
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
```

- [ ] **Step 4: Run tests, confirm they pass**

```bash
pytest evals/tests/test_reporter.py -v
```

Expected: 7 passed (4 aggregate + 2 render + 1 json).

- [ ] **Step 5: Run all evals tests together to confirm no regressions**

```bash
pytest evals/tests/ -v
```

Expected: 59 tests passing (22 retrieval + 18 graph + 12 validate + 7 reporter).

- [ ] **Step 6: Commit**

```bash
git add evals/reporter.py evals/tests/test_reporter.py
git commit -m "feat(evals): aggregate + table + JSON reporter"
```

---

## Task 7: Implement runner (async per-case retrieve loop)

**Goal:** `evals/runner.py` loads cases, calls the live `CodeGraphRetriever` per case with bounded concurrency, handles timeouts and exceptions per case, returns `CaseResult` dataclass instances. **No e2e tests** — verified by Task 9 (CI smoke) and local manual runs.

**Files:**
- Modify: `evals/runner.py`

- [ ] **Step 1: Implement `runner.py`**

Note: this file uses two extraction helpers (`extract_files_from_retrieval` and `extract_neighbors_from_graph`) whose internals depend on Task 1's TBD findings. The code below shows the format **expected**; adjust the metadata key access lines after reading the actual `chromadb_client.py` / `neo4j_client.py`.

Replace `evals/runner.py`:

```python
"""Async per-case retrieve loop. Calls CodeGraphRetriever directly (not HTTP)."""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

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


def extract_files_from_retrieval(semantic_results: Sequence[dict]) -> list[str]:
    """Extract chunk file paths in rank order.

    The field name below (``metadata.file_path``) is the assumption pending Task 1
    TBD #1 resolution. After reading chromadb_client.py, replace this line with
    the confirmed accessor.
    """
    files: list[str] = []
    for chunk in semantic_results:
        if not isinstance(chunk, dict):
            continue
        metadata = chunk.get("metadata") or {}
        file_path = metadata.get("file_path")
        if not file_path:
            continue
        # Golden cases use 'app/...' paths; strip 'backend-fastapi/' if present.
        if file_path.startswith("backend-fastapi/"):
            file_path = file_path[len("backend-fastapi/"):]
        files.append(file_path)
    return files


def extract_neighbors_from_graph(graph_context: Optional[dict]) -> list[str]:
    """Extract neighbor node identifiers from graph_context.

    Adjust after Task 1 confirms whether nodes use 'name', 'qualified_name', or 'id'.
    """
    if not graph_context:
        return []
    neighbors: list[str] = []
    raw_nodes = graph_context.get("neighbors") or graph_context.get("nodes") or []
    for node in raw_nodes:
        if isinstance(node, str):
            neighbors.append(node)
            continue
        if isinstance(node, dict):
            identifier = node.get("qualified_name") or node.get("name") or node.get("id")
            if identifier:
                neighbors.append(identifier)
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
```

- [ ] **Step 2: Confirm imports still resolve**

```bash
python -c "import evals.runner; print(evals.runner.CaseResult)"
```

Expected: `<class 'evals.runner.CaseResult'>`

- [ ] **Step 3: Smoke-test that load_golden_set works on a tiny in-memory file**

```bash
python -c "
from pathlib import Path
import tempfile, json
from evals.runner import load_golden_set
with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
    f.write(json.dumps({'id': 'x', 'question': '?', 'category': 'feature_lookup', 'expected_files': ['app/main.py']}) + '\n')
    p = Path(f.name)
cases = load_golden_set(p)
print('loaded', len(cases), 'cases')
"
```

Expected: `loaded 1 cases`

- [ ] **Step 4: Commit**

```bash
git add evals/runner.py
git commit -m "feat(evals): async per-case runner with bounded concurrency and timeout"
```

---

## Task 8: Implement CLI entry point (run.py)

**Goal:** `python -m evals.run --golden ...` wires validate → load → (optional index) → retriever instantiation → run_corpus → reporter. Exit codes match spec Section 8.

**Files:**
- Modify: `evals/run.py`

- [ ] **Step 1: Implement `run.py`**

Replace `evals/run.py`:

```python
"""CLI entry point: python -m evals.run --golden ..."""
import argparse
import asyncio
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import evals  # noqa: F401  -- triggers sys.path setup before app.* imports

from evals.config import (
    DEFAULT_CONCURRENCY,
    DEFAULT_MAX_DEPTH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PER_CASE_TIMEOUT_S,
    DEFAULT_TOP_K,
    EVAL_PROJECT_ID,
)
from evals.golden_set.validate import validate_golden_set
from evals.reporter import compute_aggregate, render_table, write_json
from evals.runner import load_golden_set, run_corpus

REPO_ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger("evals")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m evals.run")
    p.add_argument("--golden", required=True, type=Path,
                   help="Path to golden set JSONL")
    p.add_argument("--index-corpus", type=Path, default=None,
                   help="If given, index this directory before evaluating")
    p.add_argument("--project-id", type=int, default=EVAL_PROJECT_ID)
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    p.add_argument("--categories", type=str, default=None,
                   help="Comma-separated category filter")
    p.add_argument("--limit", type=int, default=None,
                   help="Only run first N cases")
    p.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--quiet", action="store_true",
                   help="Only print JSON path on success")
    return p.parse_args(argv)


def git_meta() -> tuple[str | None, bool | None]:
    """Return (short_sha, dirty_bool) or (None, None) if git is unavailable."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=REPO_ROOT, text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        )
        return sha, dirty
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None


async def _do_index(corpus_path: Path, project_id: int) -> None:
    """Index the corpus into Neo4j+Chroma via the existing graph_builder.

    The function name and signature here depend on Task 1 TBD #2. Adjust the
    import and call site after reading graph_builder.py.
    """
    from app.services.code_graph.graph_builder import build_graph_from_directory  # noqa: WPS433
    await build_graph_from_directory(str(corpus_path), project_id=project_id)


async def main_async(args: argparse.Namespace) -> int:
    # 1. Validate golden set
    errors, warnings = validate_golden_set(args.golden, REPO_ROOT)
    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 2

    cases = load_golden_set(args.golden)
    if args.categories:
        allowed = {c.strip() for c in args.categories.split(",") if c.strip()}
        cases = [c for c in cases if c["category"] in allowed]
    if args.limit:
        cases = cases[: args.limit]

    # 2. Optional indexing step
    if args.index_corpus:
        try:
            await _do_index(args.index_corpus, args.project_id)
        except Exception as exc:
            print(f"ERROR: --index-corpus failed: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            return 3

    # 3. Build retriever
    try:
        from app.services.code_graph.retriever import CodeGraphRetriever
        retriever = CodeGraphRetriever()
    except Exception as exc:
        print(f"ERROR: cannot initialize retriever: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 3

    # 4. Run
    results = await run_corpus(
        cases, retriever,
        top_k=args.top_k, max_depth=args.max_depth,
        project_id=args.project_id, concurrency=args.concurrency,
        timeout_s=DEFAULT_PER_CASE_TIMEOUT_S,
    )

    # 5. Build meta + aggregate + persist
    sha, dirty = git_meta()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "timestamp": timestamp,
        "git_sha": sha,
        "git_dirty": dirty,
        "golden_set": str(args.golden),
        "indexed_corpus": str(args.index_corpus) if args.index_corpus else None,
        "case_count": len(results),
        "config": {
            "top_k": args.top_k,
            "max_depth": args.max_depth,
            "project_id": args.project_id,
            "concurrency": args.concurrency,
        },
    }
    aggregate = compute_aggregate(results)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    safe_ts = timestamp.replace(":", "").replace("-", "")
    out_path = args.output_dir / f"{safe_ts}.json"

    try:
        write_json(out_path, meta, results, aggregate)
    except OSError as exc:
        # Still print metrics to stdout so a write failure doesn't lose info.
        print(f"WARN: could not write result file: {exc}", file=sys.stderr)
        print(render_table(aggregate))
        return 0

    if args.quiet:
        print(str(out_path))
    else:
        print(render_table(aggregate))
        print(f"\nWrote {out_path}")
    return 0


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI parses (no real Neo4j needed)**

```bash
python -m evals.run --help
```

Expected: argparse usage block listing all flags from Section 8 of the spec.

- [ ] **Step 3: Verify validation path on a bad file returns exit 2**

```bash
python -m evals.run --golden evals/golden_set/does_not_exist.jsonl
```

Expected output:
```
ERROR: ...does_not_exist.jsonl...
```
Exit code: 2 (check `echo $?` on bash or `$LASTEXITCODE` on PowerShell).

- [ ] **Step 4: Commit**

```bash
git add evals/run.py
git commit -m "feat(evals): CLI entry point with validate + index + retrieve + report"
```

---

## Task 9: Create CI fixture (mini_repo) + golden set

**Goal:** A self-contained 8-10 Python file corpus under `evals/fixtures/mini_repo/` and 10-15 hand-authored golden cases in `evals/golden_set/mini_fixture.jsonl`. CI indexes this and runs evals against it in under a minute.

**Files:**
- Create: `evals/fixtures/mini_repo/__init__.py`
- Create: `evals/fixtures/mini_repo/auth.py`
- Create: `evals/fixtures/mini_repo/db.py`
- Create: `evals/fixtures/mini_repo/cache.py`
- Create: `evals/fixtures/mini_repo/api.py`
- Create: `evals/fixtures/mini_repo/middleware.py`
- Create: `evals/fixtures/mini_repo/models.py`
- Create: `evals/fixtures/mini_repo/utils.py`
- Create: `evals/fixtures/mini_repo/errors.py`
- Create: `evals/golden_set/mini_fixture.jsonl`

- [ ] **Step 1: Create fixture files with realistic but tiny code**

Each file ~20-40 lines, with realistic imports/calls between them so graph traversal has something to find.

`evals/fixtures/mini_repo/errors.py`:

```python
"""Custom exception types used across the mini fixture."""


class AuthError(Exception):
    """Raised when authentication fails."""


class NotFoundError(Exception):
    """Raised when a record lookup misses."""


class CacheMissError(Exception):
    """Raised when a required cache entry is absent."""
```

`evals/fixtures/mini_repo/db.py`:

```python
"""Synchronous in-memory DB used by the fixture services."""
from evals.fixtures.mini_repo.errors import NotFoundError

_USERS: dict[int, dict] = {}


def insert_user(user_id: int, name: str, email: str) -> None:
    _USERS[user_id] = {"id": user_id, "name": name, "email": email}


def get_user(user_id: int) -> dict:
    user = _USERS.get(user_id)
    if user is None:
        raise NotFoundError(f"user {user_id} not found")
    return user


def delete_user(user_id: int) -> None:
    _USERS.pop(user_id, None)
```

`evals/fixtures/mini_repo/cache.py`:

```python
"""Simple in-process cache for user lookups."""
from evals.fixtures.mini_repo.errors import CacheMissError

_CACHE: dict[str, object] = {}


def set_cache(key: str, value: object) -> None:
    _CACHE[key] = value


def get_cache(key: str) -> object:
    if key not in _CACHE:
        raise CacheMissError(key)
    return _CACHE[key]


def invalidate(key: str) -> None:
    _CACHE.pop(key, None)
```

`evals/fixtures/mini_repo/auth.py`:

```python
"""Token-based auth checks built on top of the DB layer."""
from evals.fixtures.mini_repo.db import get_user
from evals.fixtures.mini_repo.errors import AuthError

_TOKENS: dict[str, int] = {}


def issue_token(user_id: int, token: str) -> None:
    _TOKENS[token] = user_id


def authenticate(token: str) -> dict:
    if token not in _TOKENS:
        raise AuthError("invalid token")
    return get_user(_TOKENS[token])
```

`evals/fixtures/mini_repo/models.py`:

```python
"""Plain data classes."""
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str


@dataclass
class Session:
    token: str
    user: User
```

`evals/fixtures/mini_repo/utils.py`:

```python
"""Helpers that don't fit elsewhere."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def make_session_id(user_id: int, salt: str) -> str:
    return f"{user_id}-{salt}"
```

`evals/fixtures/mini_repo/middleware.py`:

```python
"""Request-scoped middleware that uses auth + cache."""
from evals.fixtures.mini_repo.auth import authenticate
from evals.fixtures.mini_repo.cache import get_cache, set_cache
from evals.fixtures.mini_repo.errors import CacheMissError


def load_request_user(token: str) -> dict:
    try:
        return get_cache(token)
    except CacheMissError:
        user = authenticate(token)
        set_cache(token, user)
        return user
```

`evals/fixtures/mini_repo/api.py`:

```python
"""Top-level API handlers that everyone else feeds into."""
from evals.fixtures.mini_repo.middleware import load_request_user
from evals.fixtures.mini_repo.db import insert_user, delete_user
from evals.fixtures.mini_repo.utils import normalize_email


def create_user(user_id: int, name: str, email: str) -> dict:
    insert_user(user_id, name, normalize_email(email))
    return {"id": user_id, "name": name}


def whoami(token: str) -> dict:
    return load_request_user(token)


def remove_user(token: str, user_id: int) -> None:
    load_request_user(token)
    delete_user(user_id)
```

`evals/fixtures/mini_repo/__init__.py`:

```python
"""Minimal code fixture: an in-memory user service spread across 8 files."""
```

- [ ] **Step 2: Author `evals/golden_set/mini_fixture.jsonl`**

Each line is one case. The paths assume your TBD #1 resolution maps `evals/fixtures/mini_repo/X.py` to itself (no `app/` prefix for fixture cases — adjust if the validator's `_resolve_repo_path` needs to be made fixture-aware). If validation fails due to path prefix mismatch, either add a `--fixture-mode` flag to the validator or change the case paths to whatever convention the validator accepts.

```jsonl
{"id":"mini-001","question":"Where is the AuthError exception defined?","category":"definition_lookup","expected_files":["evals/fixtures/mini_repo/errors.py"],"expected_symbols":["AuthError"]}
{"id":"mini-002","question":"How does token authentication work?","category":"feature_lookup","expected_files":["evals/fixtures/mini_repo/auth.py"],"expected_symbols":["authenticate"]}
{"id":"mini-003","question":"How is a request user loaded with caching?","category":"feature_lookup","expected_files":["evals/fixtures/mini_repo/middleware.py"],"expected_symbols":["load_request_user"],"expected_graph_neighbors":["authenticate","get_cache","set_cache"]}
{"id":"mini-004","question":"Which file defines the User dataclass?","category":"definition_lookup","expected_files":["evals/fixtures/mini_repo/models.py"],"expected_symbols":["User"]}
{"id":"mini-005","question":"How is a user removed from the system?","category":"cross_file_flow","expected_files":["evals/fixtures/mini_repo/api.py","evals/fixtures/mini_repo/db.py"],"expected_symbols":["remove_user","delete_user"],"expected_graph_neighbors":["load_request_user","delete_user"]}
{"id":"mini-006","question":"What calls insert_user?","category":"dependency_trace","expected_files":["evals/fixtures/mini_repo/api.py"],"expected_symbols":["create_user"],"expected_graph_neighbors":["create_user"]}
{"id":"mini-007","question":"Where is the cache implementation located?","category":"feature_lookup","expected_files":["evals/fixtures/mini_repo/cache.py"],"expected_symbols":["set_cache","get_cache","invalidate"]}
{"id":"mini-008","question":"If get_user is renamed, which files need updates?","category":"impact_analysis","expected_files":["evals/fixtures/mini_repo/auth.py","evals/fixtures/mini_repo/db.py"],"expected_graph_neighbors":["authenticate"]}
{"id":"mini-009","question":"Where is email normalized?","category":"definition_lookup","expected_files":["evals/fixtures/mini_repo/utils.py"],"expected_symbols":["normalize_email"]}
{"id":"mini-010","question":"How is whoami implemented end to end?","category":"cross_file_flow","expected_files":["evals/fixtures/mini_repo/api.py","evals/fixtures/mini_repo/middleware.py","evals/fixtures/mini_repo/auth.py"],"expected_symbols":["whoami","load_request_user","authenticate"],"expected_graph_neighbors":["load_request_user","authenticate","get_cache"]}
{"id":"mini-011","question":"Which file defines CacheMissError?","category":"definition_lookup","expected_files":["evals/fixtures/mini_repo/errors.py"],"expected_symbols":["CacheMissError"]}
{"id":"mini-012","question":"What invalidates a cache entry?","category":"dependency_trace","expected_files":["evals/fixtures/mini_repo/cache.py"],"expected_symbols":["invalidate"]}
```

- [ ] **Step 3: If the validator's `_resolve_repo_path` prefix breaks fixture validation, adjust the validator**

The current `_resolve_repo_path(p, repo_root)` returns `repo_root / "backend-fastapi" / p`. For fixture paths like `evals/fixtures/mini_repo/db.py` this resolves to `<root>/backend-fastapi/evals/fixtures/mini_repo/db.py` which does not exist. Fix by detecting the `evals/` prefix:

Update `_resolve_repo_path` in `evals/golden_set/validate.py`:

```python
def _resolve_repo_path(expected_path: str, repo_root: Path) -> Path:
    """Map a golden case path to a file on disk.

    Convention:
    - Paths starting with 'evals/' resolve relative to repo root (fixture cases).
    - Anything else is treated as a backend-fastapi/-relative path.
    """
    if expected_path.startswith("evals/"):
        return repo_root / expected_path
    return repo_root / "backend-fastapi" / expected_path
```

Add a regression test in `evals/tests/test_validate.py`:

```python
def test_fixture_path_resolution(tmp_path):
    (tmp_path / "evals" / "fixtures" / "mini_repo").mkdir(parents=True)
    (tmp_path / "evals" / "fixtures" / "mini_repo" / "auth.py").write_text("# stub")
    case = {
        "id": "fix-001",
        "question": "?",
        "category": "feature_lookup",
        "expected_files": ["evals/fixtures/mini_repo/auth.py"],
    }
    errors, _ = validate_case(case, tmp_path, line_number=1)
    assert errors == []
```

- [ ] **Step 4: Run validator on the fixture golden set**

```bash
python -c "
from pathlib import Path
from evals.golden_set.validate import validate_golden_set
errs, warns = validate_golden_set(Path('evals/golden_set/mini_fixture.jsonl'), Path('.'))
print(f'errors={len(errs)} warnings={len(warns)}')
for e in errs: print('  ERR:', e)
"
```

Expected: `errors=0 warnings=24` (each of 12 cases produces 2 warnings for missing optional fields; 8 cases have `expected_graph_neighbors` so warnings are lower).

- [ ] **Step 5: Run the full evals test suite**

```bash
pytest evals/tests/ -v
```

Expected: all green, including the new fixture path resolution test.

- [ ] **Step 6: Commit**

```bash
git add evals/fixtures/ evals/golden_set/mini_fixture.jsonl evals/golden_set/validate.py evals/tests/test_validate.py
git commit -m "feat(evals): mini_repo fixture (8 files, 12 golden cases) for CI smoke"
```

---

## Task 10: Add CI evals-smoke job

**Goal:** Append a new GHA job to `.github/workflows/ci.yml` that runs the eval unit tests and the mini_fixture smoke eval with Neo4j+Chroma service containers. Uploads JSON result as artifact. Does not block other jobs.

**Note:** The `ZHIPUAI_API_KEY` env entry below assumes Task 1 TBD #5 resolved to "local bge model" (no real key needed). If TBD #5 resolved to "remote API required," replace `ci-test-key` with `${{ secrets.ZHIPUAI_API_KEY }}` and add `if: ${{ github.event.pull_request.head.repo.fork == false }}` to the job to skip on fork PRs.

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Append the new job to `ci.yml`**

Open `.github/workflows/ci.yml`. After the `frontend:` job's final line, add:

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
        ports:
          - 7687:7687
          - 7474:7474
        options: >-
          --health-cmd "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 10
      chromadb:
        image: chromadb/chroma:latest
        ports:
          - 8001:8000
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
          CHROMADB_PORT: "8001"
          ZHIPUAI_API_KEY: ci-test-key
          SECRET_KEY: ci-secret-key-for-tests-only
        run: |
          python -m evals.run \
            --golden evals/golden_set/mini_fixture.jsonl \
            --index-corpus evals/fixtures/mini_repo
      - name: Upload evals results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: evals-results
          path: evals/results/*.json
          retention-days: 30
```

- [ ] **Step 2: Validate the YAML syntax locally**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

Expected: no output (success). If `yaml` is not available, use `python -c "import json; print(open('.github/workflows/ci.yml').read()[:200])"` as a quick sanity check, then push and rely on GitHub's parser.

- [ ] **Step 3: Commit and push to a PR branch to verify the job runs**

```bash
git add .github/workflows/ci.yml
git commit -m "ci(evals): add evals-smoke job with neo4j+chroma service containers"
```

Push to a branch, open a PR, and watch the new `Evals - retrieval smoke` job:
- If the job finishes under 5 min with all steps green: success.
- If it times out: open the indexing step's log to see whether neo4j startup or fixture indexing is the bottleneck; reduce mini_fixture files if needed.
- If the embedding step fails with "401 Unauthorized" or similar: Task 1 TBD #5 was misread; switch to `${{ secrets.ZHIPUAI_API_KEY }}` per the note above.

---

## Task 11: Generate AI-drafted backend_fastapi golden set

**Goal:** Produce ~50 candidate golden cases for self-eval against `backend-fastapi/app/`. The output is a draft file; the human user reviews and finalizes (Task 12, outside this implementation flow).

**Files:**
- Create: `evals/golden_set/backend_fastapi.draft.jsonl`
- Read: `backend-fastapi/app/core/rate_limiter.py`
- Read: `backend-fastapi/app/core/sentry.py`
- Read: `backend-fastapi/app/core/telemetry.py`
- Read: `backend-fastapi/app/core/cache.py`
- Read: `backend-fastapi/app/api/auth.py`
- Read: `backend-fastapi/app/api/agent.py`
- Read: `backend-fastapi/app/api/code_graph.py`
- Read: `backend-fastapi/app/services/code_graph/retriever.py`
- Read: `backend-fastapi/app/services/code_graph/graph_builder.py`
- Read: `backend-fastapi/app/services/conversation_manager.py`
- Read: `backend-fastapi/app/services/glm_service.py`

- [ ] **Step 1: For each target module, read the file and extract candidate question seeds**

For each target file, look at:
- The exported function or class (gives a `definition_lookup` candidate)
- What the module's docstring or top-level comment says it does (gives a `feature_lookup` candidate)
- Its imports (which give `dependency_trace` candidates against the imported targets)
- Cross-module call sites (give `cross_file_flow` and `impact_analysis` candidates)

Target distribution to draft:

| category | count |
|---|---|
| definition_lookup | 12 |
| feature_lookup | 12 |
| dependency_trace | 10 |
| impact_analysis | 8 |
| cross_file_flow | 8 |

Total: 50 candidates.

- [ ] **Step 2: Write candidates as JSONL with verified `expected_files`**

For every candidate, before adding it to the file:
- Open the candidate's `expected_files` paths in the repo and confirm the file exists and the named symbol is actually in it.
- For `expected_graph_neighbors`, infer statically from imports/call sites; mark these as low-confidence in `notes` so the reviewer knows they're not Neo4j-verified.

Write to `evals/golden_set/backend_fastapi.draft.jsonl`. Example two lines:

```jsonl
{"id":"rate-limiter-001","question":"How is per-user rate limiting wired into FastAPI?","category":"feature_lookup","expected_files":["app/core/rate_limiter.py","app/main.py"],"expected_symbols":["setup_rate_limiting"],"expected_graph_neighbors":["slowapi.Limiter"],"notes":"graph neighbors inferred statically; verify against actual Neo4j"}
{"id":"sentry-001","question":"Where is Sentry initialized?","category":"definition_lookup","expected_files":["app/core/sentry.py"],"expected_symbols":["init_sentry"]}
```

(Continue with 48 more lines in the same style.)

- [ ] **Step 3: Run the validator on the draft**

```bash
python -c "
from pathlib import Path
from evals.golden_set.validate import validate_golden_set
errs, warns = validate_golden_set(Path('evals/golden_set/backend_fastapi.draft.jsonl'), Path('.'))
print(f'errors={len(errs)}')
for e in errs[:20]: print('  ERR:', e)
"
```

Expected: `errors=0`. If errors appear, fix the offending paths and re-run.

- [ ] **Step 4: Commit the draft for the user to review**

The `.draft.jsonl` extension matches the `.gitignore` exclusion from Task 2, so explicit `-f` is needed:

```bash
git add -f evals/golden_set/backend_fastapi.draft.jsonl
git commit -m "feat(evals): AI-drafted 50 candidate golden cases for backend self-eval"
```

Tell the user: "Draft committed to `evals/golden_set/backend_fastapi.draft.jsonl`. Review, trim/correct to 30-50 keepers, then save as `evals/golden_set/backend_fastapi.jsonl` (without `.draft`) and remove the `-f` requirement by ungitignoring the final filename."

---

## Task 12: Add README evaluation section

**Goal:** Document the evals harness in the project README so a reviewer can find and run it without reading the spec.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Find the right insertion point**

Open `README.md`. The spec recommends placing the evaluation section between the existing "Testing" section and the "Deployment" / quickstart area. If unsure, insert it just before "## Tech Stack."

- [ ] **Step 2: Add the section**

Insert:

```markdown
## Evaluation

The retrieval quality of the GraphRAG pipeline is measured by an automated eval harness in `evals/`.

### What it measures (v1)

Retrieval-only metrics on a fixed golden set of code questions:

- `hit_rate@k`, `precision@k`, `recall@k`, `mrr` over ChromaDB chunks
- `graph_neighbor_recall`, `graph_traversal_correctness` over Neo4j traversal
- `hybrid_hit_rate@k` — the headline GraphRAG-vs-plain-RAG metric

LLM-as-judge generation metrics and agent trajectory metrics are planned but not in v1.

### Run locally

Index `backend-fastapi/` under the eval project id (one-time setup):

```bash
python -m app.services.code_graph.graph_builder --path backend-fastapi/app --project-id 99999
```

Then run evals:

```bash
python -m evals.run --golden evals/golden_set/backend_fastapi.jsonl
```

Results are written to `evals/results/{timestamp}.json`. A summary table prints to stdout.

### CI

Every PR runs `evals-smoke` against the `mini_repo` fixture in `evals/fixtures/`, takes ~2 minutes, and uploads the result JSON as an artifact. The job reports metrics but does not gate merge in v1.

### Why `EVAL_PROJECT_ID = 99999`

Evals run under a dedicated project id to isolate the eval index from your real dev data in Neo4j and ChromaDB. This means you maintain two indices of the same code: the dev one (under your usual project id) and the eval one (under 99999). The cost is disk space; the benefit is that running evals never sees noise from other projects.

See `docs/superpowers/specs/2026-06-10-evals-harness-design.md` for the full design.
```

- [ ] **Step 3: Verify markdown renders correctly**

```bash
python -c "open('README.md').read()" 2>&1 | head -5
```

(Manual check by opening in a markdown previewer if available.)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add evaluation section to README"
```

---

## Self-Review

After all tasks land, run this checklist:

### Spec coverage

Map every spec section to a task:

- Section 4 (Architecture): Tasks 2, 7, 8
- Section 5 (Component layout): Task 2
- Section 6 (Golden case schema): Tasks 5, 9, 11
- Section 7 (Metrics): Tasks 3, 4
- Section 8 (CLI): Task 8
- Section 9 (Run flows): Tasks 8, 10
- Section 10 (JSON result schema): Tasks 6, 8
- Section 11 (Error handling): Tasks 5, 7, 8
- Section 12 (Concurrency): Task 7
- Section 13 (Testing strategy): Tasks 3-6
- Section 14 (Dependencies): Task 2 (none added)
- Section 15 (CI integration): Task 10
- Section 16 (TBDs): Task 1
- Section 17 (README): Task 12

### Final smoke

```bash
pytest evals/tests/ -v
python -m evals.run --help
```

Expected: all tests pass, help text prints.
