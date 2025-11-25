"""Simplified wrapper that uses the existing RAG agent."""

from collections import defaultdict
from typing import AsyncGenerator, Optional

from packages.core.agent import (
    agent as rag_agent_instance,
)
from packages.core.agent import (
    get_last_sources,
    initialize_db,
)

# Session-based message history storage
# In production, use Redis or database
_message_histories: dict = defaultdict(list)


def get_message_history(session_id: str) -> list:
    """Get message history for a session."""
    return _message_histories.get(session_id, [])


def update_message_history(session_id: str, messages: list):
    """Update message history for a session."""
    _message_histories[session_id] = messages


async def stream_agent_response(
    message: str, session_id: Optional[str] = None
) -> AsyncGenerator[dict, None]:
    """
    Stream agent responses using the existing RAG agent.

    Args:
        message: User's message/query
        session_id: Optional session ID for conversation history

    Yields:
        dict: Event data with type and content
    """
    try:
        # Ensure database is initialized
        await initialize_db()

        # Get existing message history for this session
        message_history = []
        if session_id:
            message_history = get_message_history(session_id)

        # Run agent with streaming and message history
        async with rag_agent_instance.run_stream(
            message, message_history=message_history
        ) as result:
            # Stream tokens as they arrive
            async for text in result.stream_text(delta=True):
                yield {"type": "token", "content": text}

            # Update message history with the new messages
            if session_id:
                update_message_history(session_id, result.all_messages())

        # Get sources after streaming completes
        sources = get_last_sources()
        if sources:
            yield {"type": "sources", "content": "", "sources": sources}

        # Send completion event
        yield {"type": "done", "content": ""}

    except Exception as e:
        # Send error event
        yield {"type": "error", "content": str(e)}
