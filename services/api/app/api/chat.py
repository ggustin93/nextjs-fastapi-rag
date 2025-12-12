"""Chat API endpoints for streaming responses."""

import json
import logging
import re
from typing import AsyncGenerator, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.core.rag_wrapper import stream_agent_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Constants
MAX_MESSAGE_LENGTH = 10000
MAX_SESSION_ID_LENGTH = 100
MAX_MODEL_LENGTH = 50


class ChatRequest(BaseModel):
    """Request model for chat endpoint with validation."""

    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    session_id: Optional[str] = Field(None, max_length=MAX_SESSION_ID_LENGTH)
    model: Optional[str] = Field(None, max_length=MAX_MODEL_LENGTH)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate and sanitize message content."""
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        # Basic XSS prevention (script tags)
        if re.search(r"<script", v, re.IGNORECASE):
            raise ValueError("Invalid message content")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID format."""
        if v is None:
            return v
        # Allow alphanumeric, underscore, hyphen only
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Invalid session ID format")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        """Validate model name format."""
        if v is None:
            return v
        # Allow alphanumeric, underscore, hyphen, slash, colon, dot
        if not re.match(r"^[a-zA-Z0-9_\-/:.]+$", v):
            raise ValueError("Invalid model name format")
        return v


async def event_stream(
    message: str, session_id: Optional[str] = None, model: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events stream from agent responses.

    Args:
        message: User's message
        session_id: Optional session ID for conversation history
        model: Optional LLM model override

    Yields:
        Formatted SSE events
    """
    async for event in stream_agent_response(message, session_id, model):
        # Format as SSE
        event_type = event["type"]

        if event_type == "sources":
            # Send sources as JSON with the sources array and cited indices
            data = {
                "content": "",
                "sources": event.get("sources", []),
                "cited_indices": event.get("cited_indices", []),
            }
            yield f"event: {event_type}\n"
            yield f"data: {json.dumps(data)}\n\n"
        elif event_type == "tool_call":
            # Send tool call metadata with optional result for debug
            data = {
                "tool_name": event.get("tool_name", ""),
                "tool_args": event.get("tool_args", {}),
                "execution_time_ms": event.get("execution_time_ms", 0),
                "tool_result": event.get("tool_result"),  # Include result for debug display
            }
            try:
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(data)}\n\n"
            except (TypeError, ValueError) as e:
                # Fallback with minimal safe data if serialization fails
                logger.warning(f"Failed to serialize tool_call event: {e}")
                safe_data = {
                    "tool_name": str(data.get("tool_name", "")),
                    "tool_args": {},
                    "execution_time_ms": 0,
                    "tool_result": None,
                }
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(safe_data)}\n\n"
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
        request: Chat request with message, optional session_id, and optional model

    Returns:
        StreamingResponse with SSE events
    """
    return StreamingResponse(
        event_stream(request.message, request.session_id, request.model),
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
