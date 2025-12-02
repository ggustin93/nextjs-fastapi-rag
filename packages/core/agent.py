"""
RAG Agent with PostgreSQL/PGVector
====================================
Core RAG agent that searches through knowledge base using semantic similarity.
Uses hybrid search (vector + French FTS) with RRF ranking for optimal retrieval.

For interactive CLI usage, use packages.core.cli module instead.
"""

import logging

from dotenv import load_dotenv

from packages.config import settings
from packages.core.factory import create_rag_agent
from packages.core.types import RAGContext
from packages.utils.supabase_client import SupabaseRestClient

# Load environment variables
load_dotenv(".env")

logger = logging.getLogger(__name__)


async def create_rag_context() -> RAGContext:
    """Create RAG context with core dependencies.

    Factory function to initialize all agent runtime dependencies.
    Dependencies are initialized once and cached in the context to avoid
    repeated initialization overhead per search query.

    Returns:
        Initialized RAGContext with all dependencies ready for agent use.

    Example:
        context = await create_rag_context()
    """
    # Initialize database client
    db_client = SupabaseRestClient()
    await db_client.initialize()
    logger.info("RAGContext: Supabase client initialized")

    # Initialize embedder (cached in context to avoid per-query client init)
    from packages.ingestion.embedder import create_embedder

    embedder = create_embedder()
    logger.info("RAGContext: Embedder initialized")

    return RAGContext(
        db_client=db_client,
        embedder=embedder,
        weather_config=settings.weather,
        last_search_sources=[],
    )


def get_last_sources(context: RAGContext) -> list:
    """Get and clear the last search sources from context.

    Args:
        context: RAGContext containing the search sources.

    Returns:
        List of source objects from the last search.
    """
    sources = context.last_search_sources.copy()
    context.last_search_sources = []
    return sources


# Create the PydanticAI agent using factory for consistent configuration
# Uses settings.llm.create_model() to support OpenAI, Chutes.ai, Ollama, or any OpenAI-compatible API
# System prompt is configurable via RAG_SYSTEM_PROMPT environment variable (see packages/config)
# Tools are configurable via ENABLED_TOOLS environment variable
agent = create_rag_agent()
