"""
Tests for the AST parser used by the code knowledge graph.
Pure parsing logic, no I/O.
"""
import pytest

from app.services.code_graph.ast_parser import (
    ASTParser,
    ClassEntity,
    FunctionEntity,
    ImportEntity,
    ParseResult,
)


@pytest.fixture
def parser():
    return ASTParser()


# ----- Python -----

class TestPythonParsing:
    def test_extracts_module_function(self, parser):
        code = "def hello(name):\n    return f'hi {name}'\n"
        result = parser.parse(code, "python", module_path="mod")
        assert result.error is None
        assert len(result.functions) == 1
        fn = result.functions[0]
        assert fn.name == "hello"
        assert "name" in fn.signature
        assert fn.module_path == "mod"

    def test_extracts_async_function(self, parser):
        code = "async def run():\n    pass\n"
        result = parser.parse(code, "python")
        assert any(f.name == "run" for f in result.functions)

    def test_class_with_methods(self, parser):
        code = (
            "class Foo(Base):\n"
            "    def a(self): pass\n"
            "    def b(self, x): return x\n"
        )
        result = parser.parse(code, "python")
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "Foo"
        assert "Base" in cls.inherits_from
        assert set(cls.methods) == {"a", "b"}

        method_names = {f.name for f in result.functions}
        assert {"a", "b"} <= method_names
        for fn in result.functions:
            assert fn.class_name == "Foo"

    def test_imports_module_and_from(self, parser):
        code = "import os\nfrom typing import List, Dict\n"
        result = parser.parse(code, "python")
        modules = {i.module for i in result.imports}
        assert "os" in modules
        assert "typing" in modules
        from_typing = next(i for i in result.imports if i.module == "typing")
        assert set(from_typing.names) == {"List", "Dict"}

    def test_import_alias_captured(self, parser):
        code = "import numpy as np\n"
        result = parser.parse(code, "python")
        np_import = next(i for i in result.imports if i.module == "numpy")
        assert np_import.alias == "np"

    def test_module_docstring(self, parser):
        code = '"""Module-level docstring."""\ndef f(): pass\n'
        result = parser.parse(code, "python")
        assert result.module_docstring == "Module-level docstring."

    def test_function_signature_includes_annotations_and_defaults(self, parser):
        code = "def f(a: int, b: str = 'x', *args, **kw) -> bool:\n    return True\n"
        result = parser.parse(code, "python")
        fn = result.functions[0]
        assert "int" in fn.signature
        assert "'x'" in fn.signature
        assert "*args" in fn.signature
        assert "**kw" in fn.signature
        assert "-> bool" in fn.signature

    def test_function_calls_collected(self, parser):
        code = (
            "def driver():\n"
            "    print('a')\n"
            "    obj.method()\n"
            "    helper()\n"
        )
        result = parser.parse(code, "python")
        fn = next(f for f in result.functions if f.name == "driver")
        assert "print" in fn.calls
        assert "method" in fn.calls
        assert "helper" in fn.calls

    def test_complexity_grows_with_branches(self, parser):
        simple = parser.parse("def a(): return 1\n", "python").functions[0]
        complex_ = parser.parse(
            "def b(x):\n"
            "    if x and x > 0:\n"
            "        for i in range(x):\n"
            "            if i % 2:\n"
            "                pass\n"
            "    return x\n",
            "python",
        ).functions[0]
        assert complex_.complexity > simple.complexity

    def test_syntax_error_returns_error_field(self, parser):
        result = parser.parse("def broken(:::\n", "python")
        assert result.error is not None
        assert "Syntax" in result.error or "error" in result.error.lower()


# ----- JavaScript / TypeScript -----

class TestJavaScriptParsing:
    def test_function_declaration(self, parser):
        code = "function add(a, b) { return a + b }\n"
        result = parser.parse(code, "javascript")
        names = [f.name for f in result.functions]
        assert "add" in names

    def test_arrow_function(self, parser):
        code = "const square = (x) => x * x;\n"
        result = parser.parse(code, "javascript")
        assert any(f.name == "square" for f in result.functions)

    def test_class_and_inheritance(self, parser):
        code = "class Cat extends Animal {}\n"
        result = parser.parse(code, "javascript")
        cls = result.classes[0]
        assert cls.name == "Cat"
        assert "Animal" in cls.inherits_from

    def test_import_styles(self, parser):
        code = (
            "import x from 'a';\n"
            "import 'b';\n"
            "const c = require('d');\n"
        )
        result = parser.parse(code, "javascript")
        modules = {i.module for i in result.imports}
        assert "a" in modules
        assert "b" in modules
        assert "d" in modules


# ----- Dispatch / misc -----

class TestDispatch:
    def test_unsupported_language_returns_error(self, parser):
        result = parser.parse("xx", "cobol")
        assert result.error is not None
        assert "Unsupported" in result.error

    def test_get_function_calls_python(self, parser):
        code = "def f():\n    a()\n    b.c()\n"
        calls = parser.get_function_calls(code, "python")
        assert set(calls) >= {"a", "c"}

    def test_get_function_calls_handles_syntax_error(self, parser):
        # bad python - returns empty rather than raising
        assert parser.get_function_calls("def broken(:::", "python") == []

    def test_get_function_calls_javascript_regex(self, parser):
        code = "foo(); bar(1, 2); baz();"
        calls = parser.get_function_calls(code, "javascript")
        assert {"foo", "bar", "baz"} <= set(calls)
