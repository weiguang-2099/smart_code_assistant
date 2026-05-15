"""
Code Graph API Routes - 代码知识图谱 API

提供代码知识图谱的构建、查询和分析接口
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.code_graph.graph_builder import get_graph_builder
from app.services.code_graph.retriever import get_retriever

router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class BuildGraphRequest(BaseModel):
    """构建图谱请求"""
    code: str = Field(..., description="源代码")
    language: str = Field(default="python", description="编程语言")
    module_path: str = Field(default="unknown", description="模块路径")
    project_id: Optional[int] = Field(None, description="项目ID")


class BuildGraphResponse(BaseModel):
    """构建图谱响应"""
    success: bool
    stats: Dict[str, Any]
    entities: Dict[str, int]
    error: Optional[str] = None


class QueryDependenciesRequest(BaseModel):
    """查询依赖请求"""
    entity_name: str = Field(..., description="实体名称")
    dep_type: str = Field(default="all", description="依赖类型: callers, callees, all")


class ImpactAnalysisRequest(BaseModel):
    """影响分析请求"""
    entity_name: str = Field(..., description="实体名称")
    entity_type: str = Field(default="function", description="实体类型")
    max_depth: int = Field(default=3, ge=1, le=5, description="最大搜索深度")


class FindPathsRequest(BaseModel):
    """查找路径请求"""
    source: str = Field(..., description="起始实体")
    target: str = Field(..., description="目标实体")
    max_depth: int = Field(default=5, ge=1, le=10, description="最大搜索深度")


class SemanticSearchRequest(BaseModel):
    """语义搜索请求"""
    query: str = Field(..., description="搜索查询")
    project_id: int = Field(default=1, description="项目ID")
    top_k: int = Field(default=10, ge=1, le=50, description="返回结果数量")


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/build", response_model=BuildGraphResponse)
async def build_code_graph(
    request: BuildGraphRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    构建代码知识图谱

    从源代码中提取函数、类、导入等实体，构建知识图谱
    """
    try:
        builder = get_graph_builder()
        result = await builder.build_from_code(
            code=request.code,
            language=request.language,
            project_id=request.project_id,
            module_path=request.module_path
        )

        return BuildGraphResponse(
            success=result["success"],
            stats=result["stats"],
            entities=result["entities"],
            error=result.get("error")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build code graph: {str(e)}"
        )


@router.get("/stats")
async def get_graph_stats(
    project_id: Optional[int] = Query(None, description="项目ID"),
    current_user: User = Depends(get_current_user),
):
    """
    获取图谱统计信息
    """
    try:
        builder = get_graph_builder()
        stats = await builder.get_graph_statistics(project_id)
        return {"success": True, "stats": stats}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.post("/query")
async def query_dependencies(
    request: QueryDependenciesRequest,
    current_user: User = Depends(get_current_user),
):
    """
    查询代码实体的依赖关系

    - callers: 查询谁调用了该实体
    - callees: 查询该实体调用了谁
    - all: 查询所有依赖
    """
    try:
        retriever = get_retriever()
        result = await retriever.get_dependencies(
            entity_name=request.entity_name,
            dep_type=request.dep_type
        )
        return {"success": True, "result": result}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}"
        )


@router.post("/impact")
async def analyze_impact(
    request: ImpactAnalysisRequest,
    current_user: User = Depends(get_current_user),
):
    """
    分析代码变更的影响范围

    返回受影响的所有代码实体
    """
    try:
        retriever = get_retriever()
        result = await retriever.analyze_impact(
            entity_name=request.entity_name,
            entity_type=request.entity_type,
            max_depth=request.max_depth
        )
        return {"success": True, "result": result}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Impact analysis failed: {str(e)}"
        )


