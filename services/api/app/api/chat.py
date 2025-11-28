"""Chat API endpoints for streaming responses."""

import json
from typing import AsyncGenerator, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.rag_wrapper import stream_agent_response

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str
    session_id: Optional[str] = None


async def event_stream(message: str, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events stream from agent responses.

    Args:
        message: User's message
        session_id: Optional session ID for conversation history

    Yields:
        Formatted SSE events
    """
    async for event in stream_agent_response(message, session_id):
        # Format as SSE
        event_type = event["type"]

        if event_type == "sources":
            # Send sources as JSON with the sources array
            data = {"content": "", "sources": event.get("sources", [])}
            yield f"event: {event_type}\n"
            yield f"data: {json.dumps(data)}\n\n"
        elif event_type == "tool_call":
            # Send tool call metadata
            data = {
                "tool_name": event.get("tool_name", ""),
                "tool_args": event.get("tool_args", {}),
                "execution_time_ms": event.get("execution_time_ms", 0),
            }
            yield f"event: {event_type}\n"
            yield f"data: {json.dumps(data)}\n\n"
        else:
            # Normal events (token, done, error)
            content = event.get("content", "")
            yield f"event: {event_type}\n"
            yield f"data: {json.dumps({'content': content})}\n\n"


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat responses using Server-Sent Events.

    Args:
        request: Chat request with message and optional session_id

    Returns:
        StreamingResponse with SSE events
    """
    return StreamingResponse(
        event_stream(request.message, request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "chat"}
