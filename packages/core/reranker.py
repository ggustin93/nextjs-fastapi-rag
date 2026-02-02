"""Cross-encoder reranker for RAG pipeline.

Implements neural reranking to improve retrieval precision by rescoring
candidate documents with a cross-encoder model.

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │                  HybridReranker                      │
    │  ┌─────────────────┐    ┌─────────────────┐        │
    │  │   BGEReranker   │───▶│  CohereReranker │        │
    │  │   (Primary)     │fail│   (Fallback)    │        │
    │  └─────────────────┘    └─────────────────┘        │
    └─────────────────────────────────────────────────────┘

Usage:
    from packages.core.reranker import rerank_results, RerankerConfig

    config = RerankerConfig(enabled=True)
    reranked = await rerank_results(query, results, config)
"""

import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RerankerConfig:
    """Configuration for reranker behavior.

    Attributes:
        enabled: Whether reranking is active
        model: Model identifier (e.g., "BAAI/bge-reranker-v2-m3")
        top_k: Number of results to return after reranking
        batch_size: Batch size for inference
        fallback_enabled: Whether to use Cohere as fallback
        device: Device for inference ("cuda", "cpu", or "auto")
    """

    enabled: bool = False
    model: str = "BAAI/bge-reranker-v2-m3"
    top_k: int = 10
    batch_size: int = 32
    fallback_enabled: bool = True
    device: str = "auto"


@runtime_checkable
class Reranker(Protocol):
    """Protocol for reranker implementations."""

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Rerank documents by relevance to query.

        Args:
            query: Search query
            documents: List of document dicts with 'content' key
            top_k: Number of top results to return

        Returns:
            Reranked documents with 'rerank_score' added
        """
        ...


class BaseReranker(ABC):
    """Abstract base class for reranker implementations."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Rerank documents by relevance to query."""
        pass

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        """Normalize scores to 0-1 range using min-max normalization.

        Args:
            scores: Raw scores from model

        Returns:
            Normalized scores in [0, 1] range
        """
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)

        # Avoid division by zero
        if max_score == min_score:
            return [0.5] * len(scores)

        return [(s - min_score) / (max_score - min_score) for s in scores]


class BGEReranker(BaseReranker):
    """Cross-encoder reranker using BAAI/bge-reranker models.

    Uses HuggingFace transformers for local inference. Supports GPU
    acceleration when available.
    """

    _init_lock = threading.Lock()  # Thread-safety for lazy initialization

    def __init__(self, config: RerankerConfig):
        """Initialize BGE reranker.

        Args:
            config: Reranker configuration
        """
        self.config = config
        self._model = None
        self._tokenizer = None
        self._device = None
        self._initialized = False

    def _lazy_init(self) -> None:
        """Lazily initialize model and tokenizer on first use.

        Thread-safe via double-checked locking pattern.
        """
        if self._initialized:
            return

        with self._init_lock:
            # Double-check after acquiring lock
            if self._initialized:
                return

            try:
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                logger.info(f"Loading reranker model: {self.config.model}")

                # Determine device
                if self.config.device == "auto":
                    self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                else:
                    self._device = torch.device(self.config.device)

                # Load model and tokenizer
                self._tokenizer = AutoTokenizer.from_pretrained(self.config.model)
                self._model = AutoModelForSequenceClassification.from_pretrained(self.config.model)
                self._model = self._model.to(self._device)
                self._model.eval()

                self._initialized = True
                logger.info(f"Reranker initialized on {self._device}")

            except ImportError as e:
                raise ImportError(
                    "transformers and torch are required for BGE reranker. "
                    "Install with: pip install transformers torch"
                ) from e
            except Exception as e:
                logger.error(f"Failed to initialize BGE reranker: {e}")
                raise

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Rerank documents using BGE cross-encoder.

        Args:
            query: Search query
            documents: Documents with 'content' key
            top_k: Number of results to return

        Returns:
            Top-k documents sorted by rerank score
        """
        if not documents:
            return []

        # Lazy initialization
        self._lazy_init()

        import torch

        # Extract content from documents
        contents = [doc.get("content", "") for doc in documents]

        # Create query-document pairs
        pairs = [[query, content] for content in contents]

        # Process in batches
        all_scores = []
        for i in range(0, len(pairs), self.config.batch_size):
            batch_pairs = pairs[i : i + self.config.batch_size]

            # Tokenize
            inputs = self._tokenizer(
                batch_pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            # Inference
            with torch.no_grad():
                outputs = self._model(**inputs)
                # BGE reranker outputs logits; take first column for relevance score
                scores = outputs.logits.view(-1).cpu().tolist()
                all_scores.extend(scores)

        # Normalize scores to 0-1 range
        normalized_scores = self._normalize_scores(all_scores)

        # Add scores to documents
        scored_docs = []
        for doc, score in zip(documents, normalized_scores):
            doc_copy = dict(doc)
            doc_copy["rerank_score"] = score
            scored_docs.append(doc_copy)

        # Sort by rerank score and return top_k
        scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)

        logger.info(
            f"BGE reranked {len(documents)} docs → top {top_k}",
            extra={
                "top_score": scored_docs[0]["rerank_score"] if scored_docs else 0,
                "min_score": scored_docs[-1]["rerank_score"] if scored_docs else 0,
            },
        )

        return scored_docs[:top_k]


class CohereReranker(BaseReranker):
    """Fallback reranker using Cohere's rerank API.

    Requires COHERE_API_KEY environment variable.
    """

    def __init__(self, config: RerankerConfig):
        """Initialize Cohere reranker.

        Args:
            config: Reranker configuration
        """
        self.config = config
        self._client = None

    def _lazy_init(self) -> None:
        """Lazily initialize Cohere client on first use."""
        if self._client is not None:
            return

        import os

        try:
            import cohere

            api_key = os.getenv("COHERE_API_KEY")
            if not api_key:
                raise ValueError("COHERE_API_KEY environment variable not set")

            self._client = cohere.AsyncClient(api_key=api_key)
            logger.info("Cohere reranker client initialized")

        except ImportError as e:
            raise ImportError(
                "cohere package is required for Cohere reranker. "
                "Install with: pip install cohere"
            ) from e

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Rerank documents using Cohere API.

        Args:
            query: Search query
            documents: Documents with 'content' key
            top_k: Number of results to return

        Returns:
            Top-k documents sorted by rerank score
        """
        if not documents:
            return []

        self._lazy_init()

        # Extract content for Cohere API
        contents = [doc.get("content", "") for doc in documents]

        # Call Cohere rerank API
        response = await self._client.rerank(
            query=query,
            documents=contents,
            top_n=top_k,
            model="rerank-multilingual-v3.0",
        )

        # Map results back to original documents
        scored_docs = []
        for result in response.results:
            doc_copy = dict(documents[result.index])
            doc_copy["rerank_score"] = result.relevance_score
            scored_docs.append(doc_copy)

        logger.info(
            f"Cohere reranked {len(documents)} docs → top {top_k}",
            extra={
                "top_score": scored_docs[0]["rerank_score"] if scored_docs else 0,
            },
        )

        return scored_docs


