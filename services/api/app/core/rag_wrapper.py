"""Simplified wrapper that uses the existing RAG agent."""

import logging
from collections import defaultdict
from typing import AsyncGenerator, Optional

from pydantic_ai import Agent

from packages.config import settings
from packages.core.agent import (
    RAGContext,
    create_rag_context,
    get_last_sources,
    search_knowledge_base,
)
from packages.core.config import DomainConfig, QueryExpansionConfig

logger = logging.getLogger(__name__)

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
        # Create RAG context with all dependencies (db_client, reranker, domain_config)
        # For domain-specific behavior, pass DomainConfig(query_expansion=QueryExpansionConfig())
        # For generic RAG, pass None for domain_config
        rag_context = await create_rag_context(
            domain_config=DomainConfig(query_expansion=QueryExpansionConfig())
        )

        logger.info("RAG context initialized with dependency injection")

        # Create agent with context - CRITICAL: Use settings.llm.model from .env
        # Default LLM_MODEL=gpt-4.1-mini (NOT hardcoded "openai:gpt-4o")
        rag_agent = Agent(
            settings.llm.create_model(),  # Uses settings.llm.model from .env
            deps_type=RAGContext,
            system_prompt=settings.llm.system_prompt,
            tools=[search_knowledge_base],
        )

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
                update_message_history(session_id, result.all_messages())

            # Check message kinds to detect tool calling
            all_messages = result.all_messages()
            logger.info(f"💬 Total messages in conversation: {len(all_messages)}")

            tool_calls = [msg for msg in all_messages if hasattr(msg, 'kind') and msg.kind == 'request-tool-call']
            tool_responses = [msg for msg in all_messages if hasattr(msg, 'kind') and msg.kind == 'response-tool-return']

            logger.info(f"🔧 Tool calls detected: {len(tool_calls)}")
            logger.info(f"📥 Tool responses received: {len(tool_responses)}")

            if tool_calls:
                for tool_call in tool_calls:
                    tool_name = getattr(tool_call, 'tool_name', 'unknown')
                    logger.info(f"  ↳ Tool called: {tool_name}")

        # Get sources after streaming completes (pass context for dependency injection)
        sources = get_last_sources(rag_context)
        logger.info(f"📚 Sources retrieved: {len(sources) if sources else 0}")

        if sources:
            logger.info(f"✅ Returning {len(sources)} sources to client")
            yield {"type": "sources", "content": "", "sources": sources}
        else:
            logger.warning("⚠️ No sources retrieved - tool may not have been called")

        # Send completion event
        yield {"type": "done", "content": ""}

    except Exception as e:
        # Send error event
        yield {"type": "error", "content": str(e)}
