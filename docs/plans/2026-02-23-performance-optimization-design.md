# Smart Code Assistant 性能优化设计文档

> 日期: 2026-02-23
> 状态: 已确认
> 优先级: P0 + P1

## 一、背景与目标

### 1.1 问题概述

当前系统在 GraphRAG 检索和 Agent 对话两个核心场景存在明显的性能问题：

- **GraphRAG 检索**：语义搜索和图遍历串行执行，每个实体单独查询，无缓存机制
- **Agent 对话**：工具串行调用，无流式响应，对话历史无限增长导致 token 暴涨

### 1.2 优化目标

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| Agent 工具分析延迟 | ~4s | ~1s | 4x |
| GraphRAG 检索延迟 | ~2s | ~1s | 2x |
| 首字响应时间 | ~3s | <500ms | 6x |
| 对话 token 使用 | 无限制 | <4000 | 可控 |
| 重复查询命中延迟 | N/A | <50ms | 新增 |

---

## 二、P0 优化方案

### 2.1 工具并行调用

**文件**: `backend-fastapi/app/api/agent.py`

**当前实现**:
```python
async def run_tool_analysis(code: str, language: str) -> Dict[str, str]:
    results = {}
    for tool in langchain_tools:
        result = tool.invoke({"code": code, "language": language})
        results[tool.name] = result
    return results
```

**优化方案**:
```python
async def run_tool_analysis(code: str, language: str) -> Dict[str, str]:
    independent_tools = [
        analyze_code_structure,
        detect_code_smells,
        calculate_code_complexity,
        check_security_issues,
    ]

    tasks = [
        asyncio.to_thread(tool.invoke, {"code": code, "language": language})
        for tool in independent_tools
    ]

    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        tool.name: result if not isinstance(result, Exception) else f"分析失败: {result}"
        for tool, result in zip(independent_tools, results_list)
    }
```

### 2.2 流式响应 (SSE)

**新增文件**: `backend-fastapi/app/api/agent_stream.py`

**后端实现**:
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

router = APIRouter()

