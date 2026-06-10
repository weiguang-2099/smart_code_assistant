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
