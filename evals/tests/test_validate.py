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
