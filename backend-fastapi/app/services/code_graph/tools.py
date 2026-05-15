"""
Code Graph LangChain Tools - 代码图谱工具

用于 LangChain Agent 调用的代码图谱工具
"""
import asyncio
import logging
from typing import Optional

from langchain_core.tools import tool

from app.services.code_graph.graph_builder import CodeGraphBuilder, get_graph_builder
from app.services.code_graph.retriever import CodeGraphRetriever, get_retriever

logger = logging.getLogger(__name__)


def _run_async(coro):
    """在同步上下文中运行异步函数"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 如果已经在异步上下文中，创建新的线程运行
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


@tool
def build_code_graph(code: str, language: str = "python", module_path: str = "unknown") -> str:
    """
    构建代码知识图谱，提取函数、类、模块及其关系

    Args:
        code: 源代码
        language: 编程语言 (默认: python)
        module_path: 模块路径 (默认: unknown)

    Returns:
        图谱构建结果和统计信息
    """
    try:
        builder = get_graph_builder()

        async def _build():
            return await builder.build_from_code(
                code=code,
                language=language,
                module_path=module_path
            )

        result = _run_async(_build())

        if result["success"]:
            stats = result["stats"]
            entities = result["entities"]
            return f"""📊 代码知识图谱构建完成 [{language}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 实体统计:
  • 函数: {entities['functions']} 个
  • 类: {entities['classes']} 个
  • 导入: {entities['imports']} 个

🔗 关系统计:
  • 创建节点: {stats['functions_created'] + stats['classes_created']} 个
  • 创建关系: {stats['relationships_created']} 条
  • 向量索引: {stats.get('vector_indexed', 0)} 个

✅ 图谱构建成功！可以使用其他工具查询依赖关系和影响分析。"""
        else:
            return f"❌ 图谱构建失败: {result.get('error', '未知错误')}"

    except Exception as e:
        logger.error(f"build_code_graph error: {e}")
        return f"❌ 图谱构建失败: {str(e)}"


@tool
def query_code_dependencies(entity_name: str, dep_type: str = "all") -> str:
    """
    查询代码实体的依赖关系

    Args:
        entity_name: 实体名称 (函数名/类名)
        dep_type: 依赖类型 (callers=谁调用它, callees=它调用谁, all=全部)

    Returns:
        依赖关系图谱
    """
    try:
        retriever = get_retriever()

        async def _query():
            return await retriever.get_dependencies(entity_name, dep_type)

        result = _run_async(_query())

        output = f"""🔍 依赖关系查询 [{entity_name}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        callers = result.get("callers", [])
        callees = result.get("callees", [])

        if dep_type in ["callers", "all"] and callers:
            output += f"\n\n📞 被调用者 ({len(callers)} 个):"
            for c in callers[:10]:
                output += f"\n  • {c.get('name', '')} ({c.get('module_path', '')})"

        if dep_type in ["callees", "all"] and callees:
            output += f"\n\n📲 调用目标 ({len(callees)} 个):"
            for c in callees[:10]:
                output += f"\n  • {c.get('name', '')} ({c.get('module_path', '')})"

        if not callers and not callees:
            output += "\n\n⚠️ 未找到依赖关系"

        return output

    except Exception as e:
        logger.error(f"query_code_dependencies error: {e}")
        return f"❌ 查询失败: {str(e)}"


@tool
def analyze_impact(entity_name: str, change_type: str = "modify") -> str:
    """
    分析代码变更的影响范围

    Args:
        entity_name: 变更的实体名称 (函数名/类名)
        change_type: 变更类型 (modify=修改, delete=删除, rename=重命名)

    Returns:
        受影响的代码实体列表
    """
    try:
        retriever = get_retriever()

        async def _analyze():
            return await retriever.analyze_impact(entity_name, "function", max_depth=3)

        result = _run_async(_analyze())

        impacted = result.get("impacted", [])
        total_count = result.get("total_count", 0)

        output = f"""🎯 影响范围分析 [{entity_name}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 变更类型: {change_type}
📊 影响范围: {total_count} 个实体
"""

        if impacted:
            output += "\n⚠️ 受影响的代码:"
            for item in impacted[:15]:
                distance = item.get("distance", 1)
                module = item.get("module_path", "")
                class_name = item.get("class_name")
                name = item.get("name", "")

                if class_name:
                    output += f"\n  {'  ' * distance}• {class_name}.{name} ({module})"
                else:
                    output += f"\n  {'  ' * distance}• {name} ({module})"

            if len(impacted) > 15:
                output += f"\n  ... 还有 {len(impacted) - 15} 个"

            # 风险评估
            if total_count > 20:
                output += "\n\n🔴 高风险变更: 影响范围较大，建议仔细测试"
            elif total_count > 10:
                output += "\n\n🟡 中等风险: 建议进行回归测试"
            else:
                output += "\n\n🟢 低风险: 影响范围有限"
        else:
            output += "\n✅ 未发现受影响的代码"

        return output

    except Exception as e:
        logger.error(f"analyze_impact error: {e}")
        return f"❌ 分析失败: {str(e)}"


@tool
def find_code_paths(source: str, target: str, max_depth: int = 5) -> str:
    """
    查找两个代码实体之间的调用路径

    Args:
        source: 起始实体名称
        target: 目标实体名称
        max_depth: 最大搜索深度 (默认: 5)

    Returns:
        调用路径列表
    """
    try:
        retriever = get_retriever()

        async def _find():
            return await retriever.find_paths(source, target, max_depth)

        paths = _run_async(_find())

        output = f"""🛤️ 调用路径查找 [{source}] → [{target}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        if paths:
            output += f"\n\n找到 {len(paths)} 条路径:\n"
            for i, path in enumerate(paths[:5], 1):
                output += f"\n路径 {i}:"
                for j, node in enumerate(path):
                    name = node.get("name", "unknown")
                    class_name = node.get("class_name")
                    if class_name:
                        output += f" → {class_name}.{name}"
                    else:
                        output += f" → {name}"

            if len(paths) > 5:
                output += f"\n\n... 还有 {len(paths) - 5} 条路径"
        else:
            output += "\n\n❌ 未找到连接路径"

        return output

    except Exception as e:
        logger.error(f"find_code_paths error: {e}")
        return f"❌ 路径查找失败: {str(e)}"


@tool
def search_code_semantic(query: str, project_id: int = 1, top_k: int = 10) -> str:
    """
    语义搜索代码实体

    Args:
        query: 自然语言查询 (如: "处理用户认证的函数")
        project_id: 项目ID (默认: 1)
        top_k: 返回结果数量 (默认: 10)

    Returns:
        匹配的代码实体列表
    """
    try:
        retriever = get_retriever()

        async def _search():
            return await retriever.retrieve(
                query=query,
                project_id=project_id,
                top_k=top_k,
                include_graph_context=False
            )

        result = _run_async(_search())

        output = f"""🔎 语义搜索结果 [{query}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        semantic_results = result.get("semantic_results", {})

        # 处理 semantic_results 可能是列表或字典的情况
        if isinstance(semantic_results, list):
            # 如果是列表，说明搜索失败或无结果
            if not semantic_results:
                output += "\n\n⚠️ 未找到相关代码实体（可能 ChromaDB 未连接或无数据）"
                return output
            # 如果是非空列表，尝试从第一项获取
            semantic_results = {}

        functions = semantic_results.get("functions", [])
        classes = semantic_results.get("classes", [])

        if functions:
            output += f"\n\n🔧 相关函数 ({len(functions)} 个):"
            for func in functions[:8]:
                metadata = func.get("metadata", {})
                name = metadata.get("name", "unknown")
                module = metadata.get("module_path", "")
                score = func.get("relevance_score", 0)
                output += f"\n  • {name} ({module}) - 相关度: {score:.2f}"

        if classes:
            output += f"\n\n📦 相关类 ({len(classes)} 个):"
            for cls in classes[:8]:
                metadata = cls.get("metadata", {})
                name = metadata.get("name", "unknown")
                module = metadata.get("module_path", "")
                score = cls.get("relevance_score", 0)
                output += f"\n  • {name} ({module}) - 相关度: {score:.2f}"

        if not functions and not classes:
            output += "\n\n⚠️ 未找到相关代码实体"

        return output

    except Exception as e:
        logger.error(f"search_code_semantic error: {e}")
        return f"❌ 搜索失败: {str(e)}"


# 导出所有工具
code_graph_tools = [
    build_code_graph,
    query_code_dependencies,
    analyze_impact,
    find_code_paths,
    search_code_semantic,
]

# 工具描述映射
code_graph_tool_descriptions = {
    "build_code_graph": "构建代码知识图谱，提取函数、类、模块及其关系",
    "query_code_dependencies": "查询代码实体的依赖关系（调用者/被调用者）",
    "analyze_impact": "分析代码变更的影响范围",
    "find_code_paths": "查找两个代码实体之间的调用路径",
    "search_code_semantic": "使用自然语言语义搜索代码实体",
}
