# packages/core/reranker.py
"""Cross-encoder reranking module for RAG retrieval."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy-loaded singleton to avoid import-time overhead
_cross_encoder: Optional[Any] = None
_encoder_lock = asyncio.Lock()


async def get_cross_encoder():
    """
    Get or initialize cross-encoder singleton.

    Uses async lock for thread-safe lazy initialization.
    Model is loaded once and reused across all requests.
    """
    global _cross_encoder

    if _cross_encoder is None:
        async with _encoder_lock:
            # Double-check after acquiring lock
            if _cross_encoder is None:
                from sentence_transformers import CrossEncoder

                logger.info("Loading cross-encoder model...")
                _cross_encoder = CrossEncoder(
                    "cross-encoder/ms-marco-MiniLM-L-6-v2",
                    max_length=512,  # Limit context window for performance
                    device="cpu",  # Explicit device; use 'cuda' if available
                )
                logger.info("Cross-encoder model loaded successfully")

    return _cross_encoder


async def rerank_results(
    query: str, results: List[Dict[str, Any]], top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Rerank search results using cross-encoder.

    Args:
        query: Original search query
        results: List of search results with 'content' field
        top_k: Number of top results to return after reranking

    Returns:
        Reranked results sorted by cross-encoder score

    Raises:
        ValueError: If results are empty or malformed
    """
    if not results:
        return []

    # Validate results structure
    for i, result in enumerate(results):
        if "content" not in result:
            raise ValueError(f"Result at index {i} missing 'content' field")

    try:
        encoder = await get_cross_encoder()

        # Create query-document pairs for scoring
        pairs = [[query, result["content"]] for result in results]

        # Run cross-encoder inference in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(None, encoder.predict, pairs)

        # Combine results with scores and sort
        scored_results = [
            {**result, "rerank_score": float(score)} for result, score in zip(results, scores)
        ]

        # Sort by rerank score (descending) and take top_k
        reranked = sorted(scored_results, key=lambda x: x["rerank_score"], reverse=True)[:top_k]

        logger.debug(
            f"Reranked {len(results)} results to top {len(reranked)}, "
            f"score range: {reranked[-1]['rerank_score']:.3f} - {reranked[0]['rerank_score']:.3f}"
        )

        return reranked

    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        # Graceful degradation: return original results truncated to top_k
        logger.warning("Falling back to original ranking without reranking")
        return results[:top_k]
