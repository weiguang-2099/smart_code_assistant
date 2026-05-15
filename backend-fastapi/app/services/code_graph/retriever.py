"""
Code Graph Retriever - 代码图谱检索器

结合向量搜索和图遍历的混合检索
"""
import asyncio
import hashlib
import logging
from typing import Optional, List, Dict, Any

from app.services.code_graph.config import CodeGraphConfig, code_graph_config
from app.services.code_graph.neo4j_client import Neo4jClient, get_neo4j_client
from app.services.code_graph.chromadb_client import ChromaDBClient, get_chromadb_client
from app.core.cache import global_cache_manager

logger = logging.getLogger(__name__)

RETRIEVAL_CACHE_TTL = 300


class CodeGraphRetriever:
    """代码图谱混合检索器"""

    def __init__(
        self,
        config: Optional[CodeGraphConfig] = None,
        neo4j_client: Optional[Neo4jClient] = None,
        chromadb_client: Optional[ChromaDBClient] = None
    ):
        self.config = config or code_graph_config
        self._neo4j = neo4j_client
        self._chromadb = chromadb_client

    async def _get_neo4j(self) -> Neo4jClient:
        if self._neo4j is None:
            self._neo4j = await get_neo4j_client()
        return self._neo4j

    def _get_chromadb(self) -> ChromaDBClient:
        if self._chromadb is None:
            self._chromadb = get_chromadb_client()
        return self._chromadb

    async def retrieve(
        self,
        query: str,
        project_id: Optional[int] = None,
        top_k: int = 10,
        include_graph_context: bool = True,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Hybrid retrieval with parallel semantic and graph queries and caching.

        Args:
            query: 查询文本
            project_id: 项目ID
            top_k: 返回结果数量
            include_graph_context: 是否包含图遍历上下文
            max_depth: 图遍历最大深度

        Returns:
            检索结果
        """
        cache_key_data = f"{query}:{project_id}:{top_k}:{include_graph_context}:{max_depth}"
        cache_key = f"retrieval:{hashlib.sha256(cache_key_data.encode()).hexdigest()[:32]}"

        cached_result = await global_cache_manager.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Retrieval cache hit for query: {query[:30]}")
            return cached_result

        result = {
            "query": query,
            "semantic_results": [],
            "graph_context": None,
            "combined_context": ""
        }

        async def semantic_search():
            if project_id and self.config.enable_semantic_search:
                try:
                    chromadb = self._get_chromadb()
                    return await asyncio.to_thread(
                        chromadb.search_all, query, project_id, top_k
                    )
                except Exception as e:
                    logger.warning(f"Semantic search failed: {e}")
            return {}

        async def graph_traversal():
            if not include_graph_context:
                return None

            try:
                neo4j = await self._get_neo4j()
                entity_names = self._extract_entity_names(query)
                return await neo4j.batch_get_entity_context(entity_names[:3])
            except Exception as e:
                logger.warning(f"Graph traversal failed: {e}")
                return None

        semantic_results, graph_context = await asyncio.gather(
            semantic_search(),
            graph_traversal(),
            return_exceptions=False
        )

        result["semantic_results"] = semantic_results
        result["graph_context"] = graph_context

        result["combined_context"] = self._build_combined_context(result)

        await global_cache_manager.set(cache_key, result, ttl=RETRIEVAL_CACHE_TTL)
        logger.debug(f"Retrieval result cached for query: {query[:30]}")

        return result


    def _extract_entity_names(self, query: str) -> List[str]:
        """从查询中提取可能的实体名称"""
        import re

        # 提取可能的函数名/类名（驼峰命名或下划线命名）
        patterns = [
            r'\b([a-z_][a-z0-9_]*)\b',  # snake_case
            r'\b([A-Z][a-zA-Z0-9]*)\b',  # CamelCase
        ]

        names = []
        for pattern in patterns:
            matches = re.findall(pattern, query)
            names.extend(matches)

        # 过滤常见关键词
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once',
            'function', 'class', 'method', 'variable', 'module', 'import',
            'find', 'search', 'get', 'query', 'show', 'list', 'what', 'how',
            'where', 'which', 'when', 'who', 'why', 'all', 'each', 'every',
            'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
            'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'
        }

        filtered = [n for n in names if n.lower() not in stop_words and len(n) > 2]
        return list(dict.fromkeys(filtered))[:10]  # 去重并限制数量

    def _build_combined_context(self, result: Dict[str, Any]) -> str:
        """构建组合上下文字符串"""
        context_parts = []

        # 添加语义搜索结果
        semantic = result.get("semantic_results", {})
        if semantic:
            if semantic.get("functions"):
                context_parts.append("相关函数:")
                for func in semantic["functions"][:5]:
                    metadata = func.get("metadata", {})
                    context_parts.append(
                        f"  - {metadata.get('name', 'unknown')} "
                        f"({metadata.get('module_path', '')})"
                    )

            if semantic.get("classes"):
                context_parts.append("相关类:")
                for cls in semantic["classes"][:5]:
                    metadata = cls.get("metadata", {})
                    context_parts.append(
                        f"  - {metadata.get('name', 'unknown')} "
                        f"({metadata.get('module_path', '')})"
                    )

        # 添加图上下文
        graph_ctx = result.get("graph_context")
        if graph_ctx:
            context_parts.append("图谱关系:")
            for ctx in graph_ctx[:10]:
                if "name" in ctx:
                    context_parts.append(
                        f"  - {ctx.get('name')} ({ctx.get('module_path', '')})"
                    )
                elif "entity" in ctx:
                    context_parts.append(
                        f"  - {ctx['entity']}: "
                        f"{ctx.get('callers_count', 0)} 调用者, "
                        f"{ctx.get('callees_count', 0)} 被调用"
                    )

        return "\n".join(context_parts) if context_parts else ""

    async def get_dependencies(
        self,
        entity_name: str,
        dep_type: str = "all"
    ) -> Dict[str, Any]:
        """
        获取实体的依赖关系

        Args:
            entity_name: 实体名称
            dep_type: 依赖类型 (callers, callees, imports, all)

        Returns:
            依赖关系
        """
        neo4j = await self._get_neo4j()
        result = {"entity": entity_name, "type": dep_type}

        if dep_type in ["callers", "all"]:
            result["callers"] = await neo4j.get_function_callers(entity_name)

        if dep_type in ["callees", "all"]:
            result["callees"] = await neo4j.get_function_callees(entity_name)

        return result

    async def analyze_impact(
        self,
        entity_name: str,
        entity_type: str = "function",
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        分析代码变更的影响范围

        Args:
            entity_name: 实体名称
            entity_type: 实体类型
            max_depth: 最大搜索深度

        Returns:
            影响分析结果
        """
        neo4j = await self._get_neo4j()
        return await neo4j.get_impact_analysis(entity_name, entity_type, max_depth)

    async def find_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 5
    ) -> List[List[Dict[str, Any]]]:
        """
        查找两个实体之间的调用路径

        Args:
            source: 起始实体
            target: 目标实体
            max_depth: 最大搜索深度

        Returns:
            路径列表
        """
        neo4j = await self._get_neo4j()
        return await neo4j.find_call_paths(source, target, max_depth)


# 全局检索器实例
_retriever: Optional[CodeGraphRetriever] = None


def get_retriever() -> CodeGraphRetriever:
    """获取检索器单例"""
    global _retriever
    if _retriever is None:
        _retriever = CodeGraphRetriever()
    return _retriever
