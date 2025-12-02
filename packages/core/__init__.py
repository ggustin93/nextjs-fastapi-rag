"""Core RAG agent functionality."""

# Agent creation (primary interface)
# Agent utilities
from .agent import agent, create_rag_context, get_last_sources

# CLI interface
from .cli import RAGAgentCLI
from .cli import main as cli_main
from .factory import create_rag_agent

# Tools (for custom agent creation)
from .tools import get_tools, register_tool

__all__ = [
    # Agent creation
    "create_rag_agent",
    # Agent utilities
    "agent",
    "create_rag_context",
    "get_last_sources",
    # CLI
    "RAGAgentCLI",
    "cli_main",
    # Tool management
    "get_tools",
    "register_tool",
]
