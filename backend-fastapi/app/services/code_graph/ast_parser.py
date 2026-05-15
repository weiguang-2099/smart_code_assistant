"""
AST Parser - 代码抽象语法树解析器

从源代码中提取函数、类、导入等代码实体
"""
import ast
import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CodeEntity:
    """代码实体基类"""
    name: str = ""
    entity_type: str = ""
    line_start: int = 0
    line_end: int = 0
    docstring: Optional[str] = None
    source_code: Optional[str] = None


@dataclass
class FunctionEntity(CodeEntity):
    """函数实体"""
    entity_type: str = "function"
    signature: Optional[str] = None
    class_name: Optional[str] = None
    module_path: Optional[str] = None
    complexity: int = 1
    calls: List[str] = field(default_factory=list)


@dataclass
class ClassEntity(CodeEntity):
    """类实体"""
    entity_type: str = "class"
    module_path: Optional[str] = None
    methods: List[str] = field(default_factory=list)
    inherits_from: List[str] = field(default_factory=list)


@dataclass
class ImportEntity:
    """导入实体"""
    module: str
    alias: Optional[str] = None
    names: List[str] = field(default_factory=list)  # from X import a, b, c


@dataclass
class ParseResult:
    """解析结果"""
    functions: List[FunctionEntity] = field(default_factory=list)
    classes: List[ClassEntity] = field(default_factory=list)
    imports: List[ImportEntity] = field(default_factory=list)
    module_docstring: Optional[str] = None
    error: Optional[str] = None


