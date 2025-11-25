"""
Core RAG agent functionality.
"""

from .agent import (
    agent,
    close_db,
    get_last_sources,
    initialize_db,
    main,
    run_cli,
    search_knowledge_base,
)
from .cli import RAGAgentCLI
from .cli import main as cli_main

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
