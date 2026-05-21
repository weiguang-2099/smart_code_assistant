"""Tests for the AST-driven entity extractor + summariser."""
import pytest

from app.services.code_graph.entity_extractor import CodeEntityExtractor


@pytest.fixture
def extractor():
    return CodeEntityExtractor()


SAMPLE = (
    "class Foo:\n"
    "    def m(self): pass\n"
    "def top(): return 1\n"
    "import os\n"
)


class TestExtractFromCode:
    def test_returns_parse_result(self, extractor):
        result = extractor.extract_from_code(SAMPLE)
        assert result.error is None
        assert len(result.functions) == 2  # m + top
        assert len(result.classes) == 1
        assert len(result.imports) == 1

    def test_extract_functions_only(self, extractor):
        fns = extractor.extract_functions(SAMPLE)
        names = {f.name for f in fns}
        assert names == {"m", "top"}

    def test_extract_classes_only(self, extractor):
        cls = extractor.extract_classes(SAMPLE)
        assert len(cls) == 1
        assert cls[0].name == "Foo"


class TestSummary:
    def test_summary_contains_counts(self, extractor):
        result = extractor.extract_from_code(SAMPLE)
        summary = extractor.get_entity_summary(result)
        assert summary["functions_count"] == 2
        assert summary["classes_count"] == 1
        assert summary["imports_count"] == 1
        assert summary["error"] is None

    def test_summary_truncates_long_lists(self, extractor):
        # 25 top-level functions -> summary should cap at 20
        code = "\n".join(f"def f{i}(): pass" for i in range(25))
        result = extractor.extract_from_code(code)
        summary = extractor.get_entity_summary(result)
        assert summary["functions_count"] == 25
        assert len(summary["functions"]) == 20


class TestToDictList:
    def test_function_dict_shape(self, extractor):
        result = extractor.extract_from_code(SAMPLE)
        as_dicts = extractor.to_dict_list(result.functions, "function")
        sample = as_dicts[0]
        for key in ("name", "type", "signature", "class_name",
                    "module_path", "docstring", "line_start",
                    "line_end", "complexity", "calls"):
            assert key in sample
        assert sample["type"] == "function"

    def test_class_dict_shape(self, extractor):
        result = extractor.extract_from_code(SAMPLE)
        as_dicts = extractor.to_dict_list(result.classes, "class")
        sample = as_dicts[0]
        for key in ("name", "type", "module_path", "docstring",
                    "line_start", "line_end", "methods", "inherits_from"):
            assert key in sample
        assert sample["type"] == "class"

    def test_unknown_entity_type_returns_empty(self, extractor):
        result = extractor.extract_from_code(SAMPLE)
        assert extractor.to_dict_list(result.functions, "unknown") == []
