"""Retrieval metrics. Chunk-ranked (hit_rate/precision/mrr) and file-coverage (recall)."""
from typing import Sequence


def hit_rate_at_k(retrieved_files: Sequence[str], expected: Sequence[str], k: int) -> int:
    """1 if any of top-k retrieved chunks has a file_path in expected, else 0."""
    expected_set = set(expected)
    if not expected_set:
        return 0
    return int(any(f in expected_set for f in retrieved_files[:k]))


def precision_at_k(retrieved_files: Sequence[str], expected: Sequence[str], k: int) -> float:
    """Chunk-based, no dedup. Denominator is k (not the actual returned count)."""
    if k <= 0:
        return 0.0
    expected_set = set(expected)
    hits = sum(1 for f in retrieved_files[:k] if f in expected_set)
    return hits / k


def recall_at_k(retrieved_files: Sequence[str], expected: Sequence[str], k: int) -> float:
    """File-coverage recall: unique files in top-k chunks vs expected set."""
    expected_set = set(expected)
    if not expected_set:
        return 0.0
    unique_topk = set(retrieved_files[:k])
    return len(unique_topk & expected_set) / len(expected_set)


def mrr(retrieved_files: Sequence[str], expected: Sequence[str]) -> float:
    """First relevant chunk's reciprocal rank. Chunks are the ranking unit; no dedup."""
    expected_set = set(expected)
    if not expected_set:
        return 0.0
    for rank, f in enumerate(retrieved_files, start=1):
        if f in expected_set:
            return 1.0 / rank
    return 0.0
