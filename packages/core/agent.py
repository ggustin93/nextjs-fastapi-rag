"""
RAG CLI Agent with PostgreSQL/PGVector
=======================================
Text-based CLI agent that searches through knowledge base using semantic similarity.
Uses deterministic query reformulation for improved semantic matching.
"""

import asyncio
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext

from packages.config import settings
from packages.core.config import DomainConfig, QueryExpansionConfig
from packages.utils.supabase_client import SupabaseRestClient

# FlashRank for local re-ranking (lazy-loaded to avoid startup cost)
_reranker = None


def get_reranker():
    """Lazy-load FlashRank reranker to avoid startup cost."""
    global _reranker
    if _reranker is None:
        from flashrank import Ranker

        _reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="./.flashrank_cache")
        logger.info("FlashRank reranker initialized")
    return _reranker


# Load environment variables
load_dotenv(".env")

logger = logging.getLogger(__name__)

# Global REST client
rest_client = None

# Global to track last search sources
last_search_sources = []


# ==============================================================================
# RAGContext: Dependency Injection for Agent Runtime
# ==============================================================================


@dataclass
class RAGContext:
    """RAG agent runtime context with dependency injection.

    This is the CORE context for the RAG agent - contains all runtime dependencies
    needed for agent operations. Replaces global singletons to enable:
    - Multiple independent agent instances
    - Testability with mock dependencies
    - Clean dependency management

    All fields are optional except db_client - external tools can add their own
    config to this context if needed (e.g., external_api_config for weather API).
    """

    db_client: SupabaseRestClient
    reranker: Optional[Any] = None
    domain_config: Optional[DomainConfig] = None
    last_search_sources: list = field(default_factory=list)
    # External API configs can be added optionally:
    # external_api_config: Optional[ExternalAPIConfig] = None


async def create_rag_context(domain_config: Optional[DomainConfig] = None) -> RAGContext:
    """Create RAG context with core dependencies.

    Factory function to initialize all agent runtime dependencies. All parameters
    are optional - creates a generic RAG agent by default. For domain-specific
    behavior, pass a DomainConfig with query expansion settings.

    Args:
        domain_config: Optional domain-specific configuration for query expansion.
                      If None, uses generic RAG behavior.

    Returns:
        Initialized RAGContext with all dependencies ready for agent use.

    Example:
        # Generic RAG (no domain customization)
        context = await create_rag_context()

        # Domain-specific RAG with query expansion
        config = DomainConfig(query_expansion=QueryExpansionConfig())
        context = await create_rag_context(domain_config=config)
    """
    # Initialize database client
    db_client = SupabaseRestClient()
    await db_client.initialize()
    logger.info("RAGContext: Supabase client initialized")

    # Initialize re-ranker (lazy-loaded through get_reranker())
    from flashrank import Ranker

    reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="./.flashrank_cache")
    logger.info("RAGContext: FlashRank reranker initialized")

    # Create context with all dependencies
    return RAGContext(
        db_client=db_client,
        reranker=reranker,
        domain_config=domain_config,  # Optional - None for generic RAG
        last_search_sources=[],
    )


