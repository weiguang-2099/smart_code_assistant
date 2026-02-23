# Performance Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimize GraphRAG retrieval and Agent chat performance through parallel execution, streaming responses, and conversation compression.

**Architecture:**
- P0: Parallel tool calls using asyncio.gather + SSE streaming for LLM responses
- P1: Parallel GraphRAG queries + batch Neo4j operations + conversation history compression
- All optimizations maintain backward compatibility with existing APIs

**Tech Stack:** Python asyncio, FastAPI StreamingResponse, Server-Sent Events (SSE), React hooks

**Parallel Execution Groups:**
- Group A (Backend P0): Tasks 1-2 (tool parallelization, streaming backend)
- Group B (Frontend P0): Tasks 3-4 (streaming hook, UI integration) - depends on Group A
- Group C (Backend P1): Tasks 5-8 (batch queries, retriever, conversation manager)

---

## Task 1: Parallel Tool Invocation (P0)

**Files:**
- Modify: `backend-fastapi/app/api/agent.py:100-122`
- Test: `backend-fastapi/tests/test_agent_parallel.py` (create)

**Step 1: Write the failing test**

Create `backend-fastapi/tests/test_agent_parallel.py`:

```python
"""Tests for parallel tool execution"""
import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock

from app.api.agent import run_tool_analysis


class TestParallelToolAnalysis:
    """Test parallel tool execution"""

    @pytest.mark.asyncio
    async def test_run_tool_analysis_returns_all_results(self):
        """Should return results for all 4 tools"""
        code = "def hello():\n    print('hello')"
        language = "python"

        result = await run_tool_analysis(code, language)

        assert "analyze_code_structure" in result
        assert "detect_code_smells" in result
        assert "calculate_code_complexity" in result
        assert "check_security_issues" in result

    @pytest.mark.asyncio
    async def test_parallel_execution_is_faster_than_sequential(self):
        """Parallel execution should be significantly faster"""
        code = "def hello():\n    print('hello')"
        language = "python"

        # Each tool takes ~0.5s, 4 tools sequentially = 2s
        # Parallel should be ~0.5s
        start = time.time()
        await run_tool_analysis(code, language)
        elapsed = time.time() - start

        # Should complete in less than 1 second (allowing overhead)
        assert elapsed < 1.5, f"Parallel execution took {elapsed}s, expected < 1.5s"

    @pytest.mark.asyncio
    async def test_handles_tool_exceptions_gracefully(self):
        """Should not fail if one tool throws an exception"""
        code = "def hello():\n    print('hello')"
        language = "python"

        result = await run_tool_analysis(code, language)

        # All results should be strings (either result or error message)
        for tool_name, tool_result in result.items():
            assert isinstance(tool_result, str), f"{tool_name} result should be string"
```

**Step 2: Run test to verify it fails**

Run: `cd backend-fastapi && python -m pytest tests/test_agent_parallel.py -v`
Expected: FAIL (function not async or not parallel)

**Step 3: Write minimal implementation**

Modify `backend-fastapi/app/api/agent.py`:

```python
# Add import at top of file (around line 6)
import asyncio

# Replace run_tool_analysis function (lines 100-122) with:
async def run_tool_analysis(code: str, language: str) -> Dict[str, str]:
    """
    Run all tools for analysis in parallel

    Args:
        code: The code to analyze
        language: Programming language

    Returns:
        Dict of tool name to analysis result
    """
    from app.services.code_tools import (
        analyze_code_structure,
        detect_code_smells,
        calculate_code_complexity,
        check_security_issues,
    )

    # Independent tools that can run in parallel
    independent_tools = [
        analyze_code_structure,
        detect_code_smells,
        calculate_code_complexity,
        check_security_issues,
    ]

    # Create parallel tasks
    tasks = [
        asyncio.to_thread(tool.invoke, {"code": code, "language": language})
        for tool in independent_tools
    ]

    # Execute all tasks in parallel, capturing exceptions
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    # Build results dict with error handling
    return {
        tool.name: result if not isinstance(result, Exception) else f"分析失败: {str(result)}"
        for tool, result in zip(independent_tools, results_list)
    }
```

**Step 4: Run test to verify it passes**

Run: `cd backend-fastapi && python -m pytest tests/test_agent_parallel.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend-fastapi/app/api/agent.py backend-fastapi/tests/test_agent_parallel.py
git commit -m "perf: parallelize tool analysis with asyncio.gather"
```

---

## Task 2: Streaming Response Backend (P0)

