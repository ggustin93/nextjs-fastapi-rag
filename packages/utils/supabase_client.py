"""
Supabase REST API client for database operations.
Uses Supabase Python SDK (HTTPS) to work around network restrictions.
"""

import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import Client, create_client

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
        self, query_embedding: List[float], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search via Supabase RPC function.

        Args:
            query_embedding: Query vector (1536 dimensions)
            limit: Maximum number of results
            threshold: Minimum similarity score (0-1)

        Returns:
            List of matching chunks with similarity scores
        """
        try:
            # PostgreSQL vector format
            embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

            response = self.client.rpc(
                "match_chunks", {"query_embedding": embedding_str, "match_count": limit}
            ).execute()

            return response.data

        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            raise

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
