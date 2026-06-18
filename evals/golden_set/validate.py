"""Golden set schema validator. Run before any eval to fail fast on bad input."""
import json
from pathlib import Path
from typing import Iterable

from evals.config import CATEGORIES

REQUIRED_FIELDS = ("id", "question", "category", "expected_files")
OPTIONAL_FIELDS = ("expected_symbols", "expected_graph_neighbors", "notes")
ALLOWED_FIELDS = set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)


def _resolve_repo_path(expected_path: str, repo_root: Path) -> Path:
    """Map a golden case path to a file on disk.

    Convention:
    - Paths starting with 'evals/' resolve relative to repo root (fixture cases).
    - Anything else is treated as a backend-fastapi/-relative path.
    """
    if expected_path.startswith("evals/"):
        return repo_root / expected_path
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
