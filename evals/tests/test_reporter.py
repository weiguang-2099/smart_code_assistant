import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from evals.generation import GenerationResult
from evals.reporter import compute_aggregate, compute_generation_aggregate, render_table, write_json
from evals.runner import CaseResult


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
        assert loaded["cases"][0]["generation"] is None
        assert loaded["aggregate"]["overall"]["n"] == 1

    def test_roundtrip_with_generation(self, tmp_path):
        results = [_gen_case("g1", 4, 5)]
        aggregate = compute_aggregate(results)
        out_path = tmp_path / "result.json"

        write_json(out_path, {"case_count": 1}, results, aggregate)

        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        gen = loaded["cases"][0]["generation"]
        assert gen["faithfulness"] == 4
        assert gen["answer_relevance"] == 5
        assert gen["error"] is None


def _gen_case(case_id, faith, rel, *, error=None, parse_errors=0):
    return CaseResult(
        id=case_id, category="definition_lookup", expected_files=["app/a.py"],
        expected_graph_neighbors=None,
        generation=GenerationResult(
            answer="a", faithfulness=faith, answer_relevance=rel,
            judge_parse_errors=parse_errors, error=error,
        ),
    )


class TestComputeGenerationAggregate:
    def test_no_generation_returns_none(self):
        plain = CaseResult(id="x", category="definition_lookup",
                           expected_files=[], expected_graph_neighbors=None)
        assert compute_generation_aggregate([plain]) is None

    def test_means_and_pct_ge_4(self):
        cases = [_gen_case("a", 5, 4), _gen_case("b", 3, 2), _gen_case("c", 4, 5)]
        agg = compute_generation_aggregate(cases)
        assert agg["n"] == 3
        assert agg["faithfulness"] == 4.0
        assert agg["faithfulness_pct_ge_4"] == round(2 / 3, 4)
        assert agg["answer_relevance_pct_ge_4"] == round(2 / 3, 4)

    def test_errors_and_nulls_excluded_from_means(self):
        cases = [
            _gen_case("ok", 5, 5),
            _gen_case("err", None, None, error="generation: boom"),
            _gen_case("parse", None, 4, parse_errors=1),
        ]
        agg = compute_generation_aggregate(cases)
        assert agg["n"] == 3
        assert agg["gen_errors"] == 1
        assert agg["gen_error_rate"] == round(1 / 3, 4)
        assert agg["judge_parse_errors"] == 1
        assert agg["faithfulness"] == 5.0       # only the one non-null value
        assert agg["faithfulness_n"] == 1
        assert agg["answer_relevance_n"] == 2

    def test_by_category_breakdown(self):
        cases = [_gen_case("a", 5, 4), _gen_case("b", 3, 2)]
        agg = compute_generation_aggregate(cases)
        cat = agg["by_category"]["definition_lookup"]
        assert cat["n"] == 2
        assert cat["faithfulness"] == 4.0
        assert cat["answer_relevance"] == 3.0


class TestGenerationTableSection:
    def test_render_includes_generation_when_present(self):
        aggregate = {
            "overall": {"n": 2, "errors": 0, "hit_rate@5": 0.5},
            "by_category": {},
            "generation": {
                "n": 2, "gen_errors": 0, "gen_error_rate": 0.0,
                "judge_parse_errors": 0,
                "faithfulness": 4.5, "faithfulness_pct_ge_4": 1.0, "faithfulness_n": 2,
                "answer_relevance": 4.0, "answer_relevance_pct_ge_4": 0.5,
                "answer_relevance_n": 2,
            },
        }
        out = render_table(aggregate)
        assert "==== Generation" in out
        assert "faithfulness" in out

    def test_render_unchanged_without_generation(self):
        aggregate = {"overall": {"n": 1, "errors": 0, "hit_rate@5": 1.0}, "by_category": {}}
        assert "Generation" not in render_table(aggregate)
