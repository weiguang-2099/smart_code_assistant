"""Aggregate per-case results, render the stdout table, write the JSON result file."""
import json
from collections import defaultdict
from dataclasses import asdict
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


_GEN_METRIC_KEYS = ("faithfulness", "answer_relevance")


def compute_generation_aggregate(case_results: Iterable[Any]) -> "dict | None":
    """Aggregate GenerationResults, overall and per category (spec 7.3).

    - returns None when no case carries one, so retrieval-only runs get no
      aggregate section (per-case dicts still gain ``generation: null``)
    - null scores are excluded from means
    - per-metric sample size is reported
    """
    annotated = [r for r in case_results if getattr(r, "generation", None) is not None]
    if not annotated:
        return None
    gens = [r.generation for r in annotated]
    n = len(gens)
    gen_errors = sum(1 for g in gens if g.error)
    block: dict[str, Any] = {
        "n": n,
        "gen_errors": gen_errors,
        "gen_error_rate": round(gen_errors / n, 4),
        "judge_parse_errors": sum(g.judge_parse_errors for g in gens),
    }
    for key in _GEN_METRIC_KEYS:
        values = [getattr(g, key) for g in gens if getattr(g, key) is not None]
        if values:
            block[key] = round(sum(values) / len(values), 4)
            block[f"{key}_pct_ge_4"] = round(sum(1 for v in values if v >= 4) / len(values), 4)
            block[f"{key}_n"] = len(values)

    by_category: dict[str, dict] = {}
    cat_cases: dict[str, list] = defaultdict(list)
    for r in annotated:
        cat_cases[r.category].append(r.generation)
    for cat, cat_gens in cat_cases.items():
        cat_block: dict[str, Any] = {"n": len(cat_gens)}
        for key in _GEN_METRIC_KEYS:
            values = [getattr(g, key) for g in cat_gens if getattr(g, key) is not None]
            if values:
                cat_block[key] = round(sum(values) / len(values), 4)
        by_category[cat] = cat_block
    block["by_category"] = by_category
    return block


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

    gen = aggregate.get("generation")
    if gen is not None:
        lines.append("")
        lines.append(
            f"==== Generation (n={gen['n']}, gen_errors={gen['gen_errors']}, "
            f"judge_parse_errors={gen['judge_parse_errors']}) ===="
        )
        for key in _GEN_METRIC_KEYS:
            if key in gen:
                lines.append(
                    f"{key:<28}  {gen[key]}  (>=4: {gen[f'{key}_pct_ge_4']:.0%}, "
                    f"n={gen[f'{key}_n']})"
                )

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
                "generation": (
                    None if getattr(r, "generation", None) is None
                    else asdict(r.generation)
                ),
            }
            for r in results
        ],
        "aggregate": aggregate,
    }
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