def reformulate_query(query: str) -> str:
    """
    Remove question artifacts while preserving semantic intent for French queries.

    This approach removes interrogative patterns and filler words while keeping:
    - Prepositions that indicate relationships (de, du, des, d')
    - Quantifiers that indicate scope (tous, toutes, tout)
    - Semantic markers that carry meaning

    Examples:
        "C'est quoi un chantier de type D ?" → "chantier de type D"
        "Quels sont tous les critères du type D ?" → "tous les critères du type D"
        "Quelle est la durée maximale ?" → "durée maximale"

    Args:
        query: The user's question in French

    Returns:
        Query with question artifacts removed, semantic markers preserved
    """
    from packages.ingestion.french_stopwords import (
        FRENCH_STOPWORDS,
        QUESTION_PATTERNS,
        SEMANTIC_MARKERS,
    )

    # Normalize: lowercase, strip whitespace and punctuation
    q = query.lower().strip().rstrip("?!.")

    # Remove question patterns
    for pattern in QUESTION_PATTERNS:
        if pattern in q:
            q = q.replace(pattern, "").strip()

    # Tokenize and filter stopwords while preserving semantic markers
    tokens = q.split()
    filtered_tokens = []

    for token in tokens:
        # Clean punctuation from token for comparison
        clean_token = token.strip("'\".,;:!?")

        # Keep token if:
        # 1. It's a semantic marker (de, du, tous, etc.)
        # 2. It's not a stopword
        # 3. It's not empty
        if clean_token in SEMANTIC_MARKERS or (clean_token not in FRENCH_STOPWORDS and clean_token):
            filtered_tokens.append(token)

    result = " ".join(filtered_tokens).strip()

    # Only log if query was actually changed
    if result != query:
        logger.debug(f"Query reformulated: '{query}' → '{result}'")

    return result if result else query


# Initialize domain config with query expansion enabled (for backward compatibility)
# Users can set this to DomainConfig() or None for generic RAG
domain_config = DomainConfig(query_expansion=QueryExpansionConfig())


def expand_query_for_fts(query: str, config: Optional[DomainConfig] = None) -> str:
    """
    Expand query with synonyms and related terms for better FTS matching.

    This function is OPTIONAL - if config is None or query_expansion is None,
    it returns the query unchanged. This makes query expansion completely optional
    and allows the RAG system to work generically without domain-specific configuration.

    When enabled with a DomainConfig, it can expand queries based on domain-specific
    synonyms and criteria (e.g., for French FTS that drops single letters as stopwords).

    Args:
        query: The search query (already reformulated)
        config: Optional domain configuration. If None or config.query_expansion is None,
                no expansion is performed (generic RAG behavior)

    Returns:
        Query with expansion terms added for FTS, or original query if no expansion configured
    """
    # No expansion if config is None or query_expansion is disabled
    if config is None or config.query_expansion is None:
        return query  # Generic RAG behavior - no domain-specific expansion

    query_lower = query.lower()

    # Build expansions map from config
    expansions_map = {
        "type d": config.query_expansion.type_d,
        "type e": config.query_expansion.type_e,
        "type a": config.query_expansion.type_a,
    }

    # Check if query mentions occupation types
    expanded_terms = []

    for type_key, expansions in expansions_map.items():
        # Check various patterns: "type d", "type-d", "typed", "chantier de type d"
        patterns = [
            type_key,
            type_key.replace(" ", "-"),
            type_key.replace(" ", ""),
            f"chantier de {type_key}",
            f"occupation de {type_key}",
            f"critères du {type_key}",
            f"critères {type_key}",
        ]

        if any(pattern in query_lower for pattern in patterns):
            # Add the most important expansion terms
            expanded_terms.extend(expansions["synonyms"][:2])  # Main synonyms
            expanded_terms.extend(expansions["criteria"][:2])  # Key criteria
            logger.debug(f"Query expansion triggered for '{type_key}': adding {expanded_terms}")
            break  # Only expand for first matching type

    if expanded_terms:
        # Combine original query with expansion terms using OR logic
        # FTS will match documents containing ANY of these terms
        expansion_str = " OR ".join(expanded_terms[:4])  # Limit to avoid overly broad search
        expanded_query = f"{query} OR {expansion_str}"
        logger.info(f"Query expanded: '{query}' → '{expanded_query}'")
        return expanded_query

    return query


# TOC detection patterns for French documents
TOC_PATTERNS = [
    r"^\s*table\s*(des\s*)?mati[èe]res?\s*$",
    r"^\s*sommaire\s*$",
    r"^\s*contents?\s*$",
    r"^[A-Z\s\.]+\s+\d+\s*$",  # "CHAPTER NAME    12"
    r"^\d+\.\s+.{5,50}\s+\d+\s*$",  # "1.2 Section name   15"
]


