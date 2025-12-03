"""
Supabase REST API client for database operations.

Uses Supabase Python SDK (HTTPS) to work around network restrictions.
Includes caching support for frequently accessed data.

Features:
    - REST API access to Supabase PostgreSQL
    - Vector similarity search via pgvector
    - LRU caching for document metadata and query results
    - Batch operations for improved performance
"""

import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from .cache import (
    document_metadata_cache,
    generate_cache_key,
    query_result_cache,
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class SupabaseRestClient:
    """
    REST API client for Supabase using official Python SDK.
    Works around network restrictions by using HTTPS instead of PostgreSQL protocol.
    """

    def __init__(self):
        """Initialize Supabase client."""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")

        if not self.url:
            raise ValueError("SUPABASE_URL environment variable not set")
        if not self.key:
            raise ValueError("SUPABASE_SERVICE_KEY environment variable not set")

        self.client: Client = create_client(self.url, self.key)
        logger.info("Supabase REST client initialized")

    async def initialize(self):
        """Initialize client (compatibility with existing code)."""
        logger.info("Supabase REST client ready")

    async def close(self):
        """Close client (compatibility with existing code)."""
        logger.info("Supabase REST client closed")

    async def delete_all_documents(self):
        """Clean database by deleting all documents and chunks."""
        try:
            # Delete all chunks first (foreign key constraint)
            self.client.table("chunks").delete().neq(
                "id", "00000000-0000-0000-0000-000000000000"
            ).execute()
            logger.info("Deleted all chunks")

            # Delete all documents
            self.client.table("documents").delete().neq(
                "id", "00000000-0000-0000-0000-000000000000"
            ).execute()
            logger.info("Deleted all documents")

        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise

    async def insert_document(
        self, title: str, source: str, content: str, metadata: Dict[str, Any]
    ) -> str:
        """
        Insert document via Supabase REST API.

        Args:
            title: Document title
            source: Document source path
            content: Full document content
            metadata: Additional metadata

        Returns:
            Document UUID as string
        """
        try:
            response = (
                self.client.table("documents")
                .insert(
                    {"title": title, "source": source, "content": content, "metadata": metadata}
                )
                .execute()
            )

            document_id = response.data[0]["id"]
            logger.debug(f"Inserted document: {title} ({document_id})")
            return document_id

        except Exception as e:
            logger.error(f"Error inserting document {title}: {e}")
            raise

    async def insert_chunk(
        self,
        document_id: str,
        content: str,
        embedding: List[float],
        chunk_index: int,
        metadata: Dict[str, Any],
        token_count: int,
        is_toc: bool = False,
    ):
        """
        Insert chunk via Supabase REST API.

        Args:
            document_id: Parent document UUID
            content: Chunk text content
            embedding: Vector embedding (1536 dimensions)
            chunk_index: Chunk position in document
            metadata: Additional metadata
            token_count: Number of tokens in chunk
            is_toc: True if chunk is Table of Contents content
        """
        try:
            # PostgreSQL vector format for Supabase
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"

            self.client.table("chunks").insert(
                {
                    "document_id": document_id,
                    "content": content,
                    "embedding": embedding_str,
                    "chunk_index": chunk_index,
                    "metadata": metadata,
                    "token_count": token_count,
                    "is_toc": is_toc,
                }
            ).execute()

            logger.debug(f"Inserted chunk {chunk_index} for document {document_id}")

        except Exception as e:
            logger.error(f"Error inserting chunk {chunk_index}: {e}")
            raise

    async def insert_chunks_batch(self, chunks_data: List[Dict[str, Any]]):
        """
        Insert multiple chunks in a single request for better performance.

        Args:
            chunks_data: List of chunk dictionaries with all required fields
        """
        try:
            # Convert embeddings to PostgreSQL vector format
            for chunk in chunks_data:
                if isinstance(chunk.get("embedding"), list):
                    chunk["embedding"] = "[" + ",".join(map(str, chunk["embedding"])) + "]"

            self.client.table("chunks").insert(chunks_data).execute()
            logger.info(f"Inserted batch of {len(chunks_data)} chunks")

        except Exception as e:
            logger.error(f"Error inserting chunk batch: {e}")
            raise

    async def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 30,
        similarity_threshold: float = 0.25,
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search via Supabase RPC function.

        Args:
            query_embedding: Query vector (1536 dimensions)
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1), passed to PostgreSQL for efficient filtering

        Returns:
            List of matching chunks with similarity scores above threshold
        """
        try:
            # PostgreSQL vector format
            embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

            # Pass threshold to PostgreSQL function for server-side filtering
            # More efficient than fetching all results and filtering in Python
            response = self.client.rpc(
                "match_chunks",
                {
                    "query_embedding": embedding_str,
                    "match_count": limit,
                    "similarity_threshold": similarity_threshold,
                },
            ).execute()

            logger.debug(
                f"Similarity search: {len(response.data)} results above threshold {similarity_threshold}"
            )

            return response.data

        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            raise

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        limit: int = 30,
        similarity_threshold: float = 0.25,
        exclude_toc: bool = True,
        rrf_k: int = 50,
        max_per_doc: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and French keyword matching.

        Uses Reciprocal Rank Fusion (RRF) to combine semantic and keyword results.
        Falls back to similarity_search if hybrid search fails.

        Args:
            query_text: Original search query for keyword matching
            query_embedding: Query vector (1536 dimensions)
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            exclude_toc: Whether to exclude TOC chunks marked during ingestion
            rrf_k: RRF parameter (default: 50). Lower values give more weight to top-ranked results.
            max_per_doc: Maximum chunks per document for source diversity (default: 3)

        Returns:
            List of matching chunks with similarity and RRF scores
        """
        try:
            # PostgreSQL vector format
            embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

            response = self.client.rpc(
                "hybrid_search",
                {
                    "query_text": query_text,
                    "query_embedding": embedding_str,
                    "match_count": limit,
                    "similarity_threshold": similarity_threshold,
                    "exclude_toc": exclude_toc,
                    "rrf_k": rrf_k,
                    "max_per_doc": max_per_doc,
                },
            ).execute()

            logger.info(
                f"Hybrid search: {len(response.data)} results for query '{query_text[:50]}...'"
            )

            return response.data

        except Exception as e:
            logger.warning(f"Hybrid search failed, falling back to similarity search: {e}")
            # Fallback to vector-only search
            return await self.similarity_search(query_embedding, limit, similarity_threshold)

    async def get_document_count(self) -> int:
        """Get total number of documents."""
        try:
            response = self.client.table("documents").select("id", count="exact").execute()
            return response.count
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0

    async def get_chunk_count(self) -> int:
        """Get total number of chunks."""
        try:
            response = self.client.table("chunks").select("id", count="exact").execute()
            return response.count
        except Exception as e:
            logger.error(f"Error getting chunk count: {e}")
            return 0

    async def get_document_by_id(
        self, document_id: str, use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get document by ID with optional caching.

        Args:
            document_id: Document UUID
            use_cache: Whether to use cache (default: True)

        Returns:
            Document data or None if not found
        """
        cache_key = f"doc:{document_id}"

        # Try cache first
        if use_cache:
            cached_doc = await document_metadata_cache.async_get(cache_key)
            if cached_doc is not None:
                logger.debug(f"Cache hit for document: {document_id}")
                return cached_doc

        # Fetch from database
        try:
            response = (
                self.client.table("documents").select("*").eq("id", document_id).single().execute()
            )

            if response.data:
                # Cache the result
                await document_metadata_cache.async_set(cache_key, response.data)
                return response.data
            return None

        except Exception as e:
            logger.error(f"Error fetching document {document_id}: {e}")
            return None

    async def get_document_by_source(
        self, source: str, use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get document by source path with optional caching.

        Args:
            source: Document source path
            use_cache: Whether to use cache (default: True)

        Returns:
            Document data or None if not found
        """
        cache_key = f"doc_source:{source}"

        # Try cache first
        if use_cache:
            cached_doc = await document_metadata_cache.async_get(cache_key)
            if cached_doc is not None:
                logger.debug(f"Cache hit for document source: {source}")
                return cached_doc

        # Fetch from database
        try:
            response = (
                self.client.table("documents").select("*").eq("source", source).single().execute()
            )

            if response.data:
                await document_metadata_cache.async_set(cache_key, response.data)
                return response.data
            return None

        except Exception as e:
            logger.error(f"Error fetching document by source {source}: {e}")
            return None

    async def similarity_search_cached(
        self,
        query_embedding: List[float],
        limit: int = 10,
        cache_ttl: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Cached vector similarity search.

        Results are cached for a short period to handle repeated queries.
        Useful for users refining their questions.

        Args:
            query_embedding: Query vector (1536 dimensions)
            limit: Maximum number of results
            cache_ttl: Cache time-to-live in seconds (default: 60)

        Returns:
            List of matching chunks with similarity scores
        """
        # Generate cache key from embedding (first 8 values + limit)
        cache_key = f"sim_search:{generate_cache_key(query_embedding[:8], limit=limit)}"

        # Try cache first
        cached_result = await query_result_cache.async_get(cache_key)
        if cached_result is not None:
            logger.debug("Cache hit for similarity search")
            return cached_result

        # Execute search
        result = await self.similarity_search(query_embedding, limit)

        # Cache the result
        await query_result_cache.async_set(cache_key, result, cache_ttl)

        return result

    async def execute_rpc(self, function_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Execute a Supabase RPC function.

        Args:
            function_name: Name of the PostgreSQL function
            params: Parameters to pass to the function

        Returns:
            Function result or None on error
        """
        try:
            response = self.client.rpc(function_name, params).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error executing RPC {function_name}: {e}")
            return None

    def invalidate_document_cache(self, document_id: str) -> None:
        """
        Invalidate cache for a specific document.

        Call this after document updates/deletes.

        Args:
            document_id: Document UUID to invalidate
        """
        cache_key = f"doc:{document_id}"
        document_metadata_cache.delete(cache_key)
        logger.debug(f"Invalidated cache for document: {document_id}")

    def clear_all_caches(self) -> None:
        """Clear all caches. Use after bulk operations."""
        document_metadata_cache.clear()
        query_result_cache.clear()
        logger.info("Cleared all Supabase client caches")
