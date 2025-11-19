"""
Core RAG agent functionality.
"""

from .agent import (
    agent,
    search_knowledge_base,
    initialize_db,
    close_db,
    run_cli,
    main,
    get_last_sources,
)
from .cli import RAGAgentCLI, main as cli_main

__all__ = [
    "agent",
    "search_knowledge_base",
    "initialize_db",
    "close_db",
    "run_cli",
    "main",
    "get_last_sources",
    "RAGAgentCLI",
    "cli_main",
]