@router.post("/paths")
async def find_paths(
    request: FindPathsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    查找两个代码实体之间的调用路径
    """
    try:
        retriever = get_retriever()
        paths = await retriever.find_paths(
            source=request.source,
            target=request.target,
            max_depth=request.max_depth
        )
        return {"success": True, "paths": paths, "count": len(paths)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Path finding failed: {str(e)}"
        )


@router.post("/search")
async def semantic_search(
    request: SemanticSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    语义搜索代码实体

    使用自然语言查询代码
    """
    try:
        retriever = get_retriever()
        result = await retriever.retrieve(
            query=request.query,
            project_id=request.project_id,
            top_k=request.top_k,
            include_graph_context=True
        )
        return {
            "success": True,
            "query": result["query"],
            "semantic_results": result["semantic_results"],
            "graph_context": result["graph_context"],
            "combined_context": result["combined_context"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.delete("/project/{project_id}")
async def clear_project_graph(
    project_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    清除项目的图谱数据
    """
    try:
        builder = get_graph_builder()
        await builder.clear_graph(project_id)
        return {"success": True, "message": f"Graph data cleared for project {project_id}"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear graph: {str(e)}"
        )


@router.get("/visualize")
async def get_graph_visualization(
    project_id: Optional[int] = Query(None, description="项目ID"),
    module_path: Optional[str] = Query(None, description="模块路径过滤"),
    limit: int = Query(100, ge=1, le=500, description="最大节点数"),
    current_user: User = Depends(get_current_user),
):
    """
    获取图谱可视化数据

    返回节点和边的数据，用于前端可视化
    """
    from app.services.code_graph.neo4j_client import get_neo4j_client

    try:
        neo4j = await get_neo4j_client()

        # 获取节点
        nodes_query = """
        MATCH (n)
        WHERE n:Function OR n:Class OR n:Module
        OPTIONAL MATCH (n)-[r]->(m)
        WHERE m:Function OR m:Class OR m:Module
        WITH n, count(r) as rel_count
        RETURN n.name as name,
               n.module_path as module_path,
               n.class_name as class_name,
               n.docstring as docstring,
               labels(n) as labels,
               rel_count
        ORDER BY rel_count DESC
        LIMIT $limit
        """
        nodes_result = await neo4j.execute_query(nodes_query, {"limit": limit})

        # 获取边（关系）
        edges_query = """
        MATCH (source)-[r]->(target)
        WHERE (source:Function OR source:Class OR source:Module)
        AND (target:Function OR target:Class OR target:Module)
        RETURN source.name as source_name,
               source.module_path as source_module,
               type(r) as relationship,
               target.name as target_name,
               target.module_path as target_module
        LIMIT $limit
        """
        edges_result = await neo4j.execute_query(edges_query, {"limit": limit * 2})

        # 处理节点数据
        nodes = []
        node_ids = set()

        for node in nodes_result:
            # 生成唯一ID
            node_id = f"{node.get('module_path', '')}:{node.get('name', '')}"
            if node.get('class_name'):
                node_id += f":{node.get('class_name')}"

            if node_id in node_ids:
                continue
            node_ids.add(node_id)

            # 确定节点类型
            labels = node.get('labels', [])
            if 'Function' in labels:
                node_type = 'function'
                color = '#22d3ee'  # cyan
            elif 'Class' in labels:
                node_type = 'class'
                color = '#a855f7'  # purple
            elif 'Module' in labels:
                node_type = 'module'
                color = '#22c55e'  # green
            else:
                node_type = 'unknown'
                color = '#6b7280'  # gray

            nodes.append({
                "id": node_id,
                "label": node.get('name', 'unknown'),
                "type": node_type,
                "color": color,
                "module": node.get('module_path', ''),
                "class": node.get('class_name'),
                "docstring": node.get('docstring', '')[:100] if node.get('docstring') else None,
            })

        # 处理边数据
        edges = []
        edge_ids = set()

        for edge in edges_result:
            source_id = f"{edge.get('source_module', '')}:{edge.get('source_name', '')}"
            target_id = f"{edge.get('target_module', '')}:{edge.get('target_name', '')}"

            edge_id = f"{source_id}->{target_id}"
            if edge_id in edge_ids:
                continue
            edge_ids.add(edge_id)

            # 关系类型映射
            rel = edge.get('relationship', 'RELATES')
            if rel == 'CALLS':
                color = '#f97316'  # orange
            elif rel == 'HAS_METHOD':
                color = '#22d3ee'  # cyan
            elif rel == 'CONTAINS':
                color = '#22c55e'  # green
            elif rel == 'INHERITS_FROM':
                color = '#ec4899'  # pink
            else:
                color = '#6b7280'  # gray

            edges.append({
                "id": edge_id,
                "source": source_id,
                "target": target_id,
                "label": rel,
                "color": color,
            })

        return {
            "success": True,
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph data: {str(e)}"
        )