**Files:**
- Create: `backend-fastapi/app/api/agent_stream.py`
- Modify: `backend-fastapi/app/main.py` (add router)
- Test: `backend-fastapi/tests/test_agent_stream.py` (create)

**Step 1: Write the failing test**

Create `backend-fastapi/tests/test_agent_stream.py`:

```python
"""Tests for streaming agent endpoints"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app


class TestAgentStream:
    """Test streaming chat endpoint"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_stream_endpoint_exists(self, client, mock_auth):
        """Stream endpoint should be accessible"""
        # Mock auth dependency
        with patch('app.core.deps.get_current_user', return_value=mock_auth):
            response = client.post(
                "/api/v1/agent/chat/stream",
                json={"message": "hello", "history": [], "language": "python"},
                headers={"Authorization": "Bearer test-token"}
            )
            # Should not return 404
            assert response.status_code != 404

    def test_stream_returns_sse_format(self, client, mock_auth):
        """Should return Server-Sent Events format"""
        mock_chunks = ["Hello", " world", "!"]

        async def mock_stream(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk

        with patch('app.core.deps.get_current_user', return_value=mock_auth):
            with patch('app.services.langchain_glm_service.langchain_glm_service.stream_chat', mock_stream):
                response = client.post(
                    "/api/v1/agent/chat/stream",
                    json={"message": "hello", "history": [], "language": "python"},
                    headers={"Authorization": "Bearer test-token"}
                )

                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")

                # Check SSE format
                content = response.text
                assert "data:" in content
                assert "[DONE]" in content

    @pytest.fixture
    def mock_auth(self):
        """Mock authenticated user"""
        from app.models.user import User
        return User(id=1, username="test", email="test@test.com", hashed_password="x")
```

**Step 2: Run test to verify it fails**

Run: `cd backend-fastapi && python -m pytest tests/test_agent_stream.py -v`
Expected: FAIL (endpoint not found)

**Step 3: Create streaming endpoint**

Create `backend-fastapi/app/api/agent_stream.py`:

```python
"""
Streaming Agent API Routes - SSE streaming endpoints

Provides Server-Sent Events streaming for real-time AI responses
"""
import json
import re
import logging
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.langchain_glm_service import langchain_glm_service

logger = logging.getLogger(__name__)
router = APIRouter()


class StreamChatRequest(BaseModel):
    """Streaming chat request"""
    message: str = Field(..., description="User message")
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    language: str = Field(default="python")


@router.post("/chat/stream")
async def agent_chat_stream(
    request: StreamChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream agent chat response using Server-Sent Events

    Returns SSE stream with format:
    - data: {"content": "chunk"} for each chunk
    - data: [DONE] when complete
    """
    try:
        # Build system prompt
        system_prompt = f"""你是一个专业的编程助手，精通 {request.language} 语言。
提供清晰、准确的答案。
显示代码时使用 markdown 代码块。"""

        # Detect code blocks in message for context
        code_blocks = _extract_code_blocks(request.message)

        # Enhance message with code context if present
        enhanced_message = request.message
        if code_blocks:
            enhanced_message += f"\n\n[检测到代码块: {len(code_blocks)} 个]"

        async def generate():
            try:
                async for chunk in langchain_glm_service.stream_chat(
                    system_prompt=system_prompt,
                    user_prompt=enhanced_message,
                ):
                    # SSE format: data: {json}\n\n
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

                # Signal completion
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    except Exception as e:
        logger.error(f"Failed to start stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stream initialization failed: {str(e)}"
        )


def _extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """Extract code blocks from text"""
    pattern = r'```(\w*)\n([\s\S]*?)```'
    blocks = []
    for match in re.finditer(pattern, text):
        blocks.append({
            "language": match.group(1) or "text",
            "code": match.group(2)
        })
    return blocks
```

**Step 4: Register router in main.py**

Add to `backend-fastapi/app/main.py` (find the router imports section and add):

```python
# Add import (around line 15-20 where other routers are imported)
from app.api.agent_stream import router as agent_stream_router

# Add router registration (around line 40-50 where other routers are included)
app.include_router(agent_stream_router, prefix="/api/v1/agent", tags=["agent-stream"])
```

**Step 5: Run test to verify it passes**

Run: `cd backend-fastapi && python -m pytest tests/test_agent_stream.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend-fastapi/app/api/agent_stream.py backend-fastapi/app/main.py backend-fastapi/tests/test_agent_stream.py
git commit -m "feat: add SSE streaming endpoint for agent chat"
```

