"""Knowledge base search tool for RAG agent.

Implements hybrid search with:
- Semantic similarity (pgvector)
- French FTS (PostgreSQL)
- RRF ranking
- TOC filtering at database level
- Title-based re-ranking for better relevance
- Query expansion for vocabulary mismatch (configurable per-domain)
"""

import logging
import re
import unicodedata
from functools import lru_cache

from pydantic_ai import RunContext

from packages.config import PROJECT_ROOT, settings
from packages.core.query_expansion import expand_query
from packages.core.types import RAGContext
from packages.utils.prompt_loader import load_json_config

logger = logging.getLogger(__name__)


@lru_cache()
def _load_stopwords(language: str = "default") -> set[str]:
    """Load stopwords from configuration file.

    Args:
        language: Language code (default, fr, en, nl)

    Returns:
        Set of stopwords for the given language
    """
    data = load_json_config(
        config_name="stopwords",
        default_path=PROJECT_ROOT / "config" / "stopwords.json",
        env_var_file="STOPWORDS_FILE",
    )

    if data:
        # Try requested language, fallback to default
        stopwords = data.get(language, data.get("default", []))
        return set(stopwords)

    # Hardcoded fallback if no config file
    return {
        "quoi",
        "quel",
        "quelle",
        "quels",
        "quelles",
        "est",
        "sont",
        "une",
        "des",
        "les",
        "pour",
        "dans",
        "avec",
        "que",
        "qui",
        "comment",
        "pourquoi",
    }


def _normalize_text(text: str) -> str:
    """Normalize text by removing accents and lowercasing."""
    # NFD decomposition separates base chars from accents
    normalized = unicodedata.normalize("NFD", text.lower())
    # Remove combining diacritical marks (accents)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def _extract_keywords(query: str, classifiers: list[str] | None = None) -> list[str]:
    """Extract meaningful keywords from query for title matching.

    Generic extraction of classification patterns and significant terms.

    Args:
        query: The search query to extract keywords from
        classifiers: List of classifier terms to match (from settings if None)
    """
    normalized = _normalize_text(query)

    keywords = []

    # Extract classification patterns using configurable classifiers
    # Matches any letter, number, or roman numeral after the classifier
    if classifiers is None:
        classifiers = settings.search.title_rerank_classifiers
    for classifier in classifiers:
        patterns = re.findall(rf"{classifier}\s*([a-z0-9]+|[ivxlc]+)", normalized, re.IGNORECASE)
        keywords.extend([f"{classifier} {p.upper()}" for p in patterns])

    # Extract other significant terms (words > 3 chars, not stopwords)
    # Stopwords loaded from config file (config/stopwords.json)
    stopwords = _load_stopwords()
    words = re.findall(r"\b[a-z]{4,}\b", normalized)
    keywords.extend([w for w in words if w not in stopwords])

    return keywords


def _calculate_title_boost(
    doc_title: str,
    keywords: list[str],
    max_boost: float | None = None,
    classifiers: list[str] | None = None,
) -> float:
    """Calculate boost factor based on title-keyword matching.

    Args:
        doc_title: Document title to match against
        keywords: Keywords extracted from query
        max_boost: Maximum boost factor (from settings if None)
        classifiers: List of classifier terms for primary matching (from settings if None)

    Returns:
        Boost factor between 0.0 and max_boost
    """
    if not keywords or not doc_title:
        return 0.0

    if max_boost is None:
        max_boost = settings.search.title_rerank_boost
    if classifiers is None:
        classifiers = settings.search.title_rerank_classifiers

    normalized_title = _normalize_text(doc_title)
    boost = 0.0

    # Calculate boost per-classifier for primary matches (2/3 of max)
    # and per-keyword for secondary matches (1/5 of max)
    primary_boost = max_boost * 2 / 3  # ~0.10 for default 0.15
    secondary_boost = max_boost / 5  # ~0.03 for default 0.15

    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in normalized_title:
            # Strong match for classifier patterns (e.g., "type A")
            is_classifier_match = any(keyword_lower.startswith(c) for c in classifiers)
            if is_classifier_match:
                boost += primary_boost
            else:
                boost += secondary_boost

    return min(boost, max_boost)


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

        # Expand query to handle vocabulary mismatch
        # Uses configurable prompt from config/prompts/query_expansion.txt
        expanded_query = await expand_query(query)

        # Generate embedding for EXPANDED query for better retrieval
        query_embedding = await rag_ctx.embedder.embed_query(expanded_query)

        # Use hybrid search (vector + FTS) with RRF ranking
        # TOC chunks are filtered at database level via exclude_toc
        # Use expanded query for better FTS matching
        results = await rag_ctx.db_client.hybrid_search(
            query_text=expanded_query,
            query_embedding=query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
            exclude_toc=settings.search.exclude_toc,
            rrf_k=settings.search.rrf_k,
        )

        # Apply title-based re-ranking to boost relevant documents (if enabled)
        if settings.search.title_rerank_enabled:
            keywords = _extract_keywords(query)
        else:
            keywords = []

        if keywords:
            for result in results:
                doc_title = result.get("document_title", "")
                boost = _calculate_title_boost(doc_title, keywords)
                if boost > 0:
                    original_sim = result.get("similarity", 0)
                    result["similarity"] = min(original_sim + boost, 1.0)
                    result["title_boosted"] = True
                    logger.debug(
                        f"Title boost applied: '{doc_title}' +{boost:.2f} "
                        f"({original_sim:.3f} -> {result['similarity']:.3f})"
                    )

            # Re-sort by boosted similarity
            results = sorted(results, key=lambda x: x.get("similarity", 0), reverse=True)
            logger.info(f"Re-ranked results with keywords: {keywords}")

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
            return (
                f"❌ QUESTION HORS PÉRIMÈTRE (score max: {int(max_similarity * 100)}%)\n\n"
                "La base de connaissances ne contient PAS d'information pertinente sur ce sujet.\n"
                "Tu DOIS répondre que cette question est hors de ton périmètre d'expertise.\n"
                "N'INVENTE RIEN - refuse poliment en expliquant que tu ne peux répondre qu'aux questions "
                "sur les chantiers, travaux de voirie et permis d'urbanisme à Bruxelles."
            )

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

            # Include content inline for ALL sources (enables chunk/full toggle)
            # PDFs benefit from chunk preview + full document viewing
            source_obj["content"] = content

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
