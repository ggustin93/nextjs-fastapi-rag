"""Simplified wrapper that uses singleton RAG agent from application state.

This module provides the streaming interface for RAG responses, using
shared resources managed by FastAPI's lifespan to prevent connection
pool exhaustion.

Architecture:
- Singleton agent: Reused across all requests (stateless)
- Agent switcher: Manages multiple agents with @mention support (e.g., @weather, @rag)
- Singleton db_client: Shared connection pool
- Singleton embedder: Shared OpenAI client
- Per-request RAGContext: Wraps singletons with request-specific mutable state
"""

import asyncio
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from packages.config import settings
from packages.core.agent import get_last_sources
from packages.core.factory import create_rag_agent

# Timeout for agent streaming (prevents indefinite hangs)
STREAM_TIMEOUT_SECONDS = 60

logger = logging.getLogger(__name__)


def _get_app_state():
    """Get singleton app state (lazy import to avoid circular imports)."""
    from app.main import app_state

    return app_state


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
_session_models: dict[str, str] = {}  # Track model per session to detect switches
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
            _session_models.pop(sid, None)


def get_message_history(session_id: str, model: str | None = None) -> list:
    """Get message history for a session (excludes system prompt).

    If model differs from session's previous model, returns empty history
    to avoid tool_call_id format incompatibilities between providers.
    """
    if model and session_id in _session_models:
        previous_model = _session_models[session_id]
        if previous_model != model:
            logger.info(f"🔄 Model switch detected ({previous_model} → {model}), clearing history")
            _message_histories.pop(session_id, None)
            return []
    return _message_histories.get(session_id, [])


async def update_message_history_with_model(
    session_id: str, messages: list, model: str | None = None
):
    """Update message history with new messages and track the model used.

    Stores only user/assistant messages for conversation continuity.
    The agent adds its own system prompt on each run.
    Also tracks the model used to detect model switches.
    """
    await _cleanup_old_sessions()

    # Track the model used for this session
    if model:
        _session_models[session_id] = model

    # Filter out system prompt messages - agent adds its own
    from pydantic_ai.messages import ModelRequest, SystemPromptPart

    filtered = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            # Remove SystemPromptPart from requests, keep user parts
            non_system_parts = [p for p in msg.parts if not isinstance(p, SystemPromptPart)]
            if non_system_parts:
                filtered.append(ModelRequest(parts=non_system_parts))
        else:
            filtered.append(msg)

    _message_histories[session_id] = filtered
    _session_timestamps[session_id] = datetime.now()


