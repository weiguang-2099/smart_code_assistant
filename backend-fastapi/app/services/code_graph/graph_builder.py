"""
Graph Builder - 代码知识图谱构建器

将代码实体存储到 Neo4j 图数据库和 ChromaDB 向量数据库
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from app.services.code_graph.config import CodeGraphConfig, code_graph_config
from app.services.code_graph.ast_parser import ParseResult, FunctionEntity, ClassEntity
from app.services.code_graph.entity_extractor import CodeEntityExtractor, entity_extractor
from app.services.code_graph.neo4j_client import Neo4jClient, get_neo4j_client
from app.services.code_graph.chromadb_client import ChromaDBClient, get_chromadb_client

logger = logging.getLogger(__name__)


class CodeGraphBuilder:
    """代码知识图谱构建器"""

    def __init__(
        self,
        config: Optional[CodeGraphConfig] = None,
        neo4j_client: Optional[Neo4jClient] = None,
        chromadb_client: Optional[ChromaDBClient] = None,
        extractor: Optional[CodeEntityExtractor] = None
    ):
        self.config = config or code_graph_config
        self._neo4j = neo4j_client
        self._chromadb = chromadb_client
        self._extractor = extractor or entity_extractor

    async def _get_neo4j(self) -> Neo4jClient:
        if self._neo4j is None:
            self._neo4j = await get_neo4j_client()
        return self._neo4j

    def _get_chromadb(self) -> ChromaDBClient:
        if self._chromadb is None:
            self._chromadb = get_chromadb_client()
        return self._chromadb

    async def build_from_code(
        self,
        code: str,
        language: str = "python",
        project_id: Optional[int] = None,
        module_path: str = "unknown"
    ) -> Dict[str, Any]:
        """
        从代码构建知识图谱

        Args:
            code: 源代码
            language: 编程语言
            project_id: 项目ID（可选）
            module_path: 模块路径

        Returns:
            构建结果统计
        """
        # 1. 提取实体
        parse_result = self._extractor.extract_from_code(code, language, module_path)

        if parse_result.error:
            return {
                "success": False,
                "error": parse_result.error,
                "stats": {}
            }

        # 2. 存储到 Neo4j
        neo4j = await self._get_neo4j()
        stats = {
            "functions_created": 0,
            "classes_created": 0,
            "imports_created": 0,
            "relationships_created": 0
        }

        try:
            # 创建项目节点（如果有）
            if project_id:
                await neo4j.create_project(project_id, f"project_{project_id}", language)

            # 清除该模块的旧图谱数据（避免重复/过时的关系）
            await neo4j.clear_module_graph(module_path)

            # 创建模块节点（始终创建）
            await neo4j.create_module(project_id or 0, module_path, module_path)

            # 创建类节点
            for cls in parse_result.classes:
                await neo4j.create_class(
                    module_path=module_path,
                    class_name=cls.name,
                    docstring=cls.docstring,
                    line_start=cls.line_start,
                    line_end=cls.line_end
                )
                stats["classes_created"] += 1

                # 创建继承关系
                for parent in cls.inherits_from:
                    await neo4j.create_inheritance_relationship(
                        child_class=cls.name,
                        parent_class=parent,
                        module_path=module_path
                    )
                    stats["relationships_created"] += 1

            # 创建函数节点
            for func in parse_result.functions:
                await neo4j.create_function(
                    module_path=module_path,
                    function_name=func.name,
                    class_name=func.class_name,
                    signature=func.signature,
                    docstring=func.docstring,
                    line_start=func.line_start,
                    line_end=func.line_end,
                    complexity=func.complexity
                )
                stats["functions_created"] += 1

                # 创建调用关系
                for called_func in func.calls:
                    try:
                        await neo4j.create_call_relationship(
                            caller_module=module_path,
                            caller_function=func.name,
                            caller_class=func.class_name,
                            callee_function=called_func
                        )
                        stats["relationships_created"] += 1
                    except Exception as e:
                        logger.debug(f"Could not create call relationship: {e}")

            # 创建导入节点
            for imp in parse_result.imports:
                await neo4j.create_import(
                    module_path=module_path,
                    import_module=imp.module,
                    alias=imp.alias,
                    names=imp.names,
                )
                stats["imports_created"] += 1

        except Exception as e:
            logger.error(f"Failed to build graph in Neo4j: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": stats
            }

        # 3. 存储到 ChromaDB（如果启用）
        if self.config.enable_semantic_search and project_id:
            try:
                chromadb = self._get_chromadb()

                # 索引函数
                func_dicts = self._extractor.to_dict_list(parse_result.functions, "function")
                chromadb.index_functions(func_dicts, project_id)

                # 索引类
                class_dicts = self._extractor.to_dict_list(parse_result.classes, "class")
                chromadb.index_classes(class_dicts, project_id)

                stats["vector_indexed"] = len(func_dicts) + len(class_dicts)
            except Exception as e:
                logger.warning(f"Failed to index in ChromaDB: {e}")
                stats["vector_indexed"] = 0

        return {
            "success": True,
            "stats": stats,
            "entities": {
                "functions": len(parse_result.functions),
                "classes": len(parse_result.classes),
                "imports": len(parse_result.imports)
            }
        }

    async def build_from_files(
        self,
        files: List[Dict[str, str]],
        project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        从多个文件构建知识图谱

        Args:
            files: 文件列表，每个包含 path, content, language
            project_id: 项目ID

        Returns:
            汇总构建结果
        """
        total_stats = {
            "files_processed": 0,
            "functions_created": 0,
            "classes_created": 0,
            "imports_created": 0,
            "relationships_created": 0,
            "errors": []
        }

        for file in files:
            try:
                result = await self.build_from_code(
                    code=file["content"],
                    language=file.get("language", "python"),
                    project_id=project_id,
                    module_path=file["path"]
                )

                if result["success"]:
                    total_stats["files_processed"] += 1
                    total_stats["functions_created"] += result["stats"].get("functions_created", 0)
                    total_stats["classes_created"] += result["stats"].get("classes_created", 0)
                    total_stats["imports_created"] += result["stats"].get("imports_created", 0)
                    total_stats["relationships_created"] += result["stats"].get("relationships_created", 0)
                else:
                    total_stats["errors"].append({
                        "file": file["path"],
                        "error": result.get("error", "Unknown error")
                    })
            except Exception as e:
                total_stats["errors"].append({
                    "file": file["path"],
                    "error": str(e)
                })

        return {
            "success": len(total_stats["errors"]) == 0,
            "stats": total_stats
        }

    async def get_graph_statistics(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """获取图谱统计信息"""
        neo4j = await self._get_neo4j()
        neo4j_stats = await neo4j.get_graph_stats(project_id)

        if project_id:
            chromadb = self._get_chromadb()
            chromadb_stats = chromadb.get_collection_stats(project_id)
            neo4j_stats.update(chromadb_stats)

        return neo4j_stats

    async def clear_graph(self, project_id: int) -> None:
        """清除项目的图谱数据"""
        neo4j = await self._get_neo4j()
        await neo4j.clear_project_graph(project_id)

        chromadb = self._get_chromadb()
        chromadb.delete_project_collections(project_id)

        logger.info(f"Cleared graph data for project {project_id}")


# 全局构建器实例
_graph_builder: Optional[CodeGraphBuilder] = None


def get_graph_builder() -> CodeGraphBuilder:
    """获取图谱构建器单例"""
    global _graph_builder
    if _graph_builder is None:
        _graph_builder = CodeGraphBuilder()
    return _graph_builder
