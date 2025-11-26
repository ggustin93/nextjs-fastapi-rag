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

# Query reformulation patterns (French interrogative → declarative)
# This improves semantic matching between questions and declarative document content
QUERY_TRANSFORMS = {
    "quelle est": "la valeur de",
    "quel est": "le critère de",
    "quelles sont": "les conditions de",
    "quels sont": "les critères de",
    "comment": "la procédure pour",
    "quand": "le moment pour",
    "où": "le lieu de",
    "combien": "le montant de",
    "pourquoi": "la raison de",
}


def reformulate_query(query: str) -> str:
    """
    Transform interrogative query to declarative for better semantic matching.

    This is a deterministic transformation that converts questions into
    declarative statements, improving embedding similarity with document content.
    No LLM call = no hallucination risk, no latency, no cost.

    Args:
        query: The user's question

    Returns:
        Reformulated query in declarative form
    """
    query_lower = query.lower().strip()
    for pattern, replacement in QUERY_TRANSFORMS.items():
        if query_lower.startswith(pattern):
            reformulated = query_lower.replace(pattern, replacement, 1)
            logger.debug(f"Query reformulated: '{query}' → '{reformulated}'")
            return reformulated
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


async def search_knowledge_base(
    ctx: RunContext[None], query: str, limit: int | None = None
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

    try:
        # Ensure database is initialized
        if not rest_client:
            await initialize_db()

        # Reformulate query for better semantic matching
        # Converts "Quelle est la superficie..." → "la valeur de la superficie..."
        search_query = reformulate_query(query)

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

        # Format results for response
        if not results:
            return "Aucune information pertinente trouvée dans la base de connaissances pour cette requête."

        # Sort results by similarity (highest first)
        sorted_results = sorted(results, key=lambda x: x.get("similarity", 0), reverse=True)

        # Build response with sources and track them globally
        global last_search_sources
        response_parts = []
        sources_tracked = []

        for index, row in enumerate(sorted_results):
            similarity = row["similarity"]
            content = row["content"]
            doc_title = row["document_title"]
            doc_source = row["document_source"]

            # Track source for frontend
            sources_tracked.append(
                {"title": doc_title, "path": doc_source, "similarity": similarity}
            )

            # Use numbered reference [1], [2], etc. for citation
            source_ref = f"[{index + 1}]"
            response_parts.append(f"{source_ref}\n{content}\n")

        # Store sources globally for retrieval
        last_search_sources = sources_tracked

        if not response_parts:
            return "Des résultats ont été trouvés mais ils ne semblent pas directement pertinents. Essayez de reformuler votre question."

        return f"Trouvé {len(response_parts)} résultats pertinents (triés par pertinence):\n\n" + "\n---\n".join(response_parts)

    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}", exc_info=True)
        return f"I encountered an error searching the knowledge base: {str(e)}"


# System prompt for the RAG agent (kept as code - defines core agent behavior)
RAG_SYSTEM_PROMPT = """Tu es un assistant intelligent avec accès à la base de connaissances de l'organisation.
Ton rôle est d'aider les utilisateurs à trouver des informations précises et factuelles.

INSTRUCTIONS DE RECHERCHE:
1. Cherche TOUJOURS dans la base de connaissances avant de répondre à une question factuelle
2. Les résultats sont numérotés [1], [2], etc. par ordre de pertinence
3. Priorise les informations des sources avec pertinence > 70%
4. Si plusieurs sources se contredisent, cite celle avec le meilleur numéro (plus petit = plus pertinent)
5. Cite tes sources en utilisant les références numérotées [1], [2], etc. dans ton texte

STYLE DE RÉPONSE:
- Sois précis et factuel en utilisant les informations trouvées
- Si l'information n'est pas dans la base, dis-le clairement
- Synthétise les informations de plusieurs chunks si nécessaire
- Utilise des listes et une mise en forme claire pour faciliter la lecture
- Réponds en français

IMPORTANT: Ne devine JAMAIS les informations - utilise uniquement ce qui est dans la base de connaissances.
Si tu trouves une information spécifique (chiffre, critère, condition), cite-la exactement comme trouvée."""

# Create the PydanticAI agent with the RAG tool
# Uses settings.llm.create_model() to support OpenAI, Chutes.ai, Ollama, or any OpenAI-compatible API
agent = Agent(
    settings.llm.create_model(),
    system_prompt=RAG_SYSTEM_PROMPT,
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
