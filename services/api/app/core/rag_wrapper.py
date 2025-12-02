"""Simplified wrapper that uses the existing RAG agent."""

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from packages.config import settings
from packages.core.agent import (
    create_rag_context,
    get_last_sources,
)
from packages.core.factory import create_rag_agent

logger = logging.getLogger(__name__)


def extract_cited_indices(response_text: str) -> set[int]:
    """Extract source indices like [1], [2], [3] from response text.

    Uses negative lookbehind/lookahead to avoid false positives from:
    - Markdown links: [text](url)
    - Nested brackets: [[1]]
    - Other bracketed contexts

    Args:
        response_text: The complete agent response text

    Returns:
        Set of 1-based indices that were cited in the response
    """
    matches = re.findall(r"(?<!\w)\[(\d+)\](?!\()", response_text)
    indices = {int(m) for m in matches}
    if indices:
        logger.info(f"Extracted cited source indices: {sorted(indices)}")
    return indices


# Session-based message history storage
# In-memory session storage with TTL cleanup (KISS approach)
# For multi-server deployments, migrate to Redis or database
_message_histories: dict = defaultdict(list)
_session_timestamps: dict[str, datetime] = {}
SESSION_TTL_HOURS = 1  # Clean up inactive sessions after 1 hour


async def _cleanup_old_sessions():
    """Remove sessions inactive for > TTL hours.

    Prevents unbounded memory growth by automatically cleaning up
    sessions that haven't been accessed within the TTL window.
    Called on every session update for passive cleanup.
    """
    cutoff = datetime.now() - timedelta(hours=SESSION_TTL_HOURS)
    expired = [sid for sid, ts in _session_timestamps.items() if ts < cutoff]

    if expired:
        logger.info(f"🧹 Cleaning up {len(expired)} expired sessions (TTL: {SESSION_TTL_HOURS}h)")
        for sid in expired:
            _message_histories.pop(sid, None)
            _session_timestamps.pop(sid, None)


def get_message_history(session_id: str) -> list:
    """Get message history for a session."""
    return _message_histories.get(session_id, [])


async def update_message_history(session_id: str, messages: list):
    """Update message history and refresh session timestamp.

    Also triggers cleanup of expired sessions on every update (passive cleanup).
    This prevents unbounded memory growth in long-running deployments.
    """
    await _cleanup_old_sessions()  # Cleanup on every access (passive)
    _message_histories[session_id] = messages
    _session_timestamps[session_id] = datetime.now()


async def stream_agent_response(
    message: str, session_id: Optional[str] = None
) -> AsyncGenerator[dict, None]:
    """
    Stream agent responses using the RAG agent with dependency injection.

    Creates a new RAG context with all dependencies, then creates an agent instance
    with proper typing for tools to access context via RunContext[RAGContext].

    Args:
        message: User's message/query
        session_id: Optional session ID for conversation history

    Yields:
        dict: Event data with type and content
    """
    try:
        # Create RAG context with all dependencies (db_client, embedder)
        rag_context = await create_rag_context()

        logger.info("RAG context initialized with dependency injection")

        # Create agent using factory - Uses settings.llm.model from .env
        # Default LLM_MODEL=gpt-4.1-mini (NOT hardcoded "openai:gpt-4o")
        # Tools are configurable via ENABLED_TOOLS environment variable (default: all tools)
        rag_agent = create_rag_agent()

        logger.info(f"Agent created with model: {settings.llm.model}")

        # Get existing message history for this session
        message_history = []
        if session_id:
            message_history = get_message_history(session_id)

        logger.info(f"🚀 Starting agent run for message: {message[:100]}...")
        logger.info(f"📝 Message history length: {len(message_history)}")

        # Run agent with streaming and message history
        async with rag_agent.run_stream(
            message, message_history=message_history, deps=rag_context
        ) as result:
            # Stream tokens as they arrive
            async for text in result.stream_text(delta=True):
                yield {"type": "token", "content": text}

            # Update message history with the new messages
            if session_id:
                await update_message_history(session_id, result.all_messages())

            # Check message kinds to detect tool calling
            all_messages = result.all_messages()
            logger.info(f"💬 Total messages in conversation: {len(all_messages)}")

            # DEBUG: Log all message kinds
            for i, msg in enumerate(all_messages):
                msg_kind = getattr(msg, "kind", "NO_KIND_ATTR")
                msg_type = type(msg).__name__
                logger.info(f"  Message {i}: type={msg_type}, kind={msg_kind}")

            tool_calls = [
                msg
                for msg in all_messages
                if hasattr(msg, "kind") and msg.kind == "request-tool-call"
            ]
            tool_responses = [
                msg
                for msg in all_messages
                if hasattr(msg, "kind") and msg.kind == "response-tool-return"
            ]

            logger.info(f"🔧 Tool calls detected: {len(tool_calls)}")
            logger.info(f"📥 Tool responses received: {len(tool_responses)}")

            # Emit tool_call events with metadata
            if tool_calls and tool_responses:
                for tool_call, tool_response in zip(tool_calls, tool_responses):
                    tool_name = getattr(tool_call, "tool_name", "unknown")

                    # Extract tool arguments from the tool call message
                    tool_args = {}
                    if hasattr(tool_call, "args") and tool_call.args:
                        # args is a ModelDump or dict containing the function arguments
                        if hasattr(tool_call.args, "model_dump"):
                            tool_args = tool_call.args.model_dump()
                        elif isinstance(tool_call.args, dict):
                            tool_args = tool_call.args

                    logger.info(f"  ↳ Tool called: {tool_name} with args: {tool_args}")

                    # Estimate execution time (use reasonable default)
                    execution_time_ms = 150

                    # Emit tool_call event with metadata
                    yield {
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "execution_time_ms": execution_time_ms,
                    }

            # Extract cited source indices from complete response
            final_text = await result.get_output()  # Get complete response text
            cited_indices = extract_cited_indices(final_text)
            rag_context.cited_source_indices = cited_indices

        # Get sources after streaming completes (pass context for dependency injection)
        sources = get_last_sources(rag_context)
        logger.info(f"📚 Sources retrieved: {len(sources) if sources else 0}")

        if sources:
            # Sort sources by similarity descending (defensive, should already be sorted)
            sorted_sources = sorted(sources, key=lambda s: s["similarity"], reverse=True)

            logger.info(
                f"✅ Returning {len(sorted_sources)} sources with {len(cited_indices)} cited indices to client"
            )
            yield {
                "type": "sources",
                "content": "",
                "sources": sorted_sources,
                "cited_indices": list(cited_indices),  # Convert set to list for JSON
            }
        else:
            logger.warning("⚠️ No sources retrieved - tool may not have been called")

        # Send completion event
        yield {"type": "done", "content": ""}

    except Exception as e:
        # Send error event
        yield {"type": "error", "content": str(e)}