def is_toc_chunk(content: str) -> bool:
    """Detect if chunk is likely a Table of Contents entry.

    TOC chunks typically contain:
    - Short lines with page numbers at the end
    - Section headers like "Table des matières", "Sommaire"
    - Numbered section references with page numbers

    Args:
        content: The chunk content to analyze

    Returns:
        True if the chunk appears to be TOC content
    """
    if not content or len(content.strip()) < 10:
        return False

    lines = content.strip().split("\n")

    # If most lines end with just a number (page reference), it's likely TOC
    page_ref_lines = 0
    for line in lines:
        stripped = line.strip()
        # Check for lines ending with just digits (page numbers)
        if re.search(r"\s+\d+\s*$", stripped):
            page_ref_lines += 1

    # If more than 50% of lines have page references, it's TOC
    if len(lines) > 0 and page_ref_lines / len(lines) > 0.5:
        logger.debug(f"TOC detected: {page_ref_lines}/{len(lines)} lines have page refs")
        return True

    # Check explicit TOC patterns
    for pattern in TOC_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            logger.debug(f"TOC detected: matched pattern '{pattern}'")
            return True

    return False


def get_last_sources(context: Optional[RAGContext] = None):
    """Get and clear the last search sources.

    Args:
        context: Optional RAGContext. If provided, sources are retrieved from context.
                 If None, falls back to global variable for backward compatibility.

    Returns:
        List of source objects from the last search.
    """
    if context:
        # Use context-based sources (preferred)
        sources = context.last_search_sources.copy()
        context.last_search_sources = []
        return sources
    else:
        # Fallback to global for backward compatibility
        global last_search_sources
        sources = last_search_sources.copy()
        last_search_sources = []
        return sources


async def initialize_db():
    """Initialize Supabase REST client."""
    global rest_client
    if not rest_client:
        rest_client = SupabaseRestClient()
        await rest_client.initialize()
        logger.info("Supabase REST client initialized")


async def close_db():
    """Close Supabase REST client."""
    global rest_client
    if rest_client:
        await rest_client.close()
        logger.info("Supabase REST client closed")


