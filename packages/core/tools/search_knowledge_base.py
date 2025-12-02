"""Knowledge base search tool for RAG agent.

Implements hybrid search with:
- Semantic similarity (pgvector)
- French FTS (PostgreSQL)
- RRF ranking
- TOC filtering at database level
"""

import logging

from pydantic_ai import RunContext

from packages.config import settings
from packages.core.types import RAGContext

logger = logging.getLogger(__name__)


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

        # Generate embedding for query using cached embedder from context
        query_embedding = await rag_ctx.embedder.embed_query(query)

        # Use hybrid search (vector + FTS) with RRF ranking
        # TOC chunks are filtered at database level via exclude_toc
        results = await rag_ctx.db_client.hybrid_search(
            query_text=query,
            query_embedding=query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
            exclude_toc=settings.search.exclude_toc,
            rrf_k=settings.search.rrf_k,
        )

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

        # Handle no results
        if not results:
            logger.warning("No chunks found matching similarity threshold")
            return "⚠️ HORS PÉRIMÈTRE: Aucune information pertinente trouvée dans la base de connaissances pour cette requête."

        logger.info(f"Retrieved {len(results)} chunks from knowledge base")

        # Check relevance using max similarity
        max_similarity = max((r.get("similarity", 0) for r in results), default=0)

        if max_similarity < settings.search.out_of_scope_threshold:
            logger.warning(f"Low relevance results - max similarity: {max_similarity:.2f}")
            return f"⚠️ PERTINENCE FAIBLE: Les résultats trouvés ont une pertinence maximale de {int(max_similarity * 100)}%, ce qui suggère que cette question est probablement HORS DU PÉRIMÈTRE de la base de connaissances."

        # Build response with sources
        response_parts = []
        sources_tracked = []

        for index, row in enumerate(results):
            similarity = row["similarity"]
            content = row["content"]
            doc_title = row["document_title"]
            doc_source = row["document_source"]

            # Extract metadata
            doc_metadata = row.get("document_metadata", {})
            original_url = doc_metadata.get("url") if isinstance(doc_metadata, dict) else None

            chunk_metadata = row.get("metadata", {})
            page_start = (
                chunk_metadata.get("page_start") if isinstance(chunk_metadata, dict) else None
            )
            page_end = chunk_metadata.get("page_end") if isinstance(chunk_metadata, dict) else None

            # Build source object
            source_obj = {"title": doc_title, "path": doc_source, "similarity": similarity}

            # Add page info for PDFs
            if page_start is not None:
                source_obj["page_number"] = page_start
                if page_end is not None and page_end != page_start:
                    source_obj["page_range"] = f"p. {page_start}-{page_end}"
                else:
                    source_obj["page_range"] = f"p. {page_start}"

            # Add URL for scraped web content
            if original_url:
                source_obj["url"] = original_url
                source_obj["metadata"] = doc_metadata

            sources_tracked.append(source_obj)

            # Format citation
            source_ref = f"[{index + 1}]"
            similarity_pct = int(similarity * 100)
            confidence_marker = " - FAIBLE" if similarity < 0.6 else ""

            response_parts.append(
                f'{source_ref} Source: "{doc_title}" (Pertinence: {similarity_pct}%{confidence_marker})\n{content}\n'
            )

        # Store sources in context for retrieval
        rag_ctx.last_search_sources = sources_tracked

        if not response_parts:
            return "Des résultats ont été trouvés mais ils ne semblent pas directement pertinents."

        formatted_response = (
            f"Trouvé {len(response_parts)} résultats pertinents (triés par pertinence):\n\n"
            + "\n---\n".join(response_parts)
        )

        logger.info(f"RAG response: {len(formatted_response)} chars, {len(response_parts)} sources")

        return formatted_response

    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}", exc_info=True)
        return f"I encountered an error searching the knowledge base: {str(e)}"
