"""
RAG CLI Agent with PostgreSQL/PGVector
=======================================
Text-based CLI agent that searches through knowledge base using semantic similarity
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext

from packages.utils.supabase_client import SupabaseRestClient

# Load environment variables
load_dotenv(".env")

logger = logging.getLogger(__name__)

# Global REST client
rest_client = None

# Global to track last search sources
last_search_sources = []


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


async def search_knowledge_base(ctx: RunContext[None], query: str, limit: int = 5) -> str:
    """
    Search the knowledge base using semantic similarity.

    Args:
        query: The search query to find relevant information
        limit: Maximum number of results to return (default: 5)

    Returns:
        Formatted search results with source citations
    """
    try:
        # Ensure database is initialized
        if not rest_client:
            await initialize_db()

        # Generate embedding for query
        from packages.ingestion.embedder import create_embedder

        embedder = create_embedder()
        query_embedding = await embedder.embed_query(query)

        # Search using REST API
        results = await rest_client.similarity_search(query_embedding=query_embedding, limit=limit)

        # Format results for response
        if not results:
            return "No relevant information found in the knowledge base for your query."

        # Build response with sources and track them globally
        global last_search_sources
        response_parts = []
        sources_tracked = []

        for i, row in enumerate(results, 1):
            similarity = row["similarity"]
            content = row["content"]
            doc_title = row["document_title"]
            doc_source = row["document_source"]

            # Track source for frontend
            sources_tracked.append(
                {"title": doc_title, "path": doc_source, "similarity": similarity}
            )

            # Include both title and file path for exact source citation
            source_citation = f"[Source: {doc_title} ({doc_source})]"
            response_parts.append(f"{source_citation}\n{content}\n")

        # Store sources globally for retrieval
        last_search_sources = sources_tracked

        if not response_parts:
            return "Found some results but they may not be directly relevant to your query. Please try rephrasing your question."

        return f"Found {len(response_parts)} relevant results:\n\n" + "\n---\n".join(response_parts)

    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}", exc_info=True)
        return f"I encountered an error searching the knowledge base: {str(e)}"


# Create the PydanticAI agent with the RAG tool
agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="""You are an intelligent knowledge assistant with access to an organization's documentation and information.
Your role is to help users find accurate information from the knowledge base.
You have a professional yet friendly demeanor.

IMPORTANT: Always search the knowledge base before answering questions about specific information.
If information isn't in the knowledge base, clearly state that and offer general guidance.
Be concise but thorough in your responses.
Ask clarifying questions if the user's query is ambiguous.
When you find relevant information, synthesize it clearly and cite the source documents.""",
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

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable is required")
        sys.exit(1)

    # Run the CLI
    await run_cli()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nShutting down...")