async def search_knowledge_base(
    ctx: RunContext[RAGContext], query: str, limit: int | None = None
) -> str:
    """
    Search the knowledge base using semantic similarity.

    Args:
        query: The search query to find relevant information
        limit: Maximum number of results to return (default from settings)

    Returns:
        Formatted search results with source citations and relevance scores
    """
    if limit is None:
        limit = settings.search.default_limit

    similarity_threshold = settings.search.similarity_threshold

    # DEBUG: Log search initiation
    logger.info(
        "RAG search initiated",
        extra={
            "original_query": query,
            "limit": limit,
            "similarity_threshold": similarity_threshold,
        },
    )

    try:
        # Get RAG context from deps (dependency injection)
        rag_ctx: RAGContext = ctx.deps

        # Use db_client from context instead of global rest_client
        # Reformulate query for better semantic matching
        # Converts "Quelle est la superficie..." → "la valeur de la superficie..."
        search_query = reformulate_query(query)
        logger.debug(f"Query reformulated: '{query}' → '{search_query}'")

        # Expand query for FTS (optional - uses domain_config from context if available)
        # "type D" → "type D OR dispense OR 50 m² OR 24 heures"
        fts_query = expand_query_for_fts(search_query, rag_ctx.domain_config)

        # Generate embedding for reformulated query (NOT expanded - keeps semantic intent)
        from packages.ingestion.embedder import create_embedder

        embedder = create_embedder()
        query_embedding = await embedder.embed_query(search_query)

        # Use hybrid search (vector + keyword) for better recall
        # FTS uses expanded query; vector uses original for semantic matching
        # Falls back to vector-only search if hybrid fails
        results = await rag_ctx.db_client.hybrid_search(
            query_text=fts_query,  # Expanded query for FTS
            query_embedding=query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
        )

        # DEBUG: Log retrieval results
        logger.info(
            "RAG chunks retrieved",
            extra={
                "chunks_found": len(results),
                "avg_similarity": (
                    sum(r.get("similarity", 0) for r in results) / len(results) if results else 0
                ),
                "max_similarity": max((r.get("similarity", 0) for r in results), default=0),
                "min_similarity": min((r.get("similarity", 0) for r in results), default=0),
            },
        )

        # Format results for response
        if not results:
            logger.warning("No chunks found matching similarity threshold")
            return "Aucune information pertinente trouvée dans la base de connaissances pour cette requête."

        # Results from DB are already sorted by similarity (highest first)
        logger.info(f"Retrieved {len(results)} chunks from knowledge base")

        # Filter out TOC chunks that pollute search results
        original_count = len(results)
        filtered_results = [r for r in results if not is_toc_chunk(r.get("content", ""))]

        if len(filtered_results) < len(results):
            toc_count = original_count - len(filtered_results)
            logger.info(
                f"TOC filter: removed {toc_count} TOC chunks, {len(filtered_results)} remaining"
            )

        # Fallback: if all chunks were TOC, use original results with warning
        if not filtered_results and results:
            logger.warning("All chunks filtered as TOC, using original results")
            filtered_results = results

        # Use filtered results for response
        results = filtered_results

        # Re-rank results using FlashRank for better precision
        if len(results) > 5 and rag_ctx.reranker:
            try:
                from flashrank import RerankRequest

                # Use reranker from context (already initialized)
                reranker = rag_ctx.reranker

                # Format results for FlashRank
                passages = [
                    {
                        "id": idx,
                        "text": r.get("content", ""),
                        "meta": {
                            "document_title": r.get("document_title", ""),
                            "document_source": r.get("document_source", ""),
                            "similarity": r.get("similarity", 0),
                        },
                    }
                    for idx, r in enumerate(results)
                ]

                # Re-rank with original query
                rerank_request = RerankRequest(query=search_query, passages=passages)
                reranked = reranker.rerank(rerank_request)

                # Map re-ranked results back to original format
                reranked_results = []
                for item in reranked[:10]:  # Take top 10 re-ranked results
                    original_idx = item.get("id", 0)
                    if 0 <= original_idx < len(results):
                        result = results[original_idx].copy()
                        result["rerank_score"] = item.get("score", 0)
                        reranked_results.append(result)

                if reranked_results:
                    logger.info(
                        f"FlashRank re-ranking: {len(results)} → {len(reranked_results)} results, "
                        f"top score: {reranked_results[0].get('rerank_score', 0):.3f}"
                    )
                    results = reranked_results

            except Exception as e:
                logger.warning(f"FlashRank re-ranking failed, using hybrid search results: {e}")

        # DEBUG: Log chunk details
        for idx, row in enumerate(results[:3]):  # Log first 3 chunks
            logger.debug(
                f"Chunk {idx + 1} details",
                extra={
                    "similarity": row.get("similarity"),
                    "content_length": len(row.get("content", "")),
                    "document": row.get("document_title"),
                    "content_preview": row.get("content", "")[:100] + "...",
                },
            )

        # Build response with sources and track them in context
        response_parts = []
        sources_tracked = []

        for index, row in enumerate(results):
            similarity = row["similarity"]
            content = row["content"]
            doc_title = row["document_title"]
            doc_source = row["document_source"]

            # Extract metadata from row if available (for scraped web content)
            doc_metadata = row.get("document_metadata", {})
            original_url = doc_metadata.get("url") if isinstance(doc_metadata, dict) else None

            # Build source object
            source_obj = {"title": doc_title, "path": doc_source, "similarity": similarity}

            # Add URL if available (for scraped web content)
            if original_url:
                source_obj["url"] = original_url
                # Optionally include full metadata for future use
                source_obj["metadata"] = doc_metadata

            # Track source for frontend
            sources_tracked.append(source_obj)

            # Use numbered reference [1], [2], etc. with source metadata
            source_ref = f"[{index + 1}]"
            similarity_pct = int(similarity * 100)

            # Add similarity warning for low-confidence chunks
            confidence_marker = ""
            if similarity < 0.6:
                confidence_marker = " - FAIBLE"

            # Format with document title and similarity score
            response_parts.append(
                f'{source_ref} Source: "{doc_title}" (Pertinence: {similarity_pct}%{confidence_marker})\n{content}\n'
            )

        # Store sources in context for retrieval
        rag_ctx.last_search_sources = sources_tracked

        if not response_parts:
            logger.warning("Chunks found but response_parts is empty")
            return "Des résultats ont été trouvés mais ils ne semblent pas directement pertinents. Essayez de reformuler votre question."

        # DEBUG: Log final formatted response
        formatted_response = (
            f"Trouvé {len(response_parts)} résultats pertinents (triés par pertinence):\n\n"
            + "\n---\n".join(response_parts)
        )
        logger.info(
            "RAG tool return value",
            extra={
                "response_length": len(formatted_response),
                "num_sources": len(response_parts),
                "response_preview": formatted_response[:2000]
                + "...",  # Increased to 2000 chars for debugging
            },
        )
        # Log full response for debugging
        logger.info(f"FULL RAG RESPONSE:\n{formatted_response}")

        return formatted_response

    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}", exc_info=True)
        return f"I encountered an error searching the knowledge base: {str(e)}"


