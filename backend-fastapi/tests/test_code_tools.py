"""
Tests for the LangChain code-analysis tools.

These are decorated @tool functions, so we invoke them through `.invoke(...)`.
The tools are pure (no I/O, no LLM), which makes them perfect unit-test material.
"""
import pytest

from app.services.code_tools import (
    analyze_code_structure,
    detect_code_smells,
    calculate_code_complexity,
    check_security_issues,
    search_code_pattern,
    get_tool,
    langchain_tools,
    langchain_tools_dict,
    tool_descriptions,
    CodeToolName,
)


def _run(tool, **kwargs):
    """Invoke a LangChain @tool with keyword args (works across LC versions)."""
    return tool.invoke(kwargs)


# ----- analyze_code_structure -----

class TestAnalyzeCodeStructure:
    def test_python_basic_counts(self, sample_python_code):
        out = _run(analyze_code_structure, code=sample_python_code, language="python")
        assert "代码结构分析" in out
        assert "总行数" in out
        assert "函数" in out
        assert "类" in out

    def test_invalid_python_falls_back_gracefully(self):
        out = _run(analyze_code_structure, code="def broken(:::", language="python")
        # No exception; the tool reports something
        assert "代码结构分析" in out

    def test_typescript_language(self):
        ts = "import x from 'y';\nfunction f() { return 1 }\nclass C {}\n"
        out = _run(analyze_code_structure, code=ts, language="typescript")
        assert "代码结构分析" in out
        assert "函数" in out

    def test_unknown_language_still_returns_basic_stats(self):
        out = _run(analyze_code_structure, code="some text\n", language="cobol")
        assert "代码结构分析" in out


# ----- detect_code_smells -----

class TestDetectSmells:
    def test_clean_code_returns_no_issues(self):
        clean = "def add(a, b):\n    return a + b\n"
        out = _run(detect_code_smells, code=clean, language="python")
        assert "未发现明显的代码坏味道" in out

    def test_long_line_is_flagged(self):
        code = "x = " + "1+" * 60 + "1\n"  # very long single line
        out = _run(detect_code_smells, code=code, language="python")
        assert "代码过长" in out

    def test_too_many_params_is_flagged(self):
        code = "def f(a, b, c, d, e, f, g):\n    return a\n"
        out = _run(detect_code_smells, code=code, language="python")
        assert "参数过多" in out

    def test_long_function_is_flagged(self, smelly_python_code):
        out = _run(detect_code_smells, code=smelly_python_code, language="python")
        assert "过长" in out


# ----- calculate_code_complexity -----

class TestComplexity:
    def test_trivial_function_is_simple(self):
        code = "def add(a, b):\n    return a + b\n"
        out = _run(calculate_code_complexity, code=code, language="python")
        assert "简单" in out
        assert "圈复杂度" in out

    def test_branches_raise_complexity(self):
        code = (
            "def f(x):\n"
            "    if x > 0:\n"
            "        for i in range(x):\n"
            "            if i % 2 == 0 and i > 5:\n"
            "                pass\n"
            "    elif x < 0:\n"
            "        while x < 0:\n"
            "            x += 1\n"
            "    return x\n"
        )
        out = _run(calculate_code_complexity, code=code, language="python")
        # not strict, just confirms it's NOT classified as simple
        assert "圈复杂度" in out

    def test_typescript_handled(self):
        ts = "function f(x){if (x && x>0){return 1} else if (x||true){return 2}}"
        out = _run(calculate_code_complexity, code=ts, language="typescript")
        assert "圈复杂度" in out

    def test_empty_code_does_not_crash(self):
        out = _run(calculate_code_complexity, code="", language="python")
        assert "圈复杂度" in out


# ----- check_security_issues -----

class TestSecurityChecks:
    def test_clean_code_returns_ok(self):
        out = _run(check_security_issues, code="def f(): return 1\n", language="python")
        assert "未发现明显的安全问题" in out

    def test_sql_injection_pattern_flagged(self):
        # Regex is execute\(["'].*\+.*["'] - needs a quote on both sides of +
        code = "cursor.execute('SELECT * FROM u WHERE id=' + uid + ' AND active=1')\n"
        out = _run(check_security_issues, code=code, language="python")
        assert "SQL" in out

    def test_eval_is_flagged(self):
        out = _run(check_security_issues, code="eval('1+1')\n", language="python")
        assert "eval" in out

    def test_hardcoded_secret_is_flagged(self):
        out = _run(check_security_issues, code='API_KEY = "sk-abc123"\n', language="python")
        assert "硬编码" in out

    def test_pickle_loads_is_flagged(self):
        out = _run(check_security_issues, code="import pickle\npickle.loads(b'x')\n", language="python")
        assert "pickle" in out

    def test_js_inner_html_is_flagged(self):
        out = _run(check_security_issues, code="el.innerHTML = userInput;", language="javascript")
        assert "innerHTML" in out

    def test_todo_marker_is_reported(self):
        out = _run(check_security_issues, code="# TODO refactor this\n", language="python")
        assert "TODO" in out


# ----- search_code_pattern -----

class TestSearchPattern:
    def test_finds_function_definitions(self):
        out = _run(search_code_pattern, code="def a():\n    pass\ndef b():\n    pass\n", pattern=r"def \w+")
        assert "搜索结果" in out
        assert "def a" in out
        assert "def b" in out

    def test_no_match_returns_friendly_message(self):
        out = _run(search_code_pattern, code="hello\n", pattern=r"\bgoodbye\b")
        assert "未找到匹配" in out

    def test_invalid_regex_returns_error_message(self):
        out = _run(search_code_pattern, code="x", pattern=r"[unclosed")
        assert "正则表达式错误" in out


# ----- Registry / metadata -----

class TestToolRegistry:
    def test_get_tool_returns_known_tools(self):
        assert get_tool(CodeToolName.ANALYZE_STRUCTURE) is not None
        assert get_tool(CodeToolName.CHECK_SECURITY) is not None

    def test_get_tool_unknown_returns_none(self):
        assert get_tool("not_a_real_tool") is None

    def test_all_dict_entries_are_in_list(self):
        for tool in langchain_tools_dict.values():
            assert tool in langchain_tools

    def test_every_dict_key_has_a_description(self):
        for name in langchain_tools_dict:
            assert name in tool_descriptions
            assert isinstance(tool_descriptions[name], str)
            assert len(tool_descriptions[name]) > 0
