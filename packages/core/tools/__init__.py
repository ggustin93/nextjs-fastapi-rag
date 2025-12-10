"""Tool registry for RAG agent.

Core Tools (always available):
- search_knowledge_base: Semantic search over knowledge base

Optional Tools:
- get_weather: Weather information via Open-Meteo API
- get_worksite_info: Brussels worksite data via OSIRIS API
- external_api_example: Template for custom API integrations
"""

from packages.core.tools.osiris_worksite import get_worksite_info
from packages.core.tools.search_knowledge_base import search_knowledge_base
from packages.core.tools.weather_tool import get_weather

# Tool registry
_AVAILABLE_TOOLS = {
    "search_knowledge_base": search_knowledge_base,
    "weather": get_weather,
    "osiris_worksite": get_worksite_info,
}


def get_tools(enabled_tools: list[str] | None = None) -> list:
    """Get list of tools for agent.

    Args:
        enabled_tools: List of tool names to enable.
                      If None, returns all available tools.
                      If empty list, returns only search_knowledge_base.

    Returns:
        List of tool functions

    Examples:
        >>> get_tools()  # All tools
        [search_knowledge_base, get_weather]

        >>> get_tools(["weather"])  # Only weather
        [search_knowledge_base, get_weather]

        >>> get_tools([])  # Only core search
        [search_knowledge_base]
    """
    # search_knowledge_base is always included (core functionality)
    tools = [search_knowledge_base]

    if enabled_tools is None:
        # Default: all tools
        tools.extend([get_weather, get_worksite_info])
    else:
        # Only specified tools
        for tool_name in enabled_tools:
            if tool_name in _AVAILABLE_TOOLS:
                tool = _AVAILABLE_TOOLS[tool_name]
                if tool not in tools:  # Avoid duplicates
                    tools.append(tool)

    return tools


def register_tool(name: str, tool_fn):
    """Register a new tool.

    Args:
        name: Tool identifier
        tool_fn: Async function with RunContext[RAGContext] signature

    Example:
        >>> from packages.core.tools import register_tool
        >>> register_tool("my_api", fetch_my_api)
    """
    _AVAILABLE_TOOLS[name] = tool_fn


__all__ = [
    "search_knowledge_base",
    "get_weather",
    "get_worksite_info",
    "get_tools",
    "register_tool",
]
