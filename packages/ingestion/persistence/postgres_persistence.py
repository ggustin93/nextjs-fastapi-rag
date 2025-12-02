"""
PostgreSQL persistence module.

Handles document and chunk storage to PostgreSQL database.
Supports both direct PostgreSQL connection and REST API access.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ..chunker import DocumentChunk

# Import database utilities (conditionally based on availability)
try:
    from ...utils.db_utils import db_pool
    from ...utils.supabase_client import SupabaseRestClient
except ImportError:
    # For testing or alternative import paths
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from packages.utils.db_utils import db_pool
    from packages.utils.supabase_client import SupabaseRestClient

logger = logging.getLogger(__name__)


class PostgresPersistence:
    """
    PostgreSQL database persistence handler.

    Handles:
    - Document insertion with metadata
    - Chunk storage with embeddings (pgvector format)
    - Database cleanup operations
    - Dual-mode access: Direct PostgreSQL or REST API
    """

    def __init__(
        self, use_rest_api: bool = False, rest_client: Optional[SupabaseRestClient] = None
    ):
        """
        Initialize persistence handler.

        Args:
            use_rest_api: Whether to use REST API instead of direct PostgreSQL
            rest_client: SupabaseRestClient instance (required if use_rest_api=True)
        """
        self.use_rest_api = use_rest_api
        self.rest_client = rest_client

    async def save_document(
        self,
        title: str,
        source: str,
        content: str,
        chunks: List[DocumentChunk],
        metadata: Dict[str, Any],
    ) -> str:
        """
        Save document and its chunks to PostgreSQL.

        Supports two storage modes:
        1. REST API (via Supabase client)
        2. Direct PostgreSQL (via asyncpg pool)

        Args:
            title: Document title
            source: Document source path
            content: Full document content
            chunks: List of document chunks with embeddings
            metadata: Document metadata dictionary

        Returns:
            Document ID (UUID as string)

        Raises:
            Exception: If database operation fails
        """
        if self.use_rest_api and self.rest_client:
            # Use REST API
            document_id = await self.rest_client.insert_document(
                title=title, source=source, content=content, metadata=metadata
            )

            # Insert chunks via REST API
            for i, chunk in enumerate(chunks):
                if hasattr(chunk, "embedding") and chunk.embedding:
                    await self.rest_client.insert_chunk(
                        document_id=document_id,
                        content=chunk.content,
                        embedding=chunk.embedding,
                        chunk_index=i,
                        metadata=chunk.metadata or {},
                        token_count=chunk.token_count,
                        is_toc=chunk.is_toc,
                    )

            return document_id
        else:
            # Use direct PostgreSQL connection
            async with db_pool.acquire() as conn:
                async with conn.transaction():
                    # Insert document
                    document_result = await conn.fetchrow(
                        """
                        INSERT INTO documents (title, source, content, metadata)
                        VALUES ($1, $2, $3, $4)
                        RETURNING id::text
                        """,
                        title,
                        source,
                        content,
                        json.dumps(metadata),
                    )

                    document_id = document_result["id"]

                    # Insert chunks with embeddings in pgvector format
                    for chunk in chunks:
                        # Convert embedding to PostgreSQL vector string format
                        # Format: '[1.0,2.0,3.0]' (no spaces after commas)
                        embedding_data = None
                        if hasattr(chunk, "embedding") and chunk.embedding:
                            embedding_data = "[" + ",".join(map(str, chunk.embedding)) + "]"

                        await conn.execute(
                            """
                            INSERT INTO chunks (document_id, content, embedding, chunk_index, metadata, token_count, is_toc)
                            VALUES ($1::uuid, $2, $3::vector, $4, $5, $6, $7)
                            """,
                            document_id,
                            chunk.content,
                            embedding_data,
                            chunk.index,
                            json.dumps(chunk.metadata),
                            chunk.token_count,
                            chunk.is_toc,
                        )

                    return document_id

    async def clean_database(self):
        """
        Clean existing data from databases.

        Removes all documents and chunks. Use with caution in production.

        Raises:
            Exception: If cleanup operation fails
        """
        logger.warning("Cleaning existing data from databases...")

        # Clean PostgreSQL
        if self.use_rest_api and self.rest_client:
            await self.rest_client.delete_all_documents()
            logger.info("Cleaned database via REST API")
        else:
            async with db_pool.acquire() as conn:
                async with conn.transaction():
                    # Delete in correct order (chunks first due to foreign key)
                    await conn.execute("DELETE FROM chunks")
                    await conn.execute("DELETE FROM documents")
            logger.info("Cleaned PostgreSQL database")