---

## Task 3: Frontend Streaming Hook (P0)

**Depends on:** Task 2

**Files:**
- Create: `frontend/src/hooks/useStreamChat.ts`
- Test: `frontend/src/hooks/__tests__/useStreamChat.test.ts` (create)

**Step 1: Create the streaming hook**

Create `frontend/src/hooks/useStreamChat.ts`:

```typescript
/**
 * useStreamChat - Hook for streaming chat responses via SSE
 *
 * Usage:
 * const { streamChat, isStreaming, error } = useStreamChat()
 * await streamChat(message, history, (chunk) => setResponse(prev => prev + chunk))
 */
import { useState, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

interface StreamChatOptions {
  language?: string
  onError?: (error: string) => void
  onComplete?: (fullResponse: string) => void
}

export const useStreamChat = () => {
  const { token } = useAuth()
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const streamChat = useCallback(
    async (
      message: string,
      history: Message[],
      onChunk: (chunk: string) => void,
      options: StreamChatOptions = {}
    ): Promise<void> => {
      if (!token) {
        setError('Not authenticated')
        return
      }

      const { language = 'python', onError, onComplete } = options
      setIsStreaming(true)
      setError(null)

      let fullResponse = ''

      try {
        const response = await fetch(`${API_URL}/api/v1/agent/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            message,
            history,
            language,
          }),
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('Response body is not readable')
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()

          if (done) break

          // Decode chunk and add to buffer
          buffer += decoder.decode(value, { stream: true })

          // Process complete SSE messages from buffer
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()

              if (data === '[DONE]') {
                // Stream complete
                onComplete?.(fullResponse)
                return
              }

              try {
                const parsed = JSON.parse(data)

                if (parsed.error) {
                  throw new Error(parsed.error)
                }

                if (parsed.content) {
                  fullResponse += parsed.content
                  onChunk(parsed.content)
                }
              } catch (parseError) {
                // Skip malformed JSON
                console.warn('Failed to parse SSE data:', data)
              }
            }
          }
        }

        onComplete?.(fullResponse)
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error'
        setError(errorMessage)
        onError?.(errorMessage)
        console.error('Stream error:', err)
      } finally {
        setIsStreaming(false)
      }
    },
    [token]
  )

  const cancel = useCallback(() => {
    // Note: For full cancellation, we'd need to store the AbortController
    // This is a simplified version
    setIsStreaming(false)
    setError('Cancelled by user')
  }, [])

  return {
    streamChat,
    isStreaming,
    error,
    cancel,
  }
}

export default useStreamChat
```

**Step 2: Create test file**

Create `frontend/src/hooks/__tests__/useStreamChat.test.ts`:

```typescript
import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useStreamChat } from '../useStreamChat'