class ASTParser:
    """AST 解析器"""

    def __init__(self):
        self.supported_languages = ["python", "javascript", "typescript"]

    def parse(
        self,
        code: str,
        language: str = "python",
        module_path: Optional[str] = None
    ) -> ParseResult:
        """
        解析代码

        Args:
            code: 源代码
            language: 编程语言
            module_path: 模块路径（可选）

        Returns:
            ParseResult 包含提取的实体
        """
        language = language.lower()

        if language == "python":
            return self._parse_python(code, module_path)
        elif language in ["javascript", "typescript", "js", "ts"]:
            return self._parse_javascript(code, module_path, language)
        else:
            return ParseResult(error=f"Unsupported language: {language}")

    def _parse_python(
        self,
        code: str,
        module_path: Optional[str] = None
    ) -> ParseResult:
        """解析 Python 代码"""
        result = ParseResult()

        try:
            tree = ast.parse(code)
            lines = code.split('\n')

            # 模块文档字符串
            result.module_docstring = ast.get_docstring(tree)

            # 解析导入
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        result.imports.append(ImportEntity(
                            module=alias.name,
                            alias=alias.asname
                        ))
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    names = [alias.name for alias in node.names]
                    result.imports.append(ImportEntity(
                        module=module,
                        names=names
                    ))

            # 解析类
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    class_entity = self._parse_class(node, lines, module_path)
                    result.classes.append(class_entity)

                    # 解析类方法
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            func_entity = self._parse_function(
                                item, lines, module_path, class_name=node.name
                            )
                            result.functions.append(func_entity)
                            class_entity.methods.append(item.name)

                elif isinstance(node, ast.FunctionDef):
                    # 模块级函数
                    func_entity = self._parse_function(node, lines, module_path)
                    result.functions.append(func_entity)

                elif isinstance(node, ast.AsyncFunctionDef):
                    # 异步函数
                    func_entity = self._parse_function(node, lines, module_path)
                    result.functions.append(func_entity)

        except SyntaxError as e:
            result.error = f"Syntax error: {e}"
            logger.warning(f"Python parse error: {e}")
        except Exception as e:
            result.error = f"Parse error: {e}"
            logger.error(f"Python parse error: {e}")

        return result

    def _parse_class(
        self,
        node: ast.ClassDef,
        lines: List[str],
        module_path: Optional[str]
    ) -> ClassEntity:
        """解析类定义"""
        # 获取继承
        inherits = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                inherits.append(base.id)
            elif isinstance(base, ast.Attribute):
                inherits.append(ast.unparse(base))

        # 获取源代码
        source = '\n'.join(lines[node.lineno - 1:node.end_lineno])

        return ClassEntity(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            source_code=source,
            module_path=module_path,
            methods=[],
            inherits_from=inherits
        )

    def _parse_function(
        self,
        node,
        lines: List[str],
        module_path: Optional[str],
        class_name: Optional[str] = None
    ) -> FunctionEntity:
        """解析函数定义"""
        # 获取签名
        args = []
        if hasattr(node, 'args'):
            # 位置参数
            for arg in node.args.args:
                arg_str = arg.arg
                if arg.annotation:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                args.append(arg_str)

            # 默认参数
            defaults = node.args.defaults
            if defaults:
                for i, default in enumerate(defaults):
                    idx = len(node.args.args) - len(defaults) + i
                    if idx < len(args):
                        args[idx] += f" = {ast.unparse(default)}"

            # *args
            if node.args.vararg:
                args.append(f"*{node.args.vararg.arg}")

            # **kwargs
            if node.args.kwarg:
                args.append(f"**{node.args.kwarg.arg}")

        signature = f"{node.name}({', '.join(args)})"
        if hasattr(node, 'returns') and node.returns:
            signature += f" -> {ast.unparse(node.returns)}"

        # 获取调用的函数
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)

        # 计算复杂度
        complexity = self._calculate_complexity(node)

        # 获取源代码
        source = '\n'.join(lines[node.lineno - 1:node.end_lineno])

        return FunctionEntity(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            source_code=source,
            signature=signature,
            class_name=class_name,
            module_path=module_path,
            complexity=complexity,
            calls=list(set(calls))
        )

    def _calculate_complexity(self, node) -> int:
        """计算圈复杂度"""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                if child.ifs:
                    complexity += len(child.ifs)

        return complexity

    def _parse_javascript(
        self,
        code: str,
        module_path: Optional[str],
        language: str
    ) -> ParseResult:
        """解析 JavaScript/TypeScript 代码（使用正则表达式简化解析）"""
        result = ParseResult()

        try:
            lines = code.split('\n')

            # 解析导入
            import_patterns = [
                r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]',
                r'import\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)'
            ]

            for pattern in import_patterns:
                for match in re.finditer(pattern, code):
                    result.imports.append(ImportEntity(module=match.group(1)))

            # 解析函数
            func_patterns = [
                # function name() {}
                r'function\s+(\w+)\s*\(([^)]*)\)',
                # const name = () => {} 或 const name = function() {}
                r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\))\s*(?:=>)?',
                # class methods
                r'(\w+)\s*\(([^)]*)\)\s*\{',
            ]

            # 简单的函数提取
            for i, line in enumerate(lines, 1):
                # function declaration
                match = re.search(r'function\s+(\w+)\s*\(([^)]*)\)', line)
                if match:
                    result.functions.append(FunctionEntity(
                        name=match.group(1),
                        line_start=i,
                        line_end=i,
                        signature=f"{match.group(1)}({match.group(2)})",
                        module_path=module_path
                    ))
                    continue

                # arrow function
                match = re.search(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_]\w*)\s*=>', line)
                if match:
                    result.functions.append(FunctionEntity(
                        name=match.group(1),
                        line_start=i,
                        line_end=i,
                        module_path=module_path
                    ))

            # 解析类
            class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
            for match in re.finditer(class_pattern, code):
                class_name = match.group(1)
                inherits = [match.group(2)] if match.group(2) else []

                # 找到类的起始行
                start_line = code[:match.start()].count('\n') + 1

                result.classes.append(ClassEntity(
                    name=class_name,
                    line_start=start_line,
                    line_end=start_line,  # 简化处理
                    module_path=module_path,
                    inherits_from=inherits
                ))

        except Exception as e:
            result.error = f"Parse error: {e}"
            logger.error(f"JavaScript parse error: {e}")

        return result

    def get_function_calls(self, code: str, language: str = "python") -> List[str]:
        """提取代码中调用的所有函数名"""
        calls = []

        if language == "python":
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            calls.append(node.func.id)
                        elif isinstance(node.func, ast.Attribute):
                            calls.append(node.func.attr)
            except:
                pass
        else:
            # JavaScript: 简单正则匹配
            call_pattern = r'(\w+)\s*\('
            calls = re.findall(call_pattern, code)

        return list(set(calls))


# 全局解析器实例
ast_parser = ASTParser()