async def stream_agent_response(
    message: str, session_id: Optional[str] = None, model: Optional[str] = None
) -> AsyncGenerator[dict, None]:
    """
    Stream agent responses using the RAG agent with dependency injection.

    Creates a new RAG context with all dependencies, then creates an agent instance
    with proper typing for tools to access context via RunContext[RAGContext].

    Args:
        message: User's message/query
        session_id: Optional session ID for conversation history
        model: Optional LLM model override (creates new agent if different from default)

    Yields:
        dict: Event data with type and content
    """
    try:
        # Get singleton app state (shared agent, db_client, embedder)
        app_state = _get_app_state()

        # Create per-request RAGContext using shared singleton resources
        # The context wraps shared resources but has per-request mutable state
        rag_context = app_state.create_rag_context()

        logger.info("RAG context initialized with shared singleton resources")

        # Parse @agent mention and get appropriate agent
        # Example: "@weather Météo Paris?" → agent_id="weather", clean_message="Météo Paris?"
        agent_id = None
        clean_message = message
        if app_state.agent_switcher:
            agent_id, clean_message = app_state.agent_switcher.parse_agent_mention(message)
            if agent_id:
                logger.info(f"🔀 Agent switch detected: @{agent_id}")

        # Use singleton agent or create new agent with model/agent override
        effective_model = model if model else settings.llm.model
        if agent_id and app_state.agent_switcher:
            # Use agent from switcher (cached or creates new)
            rag_agent = app_state.agent_switcher.switch_to(agent_id)
            logger.info(f"🤖 Using agent: {agent_id}")
        elif model and model != settings.llm.model:
            logger.info(f"Using model override: {model}")
            rag_agent = create_rag_agent(model=model)
        else:
            rag_agent = app_state.agent

        # Get existing message history for this session
        # Pass model to detect model switches and clear incompatible history
        message_history = []
        if session_id:
            message_history = get_message_history(session_id, model=effective_model)

        agent_label = f"@{agent_id}" if agent_id else "default"
        logger.info(
            f"🚀 Agent run ({agent_label}): '{clean_message[:50]}...' (history: {len(message_history)} msgs)"
        )

        # Run agent with streaming and message history
        # Use clean_message (without @agent prefix) for the actual query
        async with asyncio.timeout(STREAM_TIMEOUT_SECONDS):
            async with rag_agent.run_stream(
                clean_message, message_history=message_history, deps=rag_context
            ) as result:
                # Stream tokens as they arrive
                async for text in result.stream_text(delta=True):
                    yield {"type": "token", "content": text}

                # Update message history with the new messages and track model
                if session_id:
                    await update_message_history_with_model(
                        session_id, result.all_messages(), model=effective_model
                    )

                # Extract tool calls and their results from pydantic-ai messages
                from pydantic_ai.messages import (
                    ModelRequest,
                    ModelResponse,
                    ToolCallPart,
                    ToolReturnPart,
                )

                all_messages = result.all_messages()

                # Collect tool calls with their results
                tool_calls_with_results: list[dict] = []
                tool_results_by_id: dict[str, str] = {}

                # First pass: collect all tool results by tool_call_id
                for msg in all_messages:
                    if isinstance(msg, ModelRequest):
                        for part in msg.parts:
                            if isinstance(part, ToolReturnPart):
                                tool_results_by_id[part.tool_call_id] = part.content

                # Second pass: collect tool calls and match with results
                for msg in all_messages:
                    if isinstance(msg, ModelResponse):
                        for part in msg.parts:
                            if isinstance(part, ToolCallPart):
                                tool_result = tool_results_by_id.get(part.tool_call_id)
                                tool_calls_with_results.append(
                                    {
                                        "part": part,
                                        "result": tool_result,
                                    }
                                )

                if tool_calls_with_results:
                    logger.info(f"🔧 Found {len(tool_calls_with_results)} tool call(s)")

                for tool_data in tool_calls_with_results:
                    try:
                        tool_part = tool_data["part"]
                        tool_result = tool_data["result"]
                        tool_name = tool_part.tool_name
                        tool_args = tool_part.args_as_dict() if tool_part.args else {}

                        logger.info(f"🔧 Emitting tool_call: {tool_name} with args: {tool_args}")
                        yield {
                            "type": "tool_call",
                            "tool_name": tool_name,
                            "tool_args": tool_args,
                            "tool_result": tool_result,  # Include the result for debug display
                            "execution_time_ms": 150,
                        }
                    except Exception as tool_err:
                        logger.error(f"Tool event error: {tool_err}")

                # Extract cited source indices from complete response
                final_text = await result.get_output()
                cited_indices = extract_cited_indices(final_text)
                rag_context.cited_source_indices = cited_indices

        # Get sources after streaming completes
        sources = get_last_sources(rag_context)

        if sources:
            sorted_sources = sorted(sources, key=lambda s: s["similarity"], reverse=True)
            logger.info(f"📚 Returning {len(sorted_sources)} sources")
            yield {
                "type": "sources",
                "content": "",
                "sources": sorted_sources,
                "cited_indices": list(cited_indices),
            }
        else:
            logger.warning("⚠️ No sources retrieved - tool may not have been called")

        # Send completion event
        yield {"type": "done", "content": ""}

    except Exception as e:
        # Bug 6 fix: Log exceptions for debugging (was silent before)
        logger.error(f"❌ Stream error: {e}", exc_info=True)
        # Send error event to frontend
        yield {"type": "error", "content": str(e)}