// Mock AuthContext
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    token: 'test-token',
  }),
}))

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('useStreamChat', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('should initialize with correct default state', () => {
    const { result } = renderHook(() => useStreamChat())

    expect(result.current.isStreaming).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('should set isStreaming to true during streaming', async () => {
    const mockReader = {
      read: vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"content": "Hello"}\n\n'),
        })
        .mockResolvedValueOnce({ done: true, value: undefined }),
    }

    mockFetch.mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    const { result } = renderHook(() => useStreamChat())
    const onChunk = vi.fn()

    act(() => {
      result.current.streamChat('test message', [], onChunk)
    })

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(true)
    })
  })

  it('should call onChunk for each content chunk', async () => {
    const mockReader = {
      read: vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"content": "Hello "}\n\ndata: {"content": "world"}\n\n'),
        })
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: [DONE]\n\n'),
        })
        .mockResolvedValueOnce({ done: true, value: undefined }),
    }

    mockFetch.mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    const { result } = renderHook(() => useStreamChat())
    const onChunk = vi.fn()

    await act(async () => {
      await result.current.streamChat('test message', [], onChunk)
    })

    expect(onChunk).toHaveBeenCalledWith('Hello ')
    expect(onChunk).toHaveBeenCalledWith('world')
  })
})
```

**Step 3: Commit**

```bash
git add frontend/src/hooks/useStreamChat.ts frontend/src/hooks/__tests__/useStreamChat.test.ts
git commit -m "feat: add useStreamChat hook for SSE streaming"
```

---

## Task 4: Integrate Streaming into AgentChatPage (P0)

**Depends on:** Task 3

**Files:**
- Modify: `frontend/src/pages/AgentChatPage.tsx`

**Step 1: Read current AgentChatPage**

Read the file to understand its structure, then integrate streaming.

**Step 2: Integrate streaming hook**

Modify `frontend/src/pages/AgentChatPage.tsx`:

Add import:
```typescript
import { useStreamChat } from '../hooks/useStreamChat'
```

Add hook usage in component:
```typescript
// Inside the component function
const { streamChat, isStreaming, error: streamError } = useStreamChat()
const [streamingResponse, setStreamingResponse] = useState('')
```

Add streaming send function:
```typescript
const sendStreamingMessage = async () => {
  if (!inputMessage.trim()) return

  const userMessage = { role: 'user' as const, content: inputMessage }
  setMessages(prev => [...prev, userMessage])
  setInputMessage('')
  setStreamingResponse('')

  await streamChat(
    inputMessage,
    messages.map(m => ({ role: m.role, content: m.content })),
    (chunk) => {
      setStreamingResponse(prev => prev + chunk)
    },
    {
      onComplete: (fullResponse) => {
        setMessages(prev => [...prev, { role: 'assistant', content: fullResponse }])
        setStreamingResponse('')
      },
      onError: (error) => {
        console.error('Stream error:', error)
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Error: ${error}`
        }])
      }
    }
  )
}
```

**Step 3: Update UI to show streaming response**

Add a message component for streaming:
```typescript
{/* Streaming response indicator */}
{isStreaming && streamingResponse && (
  <div className="message assistant streaming">
    <div className="content">
      {streamingResponse}
      <span className="cursor-blink">▌</span>
    </div>
  </div>
)}
```

Add CSS for streaming cursor:
```css
.cursor-blink {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
```

**Step 4: Commit**

```bash
git add frontend/src/pages/AgentChatPage.tsx
git commit -m "feat: integrate streaming chat into AgentChatPage"
```

---

## Task 5: Batch Neo4j Entity Query (P1)

**Files:**
- Modify: `backend-fastapi/app/services/code_graph/neo4j_client.py`
- Test: `backend-fastapi/tests/test_neo4j_batch.py` (create)

**Step 1: Write the failing test**

Create `backend-fastapi/tests/test_neo4j_batch.py`:

```python
"""Tests for batch Neo4j operations"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestBatchEntityQuery:
    """Test batch entity context retrieval"""

    @pytest.mark.asyncio
    async def test_batch_get_entity_context_returns_list(self):
        """Should return a list of entity contexts"""
        from app.services.code_graph.neo4j_client import Neo4jClient

        client = Neo4jClient()
        client._driver = MagicMock()

        mock_result = [
            {"entity": "function_a", "type": "Function", "callers_count": 2, "callees_count": 3},
            {"entity": "ClassB", "type": "Class", "callers_count": 0, "callees_count": 5},
        ]

        with patch.object(client, 'execute_query', AsyncMock(return_value=mock_result)):
            result = await client.batch_get_entity_context(["function_a", "ClassB"])

            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["entity"] == "function_a"

    @pytest.mark.asyncio
    async def test_batch_query_uses_unwind(self):
        """Should use UNWIND for batch processing"""
        from app.services.code_graph.neo4j_client import Neo4jClient

        client = Neo4jClient()
        client._driver = MagicMock()

        mock_execute = AsyncMock(return_value=[])
        with patch.object(client, 'execute_query', mock_execute):
            await client.batch_get_entity_context(["func1", "func2"])

            # Check that query uses UNWIND
            call_args = mock_execute.call_args
            query = call_args[0][0]
            assert "UNWIND" in query.upper()
            assert "$names" in query
```

**Step 2: Run test to verify it fails**

Run: `cd backend-fastapi && python -m pytest tests/test_neo4j_batch.py -v`
Expected: FAIL (method doesn't exist)

**Step 3: Add batch query method**

Add to `backend-fastapi/app/services/code_graph/neo4j_client.py` (after line 394):

```python
    async def batch_get_entity_context(
        self,
        entity_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Batch retrieve context for multiple entities in a single query.

        Args:
            entity_names: List of entity names to query

        Returns:
            List of entity contexts with caller/callee counts
        """
        if not entity_names:
            return []

        query = """
        UNWIND $names as name
        MATCH (e) WHERE e.name = name AND (e:Function OR e:Class)
        OPTIONAL MATCH (caller:Function)-[:CALLS]->(e)
        OPTIONAL MATCH (e)-[:CALLS]->(callee:Function)
        RETURN e.name as entity,
               labels(e)[0] as type,
               e.module_path as module_path,
               e.class_name as class_name,
               count(DISTINCT caller) as callers_count,
               count(DISTINCT callee) as callees_count
        """
        return await self.execute_query(query, {"names": entity_names})
```

**Step 4: Run test to verify it passes**

Run: `cd backend-fastapi && python -m pytest tests/test_neo4j_batch.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend-fastapi/app/services/code_graph/neo4j_client.py backend-fastapi/tests/test_neo4j_batch.py
git commit -m "perf: add batch entity query to Neo4j client"
```

---

## Task 6: Parallelize GraphRAG Retriever (P1)

**Depends on:** Task 5

**Files:**
- Modify: `backend-fastapi/app/services/code_graph/retriever.py`
- Test: `backend-fastapi/tests/test_retriever_parallel.py` (create)

**Step 1: Write the failing test**

Create `backend-fastapi/tests/test_retriever_parallel.py`:

```python
"""Tests for parallel retriever operations"""
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock


class TestParallelRetriever:
    """Test parallel retrieval execution"""

    @pytest.mark.asyncio
    async def test_retrieve_runs_semantic_and_graph_in_parallel(self):
        """Semantic and graph queries should run concurrently"""
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()

        # Mock methods with artificial delay
        def slow_search(*args, **kwargs):
            time.sleep(0.1)
            return {"functions": [], "classes": []}

        async def slow_graph(*args, **kwargs):
            time.sleep(0.1)
            return []

        retriever._chromadb.search_all = slow_search

        with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
            with patch.object(retriever._neo4j, 'batch_get_entity_context', slow_graph):
                start = time.time()
                await retriever.retrieve(
                    query="test function",
                    project_id=1,
                    include_graph_context=True
                )
                elapsed = time.time() - start

                # If parallel, should be ~0.1s, not ~0.2s
                assert elapsed < 0.25, f"Retrieval took {elapsed}s, expected < 0.25s"

    @pytest.mark.asyncio
    async def test_retrieve_handles_semantic_failure_gracefully(self):
        """Should still return graph results if semantic search fails"""
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()

        retriever._chromadb.search_all = MagicMock(side_effect=Exception("ChromaDB error"))

        with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
            with patch.object(retriever._neo4j, 'batch_get_entity_context', AsyncMock(return_value=[{"entity": "test"}])):
                result = await retriever.retrieve(
                    query="test",
                    project_id=1,
                    include_graph_context=True
                )

                # Should have graph results even if semantic failed
                assert result.get("graph_context") is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend-fastapi && python -m pytest tests/test_retriever_parallel.py -v`
Expected: FAIL (not parallel yet)

**Step 3: Implement parallel retrieval**

Replace `retrieve` method in `backend-fastapi/app/services/code_graph/retriever.py` (lines 39-107):

```python
    async def retrieve(
        self,
        query: str,
        project_id: Optional[int] = None,
        top_k: int = 10,
        include_graph_context: bool = True,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Hybrid retrieval with parallel semantic and graph queries

        Args:
            query: Query text
            project_id: Project ID
            top_k: Number of results
            include_graph_context: Whether to include graph traversal
            max_depth: Max graph traversal depth

        Returns:
            Retrieval results
        """
        import asyncio

        result = {
            "query": query,
            "semantic_results": [],
            "graph_context": None,
            "combined_context": ""
        }

        # Define parallel tasks
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
                return []

            try:
                neo4j = await self._get_neo4j()
                entity_names = self._extract_entity_names(query)
                return await neo4j.batch_get_entity_context(entity_names[:3])
            except Exception as e:
                logger.warning(f"Graph traversal failed: {e}")
                return []

        # Execute in parallel
        semantic_results, graph_context = await asyncio.gather(
            semantic_search(),
            graph_traversal(),
            return_exceptions=False
        )

        result["semantic_results"] = semantic_results
        result["graph_context"] = graph_context

        # Build combined context
        result["combined_context"] = self._build_combined_context(result)

        return result
```

**Step 4: Run test to verify it passes**

Run: `cd backend-fastapi && python -m pytest tests/test_retriever_parallel.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend-fastapi/app/services/code_graph/retriever.py backend-fastapi/tests/test_retriever_parallel.py
git commit -m "perf: parallelize GraphRAG semantic and graph queries"
```

---

## Task 7: Conversation Manager (P1)

**Files:**
- Create: `backend-fastapi/app/services/conversation_manager.py`
- Test: `backend-fastapi/tests/test_conversation_manager.py` (create)

**Step 1: Write the failing test**

Create `backend-fastapi/tests/test_conversation_manager.py`:

```python
"""Tests for conversation manager"""
import pytest
from app.services.conversation_manager import ConversationManager


class TestConversationManager:
    """Test conversation history management"""

    def test_compress_history_returns_unchanged_when_short(self):
        """Short history should not be compressed"""
        manager = ConversationManager()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = manager.compress_history(history)

        assert result == history

    def test_compress_history_adds_summary_when_long(self):
        """Long history should include summary"""
        manager = ConversationManager(max_turns=4)

        # Create 8 messages (4 turns)
        history = []
        for i in range(4):
            history.append({"role": "user", "content": f"Question {i}"})
            history.append({"role": "assistant", "content": f"Answer {i}"})

        result = manager.compress_history(history)

        # Should have summary + recent messages
        assert len(result) <= 6  # summary + 2 turns (4 messages)
        assert any("摘要" in msg.get("content", "") or "summary" in msg.get("content", "").lower() for msg in result if msg.get("role") == "system")

    def test_estimate_tokens_counts_correctly(self):
        """Token estimation should be reasonable"""
        manager = ConversationManager()

        messages = [
            {"role": "user", "content": "Hello world"},  # ~3 tokens
            {"role": "assistant", "content": "Hi there!"},  # ~3 tokens
        ]

        tokens = manager.estimate_tokens(messages)

        # ~6 tokens * 4 chars = ~24 chars / 4 = ~6 tokens
        assert 3 <= tokens <= 10

    def test_truncate_if_needed_removes_old_messages(self):
        """Should remove old messages when over token limit"""
        manager = ConversationManager(max_tokens=50)

        # Create long messages
        history = [
            {"role": "user", "content": "x" * 100},  # 25 tokens
            {"role": "assistant", "content": "y" * 100},  # 25 tokens
            {"role": "user", "content": "z" * 100},  # 25 tokens
            {"role": "assistant", "content": "w" * 100},  # 25 tokens
        ]

        result = manager.truncate_if_needed(history)

        # Should remove messages to get under 50 tokens
        estimated = manager.estimate_tokens(result)
        assert estimated <= 50
```

**Step 2: Run test to verify it fails**

Run: `cd backend-fastapi && python -m pytest tests/test_conversation_manager.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Create conversation manager**

Create `backend-fastapi/app/services/conversation_manager.py`:

```python
"""
Conversation Manager - Handles conversation history compression and token control

Provides utilities to manage conversation history length and token usage
for LLM interactions.
"""
from typing import List, Dict, Optional


class ConversationManager:
    """
    Manages conversation history with compression and token control.

    Features:
    - Sliding window for recent messages
    - Summary generation for old messages
    - Token counting and limiting
    """

    MAX_TURNS = 10
    MAX_TOKENS = 4000
    SUMMARY_THRESHOLD = 6  # Turns before compression kicks in

    def __init__(
        self,
        max_turns: Optional[int] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize conversation manager.

        Args:
            max_turns: Maximum turns to keep (default: 10)
            max_tokens: Maximum tokens allowed (default: 4000)
        """
        self.max_turns = max_turns or self.MAX_TURNS
        self.max_tokens = max_tokens or self.MAX_TOKENS

    def compress_history(self, history: List[Dict]) -> List[Dict]:
        """
        Compress conversation history if too long.

        Args:
            history: List of message dicts with 'role' and 'content'

        Returns:
            Compressed history with summary of old messages
        """
        if len(history) <= self.SUMMARY_THRESHOLD:
            return history

        # Calculate how many turns to keep
        keep_turns = min(self.max_turns - 1, len(history) // 2)
        keep_messages = keep_turns * 2

        # Keep recent messages
        recent = history[-keep_messages:] if keep_messages > 0 else []

        # Create summary of old messages
        old_messages = history[:-keep_messages] if keep_messages > 0 else history

        if old_messages:
            summary = self._create_summary_context(old_messages)
            return [{"role": "system", "content": summary}] + recent

        return recent

    def _create_summary_context(self, messages: List[Dict]) -> str:
        """
        Create summary context from old messages.

        Args:
            messages: List of old message dicts

        Returns:
            Summary string
        """
        conversation_text = self._format_messages(messages)

        # Truncate if too long
        if len(conversation_text) > 500:
            conversation_text = conversation_text[:500] + "..."

        return f"[历史对话摘要]\n之前的讨论主要涉及: {conversation_text}"

    def _format_messages(self, messages: List[Dict]) -> str:
        """
        Format messages into readable text.

        Args:
            messages: List of message dicts

        Returns:
            Formatted string
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]  # Truncate long messages
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def estimate_tokens(self, messages: List[Dict]) -> int:
        """
        Estimate token count for messages.

        Uses simple heuristic: 1 token ≈ 4 characters

        Args:
            messages: List of message dicts

        Returns:
            Estimated token count
        """
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return total_chars // 4

    def truncate_if_needed(self, messages: List[Dict]) -> List[Dict]:
        """
        Truncate messages if over token limit.

        Removes oldest messages first to stay under limit.

        Args:
            messages: List of message dicts

        Returns:
            Truncated message list
        """
        if self.estimate_tokens(messages) <= self.max_tokens:
            return messages

        result = messages.copy()

        # Remove oldest messages until under limit
        while result and self.estimate_tokens(result) > self.max_tokens:
            # Remove first two messages (one turn)
            if len(result) >= 2:
                result = result[2:]
            else:
                result = []

        return result

    def prepare_for_llm(
        self,
        history: List[Dict],
        max_tokens: Optional[int] = None
    ) -> List[Dict]:
        """
        Prepare history for LLM call (compress + truncate).

        Args:
            history: Raw conversation history
            max_tokens: Optional token limit override

        Returns:
            Prepared history ready for LLM
        """
        # First compress if needed
        compressed = self.compress_history(history)

        # Then truncate if over token limit
        limit = max_tokens or self.max_tokens
        if self.estimate_tokens(compressed) > limit:
            manager = ConversationManager(max_tokens=limit)
            return manager.truncate_if_needed(compressed)

        return compressed


# Global instance for convenience
conversation_manager = ConversationManager()
```

**Step 4: Run test to verify it passes**

Run: `cd backend-fastapi && python -m pytest tests/test_conversation_manager.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend-fastapi/app/services/conversation_manager.py backend-fastapi/tests/test_conversation_manager.py
git commit -m "feat: add conversation manager for history compression"
```

---

## Task 8: Integrate Conversation Manager into Agent (P1)

**Depends on:** Task 7

**Files:**
- Modify: `backend-fastapi/app/api/agent.py`

**Step 1: Add import and usage**

Modify `backend-fastapi/app/api/agent.py`:

Add import at top (around line 15):
```python
from app.services.conversation_manager import conversation_manager
```

**Step 2: Update agent_chat endpoint**

Modify the `agent_chat` function (around line 409-540) to use conversation manager:

```python
@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with Agent - supports multi-turn conversation with history compression
    """
    import re
    from app.services.code_tools import (
        analyze_code_structure,
        detect_code_smells,
        check_security_issues,
        search_code_semantic,
    )

    try:
        # Build and compress conversation history
        conversation = []
        for msg in request.history:
            conversation.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Compress and truncate history to control tokens
        compressed_history = conversation_manager.prepare_for_llm(
            conversation,
            max_tokens=3000  # Leave room for response
        )

        # ... rest of the existing code ...
```

**Step 3: Test the integration**

Run: `cd backend-fastapi && python -m pytest tests/test_agent_parallel.py -v`
Expected: PASS (existing tests should still pass)

**Step 4: Commit**

```bash
git add backend-fastapi/app/api/agent.py
git commit -m "perf: integrate conversation manager for token control"
```

---

## Task 9: Performance Benchmarking

**Files:**
- Create: `backend-fastapi/tests/test_performance_benchmark.py`

**Step 1: Create benchmark test**

Create `backend-fastapi/tests/test_performance_benchmark.py`:

```python
"""
Performance benchmark tests

Run with: pytest tests/test_performance_benchmark.py -v --benchmark-only
"""
import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


class TestPerformanceBenchmarks:
    """Benchmark tests for performance optimization verification"""

    @pytest.mark.asyncio
    async def test_tool_analysis_parallel_performance(self, benchmark):
        """Benchmark parallel tool analysis"""
        from app.api.agent import run_tool_analysis

        code = """
def calculate_sum(numbers):
    total = 0
    for n in numbers:
        total += n
    return total
"""

        async def run_analysis():
            return await run_tool_analysis(code, "python")

        # Warmup
        await run_analysis()

        # Benchmark
        result = await benchmark(run_analysis)

        # Verify all tools returned results
        assert "analyze_code_structure" in result
        assert "detect_code_smells" in result

    @pytest.mark.asyncio
    async def test_retriever_parallel_performance(self, benchmark):
        """Benchmark parallel GraphRAG retrieval"""
        from app.services.code_graph.retriever import CodeGraphRetriever

        retriever = CodeGraphRetriever()
        retriever._chromadb = MagicMock()
        retriever._neo4j = MagicMock()

        retriever._chromadb.search_all = MagicMock(return_value={
            "functions": [{"id": "1", "document": "test", "metadata": {}}],
            "classes": []
        })

        async def run_retrieve():
            with patch.object(retriever, '_get_neo4j', AsyncMock(return_value=retriever._neo4j)):
                with patch.object(retriever._neo4j, 'batch_get_entity_context', AsyncMock(return_value=[])):
                    return await retriever.retrieve("test query", project_id=1)

        # Warmup
        await run_retrieve()

        # Benchmark
        result = await benchmark(run_retrieve)

        assert result["query"] == "test query"

    def test_conversation_compression_performance(self, benchmark):
        """Benchmark conversation compression"""
        from app.services.conversation_manager import ConversationManager

        manager = ConversationManager()

        # Create large history
        history = []
        for i in range(50):
            history.append({"role": "user", "content": f"Question {i}" * 20})
            history.append({"role": "assistant", "content": f"Answer {i}" * 50})

        def run_compress():
            return manager.compress_history(history)

        result = benchmark(run_compress)

        # Should be compressed to max_turns
        assert len(result) <= 20


class TestLatencyRequirements:
    """Verify latency requirements are met"""

    @pytest.mark.asyncio
    async def test_tool_analysis_latency_under_1_5s(self):
        """Tool analysis should complete under 1.5s"""
        from app.api.agent import run_tool_analysis

        code = "def test():\n    pass"

        start = time.time()
        await run_tool_analysis(code, "python")
        elapsed = time.time() - start

        assert elapsed < 1.5, f"Tool analysis took {elapsed:.2f}s, expected < 1.5s"

    def test_conversation_compression_latency_under_100ms(self):
        """Compression should be fast"""
        from app.services.conversation_manager import ConversationManager

        manager = ConversationManager()
        history = [{"role": "user", "content": f"Message {i}"} for i in range(100)]

        start = time.time()
        manager.compress_history(history)
        elapsed = time.time() - start

        assert elapsed < 0.1, f"Compression took {elapsed:.3f}s, expected < 0.1s"
```

**Step 2: Run benchmarks**

Run: `cd backend-fastapi && python -m pytest tests/test_performance_benchmark.py -v`
Expected: All latency tests should PASS

**Step 3: Commit**

```bash
git add backend-fastapi/tests/test_performance_benchmark.py
git commit -m "test: add performance benchmark tests"
```

---

## Execution Summary

### Parallel Execution Groups

**Group A (Backend P0) - Can run in parallel:**
- Task 1: Parallel Tool Invocation
- Task 2: Streaming Response Backend

**Group B (Frontend P0) - Depends on Group A:**
- Task 3: Frontend Streaming Hook
- Task 4: AgentChatPage Integration

**Group C (Backend P1) - Can run in parallel with Group A:**
- Task 5: Batch Neo4j Query
- Task 6: Parallel Retriever
- Task 7: Conversation Manager

**Group D (Integration) - Depends on Group C:**
- Task 8: Agent Integration
- Task 9: Performance Benchmarks

### Suggested Parallel Execution

```
┌─────────────────────────────────────────────────────────────┐
│                    Parallel Execution                        │
├─────────────────────────────────────────────────────────────┤
│  Group A (P0 Backend)    │    Group C (P1 Backend)          │
│  ├─ Task 1               │    ├─ Task 5                     │
│  └─ Task 2               │    ├─ Task 6                     │
│                          │    └─ Task 7                     │
├─────────────────────────────────────────────────────────────┤
│  Group B (P0 Frontend)   │    Group D (Integration)         │
│  ├─ Task 3               │    ├─ Task 8                     │
│  └─ Task 4               │    └─ Task 9                     │
└─────────────────────────────────────────────────────────────┘
```

### Verification Commands

After all tasks:
```bash
# Run all tests
cd backend-fastapi && python -m pytest tests/ -v

# Run frontend tests
cd frontend && npm test

# Manual verification
# 1. Start backend: cd backend-fastapi && uvicorn app.main:app --reload
# 2. Start frontend: cd frontend && npm run dev
# 3. Test streaming in AgentChatPage
# 4. Verify conversation history is compressed
```