@router.post("/chat/stream")
async def agent_chat_stream(request: AgentChatRequest, ...):
    async def generate():
        async for chunk in langchain_glm_service.stream_chat(
            system_prompt=system_prompt,
            user_prompt=enhanced_message,
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )
```

**前端实现** (新增 hook):
```typescript
// frontend/src/hooks/useStreamChat.ts
export const useStreamChat = () => {
  const streamChat = async (
    message: string,
    history: Message[],
    onChunk: (chunk: string) => void
  ) => {
    const response = await fetch(`${API_URL}/api/v1/agent/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ message, history, language: 'python' }),
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    while (reader) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n').filter(line => line.startsWith('data: '))

      for (const line of lines) {
        const data = line.replace('data: ', '')
        if (data === '[DONE]') return
        onChunk(JSON.parse(data).content)
      }
    }
  }

  return { streamChat }
}
```

---

## 三、P1 优化方案

### 3.1 GraphRAG 并行查询

**文件**: `backend-fastapi/app/services/code_graph/retriever.py`

**当前实现**:
```python
async def retrieve(self, query: str, ...):
    # 1. 语义搜索 (串行)
    if project_id and self.config.enable_semantic_search:
        semantic_results = chromadb.search_all(query, project_id, top_k)

    # 2. 图遍历 (串行)
    if include_graph_context:
        for entity_name in entity_names[:3]:
            related = await neo4j.search_entities(entity_name, limit=5)
            callers = await neo4j.get_function_callers(entity_name)
            callees = await neo4j.get_function_callees(entity_name)
```

**优化方案**:
```python
async def retrieve(self, query: str, ...):
    # 并行执行语义搜索和图遍历
    async def semantic_search():
        if project_id and self.config.enable_semantic_search:
            return await asyncio.to_thread(
                self._get_chromadb().search_all, query, project_id, top_k
            )
        return []

    async def graph_traversal():
        if not include_graph_context:
            return []
        entity_names = self._extract_entity_names(query)
        return await self._batch_graph_query(entity_names[:3])

    semantic_results, graph_context = await asyncio.gather(
        semantic_search(),
        graph_traversal(),
        return_exceptions=True
    )

    return self._build_result(query, semantic_results, graph_context)

async def _batch_graph_query(self, entity_names: List[str]) -> List[Dict]:
    """批量查询图数据"""
    neo4j = await self._get_neo4j()
    return await neo4j.batch_get_entity_context(entity_names)
```

**Neo4j 批量查询** (新增方法):
```python
# backend-fastapi/app/services/code_graph/neo4j_client.py

async def batch_get_entity_context(self, entity_names: List[str]) -> List[Dict]:
    """批量获取实体上下文"""
    query = """
    UNWIND $names as name
    MATCH (e) WHERE e.name = name AND (e:Function OR e:Class)
    OPTIONAL MATCH (caller:Function)-[:CALLS]->(e)
    OPTIONAL MATCH (e)-[:CALLS]->(callee:Function)
    RETURN e.name as entity,
           labels(e)[0] as type,
           e.module_path as module_path,
           count(DISTINCT caller) as callers_count,
           count(DISTINCT callee) as callees_count
    """
    return await self.execute_query(query, {"names": entity_names})
```

### 3.2 对话历史压缩

**新增文件**: `backend-fastapi/app/services/conversation_manager.py`

```python
from typing import List, Dict
from app.services.langchain_glm_service import glm_service_flash

class ConversationManager:
    """对话管理器 - 处理历史压缩和 token 控制"""

    MAX_TURNS = 10
    MAX_TOKENS = 4000
    SUMMARY_THRESHOLD = 6  # 超过 6 轮时开始压缩

    def __init__(self, max_turns: int = None, max_tokens: int = None):
        self.max_turns = max_turns or self.MAX_TURNS
        self.max_tokens = max_tokens or self.MAX_TOKENS

    def compress_history(self, history: List[Dict]) -> List[Dict]:
        """压缩对话历史"""
        if len(history) <= self.SUMMARY_THRESHOLD:
            return history

        # 保留最近的对话
        keep_turns = self.max_turns - 2
        recent = history[-(keep_turns * 2):]  # 保留最近 N 轮 (每轮 2 条消息)

        # 对早期对话生成摘要
        old_messages = history[:-(keep_turns * 2)]
        if old_messages:
            summary = self._create_summary_context(old_messages)
            return [{"role": "system", "content": summary}] + recent

        return recent

    def _create_summary_context(self, messages: List[Dict]) -> str:
        """创建摘要上下文"""
        conversation_text = self._format_messages(messages)
        return f"[历史对话摘要]\n之前的讨论主要涉及: {conversation_text[:500]}"

    def _format_messages(self, messages: List[Dict]) -> str:
        """格式化消息列表"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]  # 截断长消息
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def estimate_tokens(self, messages: List[Dict]) -> int:
        """估算 token 数量 (简单估算: 1 token ≈ 4 chars)"""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return total_chars // 4

    def truncate_if_needed(self, messages: List[Dict]) -> List[Dict]:
        """如果超过 token 限制则截断"""
        if self.estimate_tokens(messages) <= self.max_tokens:
            return messages

        # 从最早的对话开始截断
        while messages and self.estimate_tokens(messages) > self.max_tokens:
            messages = messages[2:]  # 移除最早的一轮对话

        return messages


# 全局实例
conversation_manager = ConversationManager()
```

**集成到 Agent API**:
```python
# backend-fastapi/app/api/agent.py

from app.services.conversation_manager import conversation_manager

@router.post("/chat")
async def agent_chat(request: AgentChatRequest, ...):
    # 压缩历史
    compressed_history = conversation_manager.compress_history(request.history)
    compressed_history = conversation_manager.truncate_if_needed(compressed_history)

    # 使用压缩后的历史调用 LLM
    response = await langchain_glm_service.chat_with_history(
        user_message=enhanced_message,
        history=compressed_history,
        system_prompt=system_prompt,
    )
    ...
```

---

## 四、实现计划

### Phase 1: P0 优化 (1-2 天)

| 任务 | 文件 | 依赖 |
|------|------|------|
| 1.1 工具并行调用 | `agent.py` | 无 |
| 1.2 流式响应后端 | `agent_stream.py` (新建) | 无 |
| 1.3 流式响应前端 | `useStreamChat.ts` (新建) | 1.2 |
| 1.4 AgentChatPage 集成 | `AgentChatPage.tsx` | 1.3 |

### Phase 2: P1 优化 (1-2 天)

| 任务 | 文件 | 依赖 |
|------|------|------|
| 2.1 批量图查询 | `neo4j_client.py` | 无 |
| 2.2 Retriever 并行化 | `retriever.py` | 2.1 |
| 2.3 对话管理器 | `conversation_manager.py` (新建) | 无 |
| 2.4 Agent 集成压缩 | `agent.py` | 2.3 |

### Phase 3: 测试与验证 (1 天)

| 任务 | 描述 |
|------|------|
| 3.1 单元测试 | 为新模块编写测试 |
| 3.2 性能基准测试 | 对比优化前后延迟 |
| 3.3 集成测试 | 端到端功能验证 |

---

## 五、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 并行调用异常传播 | 部分结果丢失 | 使用 `return_exceptions=True` |
| 流式连接中断 | 用户看到不完整响应 | 添加重连机制和错误提示 |
| 历史压缩信息丢失 | 上下文不完整 | 保留关键信息摘要 |
| Neo4j 批量查询超时 | 查询失败 | 添加超时控制和降级策略 |

---

## 六、验收标准

1. **工具并行调用**: 4 个工具总执行时间 < 1.5s (原 ~4s)
2. **流式响应**: 首字响应时间 < 500ms
3. **GraphRAG 检索**: 检索延迟 < 1s (原 ~2s)
4. **对话历史**: 历史消息控制在 4000 token 以内
5. **无功能回退**: 所有现有功能正常工作
