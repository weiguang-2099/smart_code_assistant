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
