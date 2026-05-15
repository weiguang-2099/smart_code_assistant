"""
Entity Extractor - 代码实体提取器

结合 AST 解析和 LLM 增强提取代码实体
"""
import logging
from typing import Optional, List, Dict, Any

from app.services.code_graph.ast_parser import ASTParser, ParseResult, FunctionEntity, ClassEntity
from app.services.code_graph.config import CodeGraphConfig, code_graph_config

logger = logging.getLogger(__name__)


class CodeEntityExtractor:
    """代码实体提取器"""

    def __init__(
        self,
        config: Optional[CodeGraphConfig] = None,
        ast_parser: Optional[ASTParser] = None
    ):
        self.config = config or code_graph_config
        self.ast_parser = ast_parser or ASTParser()

    def extract_from_code(
        self,
        code: str,
        language: str = "python",
        module_path: Optional[str] = None
    ) -> ParseResult:
        """
        从代码中提取实体

        Args:
            code: 源代码
            language: 编程语言
            module_path: 模块路径

        Returns:
            ParseResult 包含提取的实体
        """
        return self.ast_parser.parse(code, language, module_path)

    def extract_functions(
        self,
        code: str,
        language: str = "python",
        module_path: Optional[str] = None
    ) -> List[FunctionEntity]:
        """只提取函数实体"""
        result = self.extract_from_code(code, language, module_path)
        return result.functions

    def extract_classes(
        self,
        code: str,
        language: str = "python",
        module_path: Optional[str] = None
    ) -> List[ClassEntity]:
        """只提取类实体"""
        result = self.extract_from_code(code, language, module_path)
        return result.classes

    def get_entity_summary(self, result: ParseResult) -> Dict[str, Any]:
        """获取实体提取摘要"""
        return {
            "functions_count": len(result.functions),
            "classes_count": len(result.classes),
            "imports_count": len(result.imports),
            "error": result.error,
            "functions": [
                {
                    "name": f.name,
                    "class": f.class_name,
                    "line": f"{f.line_start}-{f.line_end}",
                    "complexity": f.complexity,
                    "calls": f.calls[:5]  # 只显示前5个调用
                }
                for f in result.functions[:20]  # 只显示前20个
            ],
            "classes": [
                {
                    "name": c.name,
                    "line": f"{c.line_start}-{c.line_end}",
                    "methods": c.methods[:10],
                    "inherits": c.inherits_from
                }
                for c in result.classes[:10]
            ]
        }

    def to_dict_list(self, entities: List, entity_type: str) -> List[Dict[str, Any]]:
        """将实体列表转换为字典列表"""
        result = []
        for entity in entities:
            if entity_type == "function":
                result.append({
                    "name": entity.name,
                    "type": "function",
                    "signature": entity.signature,
                    "class_name": entity.class_name,
                    "module_path": entity.module_path,
                    "docstring": entity.docstring,
                    "line_start": entity.line_start,
                    "line_end": entity.line_end,
                    "complexity": entity.complexity,
                    "calls": entity.calls
                })
            elif entity_type == "class":
                result.append({
                    "name": entity.name,
                    "type": "class",
                    "module_path": entity.module_path,
                    "docstring": entity.docstring,
                    "line_start": entity.line_start,
                    "line_end": entity.line_end,
                    "methods": entity.methods,
                    "inherits_from": entity.inherits_from
                })
        return result


# 全局提取器实例
entity_extractor = CodeEntityExtractor()
