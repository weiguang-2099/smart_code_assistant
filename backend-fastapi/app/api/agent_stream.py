"""
Streaming Agent API Routes - SSE streaming endpoints

Provides Server-Sent Events streaming for real-time AI responses
with comprehensive error handling, monitoring, and reconnection support.
"""
import asyncio
import json
import re
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.core.cache import global_cache_manager
from app.models.user import User
from app.services.langchain_glm_service import langchain_glm_service
from app.schemas.agent import StreamChatRequest

logger = logging.getLogger(__name__)
router = APIRouter()


class StreamEventType(str, Enum):
    """SSE event types."""
    CONTENT = "content"
    ERROR = "error"
    DONE = "done"
    HEARTBEAT = "heartbeat"
    METADATA = "metadata"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"


@dataclass
class StreamMetrics:
    """Metrics for streaming session."""
    session_id: str
    user_id: int
    start_time: float = field(default_factory=time.time)
    chunks_sent: int = 0
    total_tokens: int = 0
    errors: int = 0
    last_chunk_time: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "duration_ms": round((time.time() - self.start_time) * 1000, 2),
            "chunks_sent": self.chunks_sent,
            "total_tokens": self.total_tokens,
            "errors": self.errors,
        }


active_streams: Dict[str, StreamMetrics] = {}


def format_sse_event(
    event_type: StreamEventType,
    data: Any,
    event_id: Optional[str] = None,
    retry: Optional[int] = None,
) -> str:
    """
    Format a Server-Sent Event.

    Args:
        event_type: Type of event
        data: Event data (will be JSON encoded)
        event_id: Optional event ID for reconnection
        retry: Retry delay in milliseconds

    Returns:
        Formatted SSE string
    """
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type.value}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    if retry:
        lines.append(f"retry: {retry}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


async def generate_stream_with_heartbeat(
    generator: AsyncGenerator[str, None],
    metrics: StreamMetrics,
    heartbeat_interval: float = 15.0,
) -> AsyncGenerator[str, None]:
    """
    Wrap a generator with heartbeat events to keep connection alive.

    Args:
        generator: The base generator
        metrics: Stream metrics tracker
        heartbeat_interval: Seconds between heartbeats

    Yields:
        SSE formatted strings
    """
    event_counter = 0
    last_heartbeat = time.time()

    try:
        async for chunk in generator:
            event_counter += 1
            event_id = f"{metrics.session_id}-{event_counter}"

            yield format_sse_event(
                StreamEventType.CONTENT,
                {"content": chunk},
                event_id=event_id,
            )

            metrics.chunks_sent += 1
            metrics.last_chunk_time = time.time()

            if time.time() - last_heartbeat > heartbeat_interval:
                yield format_sse_event(
                    StreamEventType.HEARTBEAT,
                    {"timestamp": datetime.utcnow().isoformat()},
                )
                last_heartbeat = time.time()

    except asyncio.CancelledError:
        logger.info(f"Stream {metrics.session_id} cancelled by client")
        yield format_sse_event(
            StreamEventType.ERROR,
            {"error": "Stream cancelled", "recoverable": True},
        )
        raise
    except Exception as e:
        logger.error(f"Stream {metrics.session_id} error: {e}")
        metrics.errors += 1
        yield format_sse_event(
            StreamEventType.ERROR,
            {"error": str(e), "recoverable": False},
        )
        raise


async def stream_chat_response(
    request: StreamChatRequest,
    metrics: StreamMetrics,
) -> AsyncGenerator[str, None]:
    """
    Generate streaming chat response.

    Args:
        request: Chat request
        metrics: Stream metrics

    Yields:
        Content chunks
    """
    system_prompt = f"""你是一个专业的编程助手，精通 {request.language} 语言。
提供清晰、准确的答案。
显示代码时使用 markdown 代码块。"""

    code_blocks = _extract_code_blocks(request.message)

    enhanced_message = request.message
    if code_blocks:
        enhanced_message += f"\n\n[检测到代码块: {len(code_blocks)} 个]"

    yield format_sse_event(
        StreamEventType.METADATA,
        {
            "session_id": metrics.session_id,
            "code_blocks_detected": len(code_blocks),
            "language": request.language,
        },
    )

    try:
        async for chunk in langchain_glm_service.stream_chat(
            system_prompt=system_prompt,
            user_prompt=enhanced_message,
        ):
            yield chunk
            metrics.total_tokens += 1

    except Exception as e:
        logger.error(f"LLM stream error: {e}")
        raise


@router.post("/chat/stream")
async def agent_chat_stream(
    request: StreamChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream agent chat response using Server-Sent Events.

    Features:
    - Real-time content streaming
    - Heartbeat events for connection keep-alive
    - Event IDs for reconnection support
    - Comprehensive error handling
    - Stream metrics and monitoring

    SSE Event Types:
    - content: Content chunk
    - error: Error message
    - done: Stream complete
    - heartbeat: Connection keep-alive
    - metadata: Stream metadata

    Headers:
    - Last-Event-ID: Resume from last received event
    """
    session_id = str(uuid.uuid4())[:8]

    metrics = StreamMetrics(
        session_id=session_id,
        user_id=current_user.id,
    )
    active_streams[session_id] = metrics

    last_event_id = http_request.headers.get("Last-Event-ID")
    if last_event_id:
        logger.info(f"Client reconnecting with Last-Event-ID: {last_event_id}")

    async def generate():
        try:
            async for event in generate_stream_with_heartbeat(
                stream_chat_response(request, metrics),
                metrics,
            ):
                if await http_request.is_disconnected():
                    logger.info(f"Client disconnected for stream {session_id}")
                    break
                yield event

            yield format_sse_event(StreamEventType.DONE, {"session_id": session_id})

        except asyncio.CancelledError:
            logger.info(f"Stream {session_id} was cancelled")
            yield format_sse_event(
                StreamEventType.ERROR,
                {"error": "Stream cancelled", "session_id": session_id},
            )
        except Exception as e:
            logger.error(f"Stream {session_id} failed: {e}")
            yield format_sse_event(
                StreamEventType.ERROR,
                {"error": str(e), "session_id": session_id},
            )
        finally:
            duration = time.time() - metrics.start_time
            logger.info(
                f"Stream {session_id} completed: "
                f"{metrics.chunks_sent} chunks, "
                f"{metrics.total_tokens} tokens, "
                f"{duration:.2f}s"
            )
            active_streams.pop(session_id, None)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Stream-Id": session_id,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, Last-Event-ID",
        },
    )


@router.get("/stream/stats")
async def get_stream_stats(
    current_user: User = Depends(get_current_user),
):
    """Get active stream statistics."""
    return {
        "active_streams": len(active_streams),
        "streams": [
            metrics.to_dict()
            for metrics in active_streams.values()
        ],
    }


@router.delete("/stream/{session_id}")
async def cancel_stream(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel an active stream."""
    if session_id in active_streams:
        metrics = active_streams[session_id]
        if metrics.user_id == current_user.id:
            active_streams.pop(session_id, None)
            return {"message": f"Stream {session_id} cancelled"}
        return {"error": "Unauthorized"}
    return {"error": f"Stream {session_id} not found"}


def _extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """Extract code blocks from text."""
    pattern = r'```(\w*)\n([\s\S]*?)```'
    blocks = []
    for match in re.finditer(pattern, text):
        blocks.append({
            "language": match.group(1) or "text",
            "code": match.group(2)
        })
    return blocks
