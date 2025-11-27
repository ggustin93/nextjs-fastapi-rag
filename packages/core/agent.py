"""
RAG CLI Agent with PostgreSQL/PGVector
=======================================
Text-based CLI agent that searches through knowledge base using semantic similarity.
Uses deterministic query reformulation for improved semantic matching.
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext

from packages.config import settings
from packages.utils.supabase_client import SupabaseRestClient

# Load environment variables
load_dotenv(".env")

logger = logging.getLogger(__name__)

# Global REST client
rest_client = None

# Global to track last search sources
last_search_sources = []

# Question patterns to remove for semantic search (longer patterns first)
# Removing question words preserves user vocabulary for better embedding match
QUESTION_PATTERNS = [
    "quelle est",
    "quel est",
    "quelles sont",
    "quels sont",
    "comment est-ce que",
    "comment",
    "quand est-ce que",
    "quand",
    "où est-ce que",
    "où",
    "combien de",
    "combien",
    "pourquoi est-ce que",
    "pourquoi",
    "est-ce que",
]


def reformulate_query(query: str) -> str:
    """
    Remove question words to focus on core keywords for semantic matching.

    This minimaliste approach removes interrogative patterns while preserving
    the user's exact vocabulary, letting embeddings handle semantic matching.
    No LLM call = no hallucination risk, no latency, no cost.

    Example: "Quelle est la superficie maximale?" → "superficie maximale"

    Args:
        query: The user's question

    Returns:
        Query with question words removed
    """
    # Normalize: lowercase, strip whitespace and punctuation
    q = query.lower().strip().rstrip("?!.")

    for pattern in QUESTION_PATTERNS:
        if q.startswith(pattern):
            # Remove question pattern
            result = q.replace(pattern, "", 1).strip()
            # Clean up leading articles/prepositions
            for article in ["le ", "la ", "les ", "l'", "de ", "du ", "des ", "d'"]:
                if result.startswith(article):
                    result = result[len(article) :]
            logger.debug(f"Query reformulated: '{query}' → '{result}'")
            return result

    return query


def get_last_sources():
    """Get and clear the last search sources."""
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


async def search_knowledge_base(ctx: RunContext[None], query: str, limit: int | None = None) -> str:
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
        # Ensure database is initialized
        if not rest_client:
            await initialize_db()

        # Reformulate query for better semantic matching
        # Converts "Quelle est la superficie..." → "la valeur de la superficie..."
        search_query = reformulate_query(query)
        logger.debug(f"Query reformulated: '{query}' → '{search_query}'")

        # Generate embedding for reformulated query
        from packages.ingestion.embedder import create_embedder

        embedder = create_embedder()
        query_embedding = await embedder.embed_query(search_query)

        # Search using REST API with threshold filtering
        results = await rest_client.similarity_search(
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

        # Sort results by similarity (highest first)
        sorted_results = sorted(results, key=lambda x: x.get("similarity", 0), reverse=True)

        # Deduplicate by document source (keep highest similarity per document)
        seen_documents = {}
        deduped_results = []
        for row in sorted_results:
            doc_source = row["document_source"]
            if doc_source not in seen_documents:
                seen_documents[doc_source] = True
                deduped_results.append(row)

        logger.info(
            f"Deduplicated sources: {len(results)} chunks → {len(deduped_results)} unique documents"
        )

        # DEBUG: Log chunk details
        for idx, row in enumerate(deduped_results[:3]):  # Log first 3 deduped chunks
            logger.debug(
                f"Chunk {idx + 1} details",
                extra={
                    "similarity": row.get("similarity"),
                    "content_length": len(row.get("content", "")),
                    "document": row.get("document_title"),
                    "content_preview": row.get("content", "")[:100] + "...",
                },
            )

        # Build response with deduplicated sources and track them globally
        global last_search_sources
        response_parts = []
        sources_tracked = []

        for index, row in enumerate(deduped_results):
            similarity = row["similarity"]
            content = row["content"]
            doc_title = row["document_title"]
            doc_source = row["document_source"]

            # Track source for frontend
            sources_tracked.append(
                {"title": doc_title, "path": doc_source, "similarity": similarity}
            )

            # Use numbered reference [1], [2], etc. with source metadata
            source_ref = f"[{index + 1}]"
            similarity_pct = int(similarity * 100)

            # Add similarity warning for low-confidence chunks
            confidence_marker = ""
            if similarity < 0.6:
                confidence_marker = " - FAIBLE"

            # Format with document title and similarity score
            response_parts.append(
                f"{source_ref} Source: \"{doc_title}\" (Pertinence: {similarity_pct}%{confidence_marker})\n{content}\n"
            )

        # Store sources globally for retrieval
        last_search_sources = sources_tracked

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
                "response_preview": formatted_response[:200] + "...",
            },
        )

        return formatted_response

    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}", exc_info=True)
        return f"I encountered an error searching the knowledge base: {str(e)}"


# Create the PydanticAI agent with the RAG tool
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
