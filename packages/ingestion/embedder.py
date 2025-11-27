"""
Document embedding generation for vector search.

Supports OpenAI, Chutes.ai, Ollama, and any OpenAI-compatible API
via centralized configuration in packages.config.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from openai import APIError, RateLimitError

from .chunker import DocumentChunk

# Import flexible providers and settings
try:
    from packages.config import settings

    from ..utils.providers import get_embedding_client, get_embedding_model
except ImportError:
    # For direct execution or testing
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from packages.config import settings
    from packages.utils.providers import get_embedding_client, get_embedding_model

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Lazy initialization to avoid requiring API keys at import time
embedding_client = None
EMBEDDING_MODEL = None


def _get_embedding_client():
    """Get embedding client with lazy initialization."""
    global embedding_client, EMBEDDING_MODEL
    if embedding_client is None:
        embedding_client = get_embedding_client()
        EMBEDDING_MODEL = get_embedding_model()
    return embedding_client, EMBEDDING_MODEL


class EmbeddingGenerator:
    """Generates embeddings for document chunks."""

    def __init__(
        self,
        model: str | None = None,
        batch_size: int | None = None,
        max_retries: int | None = None,
        retry_delay: float | None = None,
    ):
        """
        Initialize embedding generator.

        Args:
            model: Embedding model to use (default from settings)
            batch_size: Number of texts to process in parallel (default from settings)
            max_retries: Maximum number of retry attempts (default from settings)
            retry_delay: Delay between retries in seconds (default from settings)
        """
        # Use settings defaults if not provided
        self.model = model if model is not None else settings.embedding.model
        self.batch_size = batch_size if batch_size is not None else settings.embedding.batch_size
        self.max_retries = (
            max_retries if max_retries is not None else settings.embedding.max_retries
        )
        self.retry_delay = (
            retry_delay if retry_delay is not None else settings.embedding.retry_delay
        )

        # Lazy load embedding client when first needed
        self._client = None

        # Model-specific configurations
        self.model_configs = {
            "text-embedding-3-small": {"dimensions": 1536, "max_tokens": 8191},
            "text-embedding-3-large": {"dimensions": 3072, "max_tokens": 8191},
            "text-embedding-ada-002": {"dimensions": 1536, "max_tokens": 8191},
        }

        if model not in self.model_configs:
            logger.warning(f"Unknown model {model}, using default config")
            self.config = {"dimensions": 1536, "max_tokens": 8191}
        else:
            self.config = self.model_configs[model]

    @property
    def client(self):
        """Lazy load embedding client on first access."""
        if self._client is None:
            self._client, _ = _get_embedding_client()
        return self._client

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Truncate text if too long
        if len(text) > self.config["max_tokens"] * 4:  # Rough token estimation
            text = text[: self.config["max_tokens"] * 4]

        for attempt in range(self.max_retries):
            try:
                response = await self.client.embeddings.create(model=self.model, input=text)

                return response.data[0].embedding

            except RateLimitError:
                if attempt == self.max_retries - 1:
                    raise

                # Exponential backoff for rate limits
                delay = self.retry_delay * (2**attempt)
                logger.warning(f"Rate limit hit, retrying in {delay}s")
                await asyncio.sleep(delay)

            except APIError as e:
                logger.error(f"OpenAI API error: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)

            except Exception as e:
                logger.error(f"Unexpected error generating embedding: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Filter and truncate texts
        processed_texts = []
        for text in texts:
            if not text or not text.strip():
                processed_texts.append("")
                continue

            # Truncate if too long
            if len(text) > self.config["max_tokens"] * 4:
                text = text[: self.config["max_tokens"] * 4]

            processed_texts.append(text)

        for attempt in range(self.max_retries):
            try:
                response = await self.client.embeddings.create(
                    model=self.model, input=processed_texts
                )

                return [data.embedding for data in response.data]

            except RateLimitError:
                if attempt == self.max_retries - 1:
                    raise

                delay = self.retry_delay * (2**attempt)
                logger.warning(f"Rate limit hit, retrying batch in {delay}s")
                await asyncio.sleep(delay)

            except APIError as e:
                logger.error(f"OpenAI API error in batch: {e}")
                if attempt == self.max_retries - 1:
                    # Fallback to individual processing
                    return await self._process_individually(processed_texts)
                await asyncio.sleep(self.retry_delay)

            except Exception as e:
                logger.error(f"Unexpected error in batch embedding: {e}")
                if attempt == self.max_retries - 1:
                    return await self._process_individually(processed_texts)
                await asyncio.sleep(self.retry_delay)

    async def _process_individually(self, texts: List[str]) -> List[List[float]]:
        """
        Process texts individually as fallback.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []

        for text in texts:
            try:
                if not text or not text.strip():
                    embeddings.append([0.0] * self.config["dimensions"])
                    continue

                embedding = await self.generate_embedding(text)
                embeddings.append(embedding)

                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Failed to embed text: {e}")
                # Use zero vector as fallback
                embeddings.append([0.0] * self.config["dimensions"])

        return embeddings

    async def embed_chunks(
        self, chunks: List[DocumentChunk], progress_callback: Optional[callable] = None
    ) -> List[DocumentChunk]:
        """
        Generate embeddings for document chunks.

        Args:
            chunks: List of document chunks
            progress_callback: Optional callback for progress updates

        Returns:
            Chunks with embeddings added
        """
        if not chunks:
            return chunks

        logger.info(f"Generating embeddings for {len(chunks)} chunks")

        # Process chunks in batches
        embedded_chunks = []
        total_batches = (len(chunks) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(chunks), self.batch_size):
            batch_chunks = chunks[i : i + self.batch_size]
            batch_texts = [chunk.content for chunk in batch_chunks]

            try:
                # Generate embeddings for this batch
                embeddings = await self.generate_embeddings_batch(batch_texts)

                # Add embeddings to chunks
                for chunk, embedding in zip(batch_chunks, embeddings):
                    # Create a new chunk with embedding
                    embedded_chunk = DocumentChunk(
                        content=chunk.content,
                        index=chunk.index,
                        start_char=chunk.start_char,
                        end_char=chunk.end_char,
                        metadata={
                            **chunk.metadata,
                            "embedding_model": self.model,
                            "embedding_generated_at": datetime.now().isoformat(),
                        },
                        token_count=chunk.token_count,
                    )

                    # Add embedding as a separate attribute
                    embedded_chunk.embedding = embedding
                    embedded_chunks.append(embedded_chunk)

                # Progress update
                current_batch = (i // self.batch_size) + 1
                if progress_callback:
                    progress_callback(current_batch, total_batches)

                logger.info(f"Processed batch {current_batch}/{total_batches}")

            except Exception as e:
                logger.error(f"Failed to process batch {i // self.batch_size + 1}: {e}")

                # Add chunks without embeddings as fallback
                for chunk in batch_chunks:
                    chunk.metadata.update(
                        {
                            "embedding_error": str(e),
                            "embedding_generated_at": datetime.now().isoformat(),
                        }
                    )
                    chunk.embedding = [0.0] * self.config["dimensions"]
                    embedded_chunks.append(chunk)

        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")
        return embedded_chunks

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query

        Returns:
            Query embedding
        """
        return await self.generate_embedding(query)

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for this model."""
        return self.config["dimensions"]


# Factory function
def create_embedder(model: str | None = None, **kwargs) -> EmbeddingGenerator:
    """Create embedding generator instance."""
    return EmbeddingGenerator(model=model, **kwargs)
