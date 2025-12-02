"""Tests for search_knowledge_base tool."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import RunContext

from packages.core.tools.search_knowledge_base import search_knowledge_base
from packages.core.types import RAGContext


@pytest.mark.asyncio
async def test_search_knowledge_base_success():
    """Search tool returns formatted results."""
    # Mock RAG context
    mock_rag_ctx = MagicMock(spec=RAGContext)
    mock_rag_ctx.embedder = MagicMock()
    mock_rag_ctx.embedder.embed_query = AsyncMock(return_value=[0.1] * 1536)
    mock_rag_ctx.db_client = MagicMock()
    mock_rag_ctx.db_client.hybrid_search = AsyncMock(
        return_value=[
            {
                "similarity": 0.9,
                "content": "Test content",
                "document_title": "Test Doc",
                "document_source": "test.pdf",
                "document_metadata": {},
                "metadata": {"page_start": 1},
            }
        ]
    )

    # Mock RunContext
    mock_ctx = MagicMock(spec=RunContext)
    mock_ctx.deps = mock_rag_ctx

    result = await search_knowledge_base(mock_ctx, "test query")

    assert "Trouvé 1 résultats pertinents" in result
    assert "Test Doc" in result
    assert "Test content" in result
    assert "90%" in result  # similarity percentage


@pytest.mark.asyncio
async def test_search_knowledge_base_no_results():
    """Search tool handles no results gracefully."""
    mock_rag_ctx = MagicMock(spec=RAGContext)
    mock_rag_ctx.embedder = MagicMock()
    mock_rag_ctx.embedder.embed_query = AsyncMock(return_value=[0.1] * 1536)
    mock_rag_ctx.db_client = MagicMock()
    mock_rag_ctx.db_client.hybrid_search = AsyncMock(return_value=[])

    mock_ctx = MagicMock(spec=RunContext)
    mock_ctx.deps = mock_rag_ctx

    result = await search_knowledge_base(mock_ctx, "nonexistent")

    assert "HORS PÉRIMÈTRE" in result or "Aucune information" in result


@pytest.mark.asyncio
async def test_search_knowledge_base_error_handling():
    """Search tool handles errors gracefully."""
    mock_rag_ctx = MagicMock(spec=RAGContext)
    mock_rag_ctx.embedder = MagicMock()
    mock_rag_ctx.embedder.embed_query = AsyncMock(side_effect=Exception("Database error"))

    mock_ctx = MagicMock(spec=RunContext)
    mock_ctx.deps = mock_rag_ctx

    result = await search_knowledge_base(mock_ctx, "test")

    assert "error" in result.lower()
    assert "Database error" in result
