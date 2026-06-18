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