# Create the PydanticAI agent with RAG tool
# Uses settings.llm.create_model() to support OpenAI, Chutes.ai, Ollama, or any OpenAI-compatible API
# System prompt is now configurable via RAG_SYSTEM_PROMPT environment variable (see packages/config)
agent = Agent(
    settings.llm.create_model(),
    system_prompt=settings.llm.system_prompt,
    tools=[search_knowledge_base],
)


async def run_cli():
    """Run the agent in an interactive CLI with streaming."""

    # Initialize database
    await initialize_db()

    print("=" * 60)
    print("RAG Knowledge Assistant")
    print("=" * 60)
    print("Ask me anything about the knowledge base!")
    print("Type 'quit', 'exit', or press Ctrl+C to exit.")
    print("=" * 60)
    print()

    message_history = []

    try:
        while True:
            # Get user input
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "bye"]:
                print("\nAssistant: Thank you for using the knowledge assistant. Goodbye!")
                break

            print("Assistant: ", end="", flush=True)

            try:
                # Stream the response using run_stream
                async with agent.run_stream(user_input, message_history=message_history) as result:
                    # Stream text as it comes in (delta=True for only new tokens)
                    async for text in result.stream_text(delta=True):
                        # Print only the new token
                        print(text, end="", flush=True)

                    print()  # New line after streaming completes

                    # Update message history for context
                    message_history = result.all_messages()

            except KeyboardInterrupt:
                print("\n\n[Interrupted]")
                break
            except Exception as e:
                print(f"\n\nError: {e}")
                logger.error(f"Agent error: {e}", exc_info=True)

            print()  # Extra line for readability

    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    finally:
        await close_db()


async def main():
    """Main entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Check required environment variables
    if not os.getenv("SUPABASE_URL"):
        logger.error("SUPABASE_URL environment variable is required")
        sys.exit(1)

    # API key is required unless using a custom base_url (like Ollama)
    if not settings.llm.api_key and not settings.llm.base_url:
        logger.error("LLM_API_KEY or OPENAI_API_KEY environment variable is required")
        logger.error("(or set LLM_BASE_URL for local models like Ollama)")
        sys.exit(1)

    # Run the CLI
    await run_cli()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nShutting down...")