class HybridReranker(BaseReranker):
    """Orchestrator that tries BGE first, falls back to Cohere on failure."""

    def __init__(self, config: RerankerConfig):
        """Initialize hybrid reranker with primary and fallback.

        Args:
            config: Reranker configuration
        """
        self.config = config
        self._primary: Optional[BGEReranker] = None
        self._fallback: Optional[CohereReranker] = None

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Rerank with fallback strategy.

        Tries BGE reranker first. If it fails and fallback is enabled,
        tries Cohere. If both fail, returns original documents.

        Args:
            query: Search query
            documents: Documents with 'content' key
            top_k: Number of results to return

        Returns:
            Reranked documents or original on complete failure
        """
        if not documents:
            return []

        # Try primary (BGE)
        try:
            if self._primary is None:
                self._primary = BGEReranker(self.config)
            return await self._primary.rerank(query, documents, top_k)

        except Exception as e:
            logger.warning(f"BGE reranker failed: {e}")

            # Try fallback (Cohere) if enabled
            if self.config.fallback_enabled:
                try:
                    if self._fallback is None:
                        self._fallback = CohereReranker(self.config)
                    return await self._fallback.rerank(query, documents, top_k)

                except Exception as fallback_error:
                    logger.error(f"Cohere fallback also failed: {fallback_error}")

            # Return original documents (truncated to top_k) as last resort
            logger.warning("All rerankers failed, returning original order")
            return documents[:top_k]


# Singleton instance for reuse
_reranker_instance: Optional[HybridReranker] = None


def get_reranker(config: RerankerConfig) -> HybridReranker:
    """Get or create singleton reranker instance.

    Args:
        config: Reranker configuration

    Returns:
        HybridReranker instance
    """
    global _reranker_instance

    if _reranker_instance is None:
        _reranker_instance = HybridReranker(config)

    return _reranker_instance


async def rerank_results(
    query: str,
    results: list[dict[str, Any]],
    config: Optional[RerankerConfig] = None,
) -> list[dict[str, Any]]:
    """Convenience function to rerank search results.

    This is the main entry point for reranking in the RAG pipeline.

    Args:
        query: Original search query (not expanded)
        results: Search results from hybrid_search
        config: Reranker configuration (uses defaults if None)

    Returns:
        Reranked results if enabled, otherwise original results
    """
    if config is None:
        from packages.config import settings

        config = RerankerConfig(
            enabled=settings.search.reranker_enabled,
            model=settings.search.reranker_model,
            top_k=settings.search.reranker_top_k,
            batch_size=settings.search.reranker_batch_size,
            fallback_enabled=settings.search.reranker_fallback_enabled,
        )

    # Skip if disabled
    if not config.enabled:
        logger.debug("Reranker disabled, returning original results")
        return results

    # Skip if no results
    if not results:
        return results

    reranker = get_reranker(config)
    return await reranker.rerank(query, results, config.top_k)


def clear_reranker_cache() -> None:
    """Clear the singleton reranker instance.

    Useful for testing or when configuration changes.
    """
    global _reranker_instance
    _reranker_instance = None
