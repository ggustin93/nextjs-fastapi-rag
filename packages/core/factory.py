"""Agent factory for consistent RAG agent creation."""

from pydantic_ai import Agent

from packages.config import settings
from packages.core.tools import get_tools
from packages.core.types import RAGContext


def create_rag_agent(
    system_prompt: str | None = None,
    enabled_tools: list[str] | None = None,
    deps_type=RAGContext,
) -> Agent:
    """Create RAG agent with consistent configuration.

    Args:
        system_prompt: Override default system prompt
        enabled_tools: List of tool names to enable.
                      None = all tools, [] = search only
        deps_type: Dependency type (RAGContext or None)

    Returns:
        Configured Agent instance

    Examples:
        >>> # Default agent (all tools)
        >>> agent = create_rag_agent()

        >>> # CLI agent (search only)
        >>> agent = create_rag_agent(
        ...     system_prompt=RAG_SYSTEM_PROMPT,
        ...     enabled_tools=[]
        ... )

        >>> # API agent (configurable)
        >>> agent = create_rag_agent(
        ...     enabled_tools=settings.enabled_tools
        ... )
    """
    tools = get_tools(enabled_tools if enabled_tools is not None else settings.enabled_tools)
    prompt = system_prompt or settings.llm.system_prompt

    return Agent(
        settings.llm.create_model(),
        deps_type=deps_type,
        system_prompt=prompt,
        tools=tools,
    )
