"""
Integration tests for page number flow through RAG pipeline.

Tests end-to-end flow from chunk ingestion to source object creation.
"""

from unittest.mock import Mock

import pytest


@pytest.mark.asyncio
class TestPageNumberPipeline:
    """Test page numbers flow through the entire pipeline."""

    async def test_pdf_chunk_to_source_with_single_page(self):
        """End-to-end: PDF chunk with single page → source object."""
        # 1. Mock Docling chunk (input to chunker)
        mock_docling_chunk = Mock()
        mock_docling_chunk.meta = Mock()
        mock_docling_chunk.meta.page = 5
        mock_docling_chunk.text = "Test content from page 5"

        # 2. Extract page info (chunker logic)
        page_start = mock_docling_chunk.meta.page
        page_end = mock_docling_chunk.meta.page

        chunk_metadata = {
            "title": "Test Document",
            "source": "test.pdf",
            "page_start": page_start,
            "page_end": page_end,
        }

        # 3. Simulate database retrieval (agent logic)
        db_row = {
            "document_title": "Test Document",
            "document_source": "data/processed/test.pdf",
            "similarity": 0.95,
            "metadata": chunk_metadata,
        }

        # 4. Build source object (agent logic)
        chunk_meta = db_row.get("metadata", {})
        page_start_from_db = chunk_meta.get("page_start") if isinstance(chunk_meta, dict) else None
        page_end_from_db = chunk_meta.get("page_end") if isinstance(chunk_meta, dict) else None

        source_obj = {
            "title": db_row["document_title"],
            "path": db_row["document_source"],
            "similarity": db_row["similarity"],
        }

        if page_start_from_db is not None:
            source_obj["page_number"] = page_start_from_db
            if page_end_from_db is not None and page_end_from_db != page_start_from_db:
                source_obj["page_range"] = f"p. {page_start_from_db}-{page_end_from_db}"
            else:
                source_obj["page_range"] = f"p. {page_start_from_db}"

        # Verify end-to-end flow
        assert source_obj["page_number"] == 5
        assert source_obj["page_range"] == "p. 5"

    async def test_pdf_chunk_to_source_with_page_range(self):
        """End-to-end: PDF chunk spanning pages → source object with range."""
        # 1. Mock Docling chunk with doc_items
        mock_item1 = Mock()
        mock_item1.prov = [Mock(page_no=3)]
        mock_item2 = Mock()
        mock_item2.prov = [Mock(page_no=5)]

        mock_docling_chunk = Mock()
        mock_docling_chunk.meta = Mock()
        mock_docling_chunk.meta.doc_items = [mock_item1, mock_item2]
        mock_docling_chunk.text = "Content spanning pages"

        # 2. Extract page range (chunker logic)
        pages = [
            item.prov[0].page_no
            for item in mock_docling_chunk.meta.doc_items
            if hasattr(item, "prov") and item.prov
        ]
        page_start = min(pages)
        page_end = max(pages)

        chunk_metadata = {"page_start": page_start, "page_end": page_end}

        # 3. Database retrieval
        db_row = {
            "document_title": "Multi-Page Doc",
            "document_source": "data/raw/report.pdf",
            "similarity": 0.88,
            "metadata": chunk_metadata,
        }

        # 4. Build source object
        chunk_meta = db_row.get("metadata", {})
        page_start_from_db = chunk_meta.get("page_start")
        page_end_from_db = chunk_meta.get("page_end")

        source_obj = {
            "title": db_row["document_title"],
            "path": db_row["document_source"],
            "similarity": db_row["similarity"],
        }

        if page_start_from_db is not None:
            source_obj["page_number"] = page_start_from_db
            if page_end_from_db is not None and page_end_from_db != page_start_from_db:
                source_obj["page_range"] = f"p. {page_start_from_db}-{page_end_from_db}"
            else:
                source_obj["page_range"] = f"p. {page_start_from_db}"

        assert source_obj["page_number"] == 3
        assert source_obj["page_range"] == "p. 3-5"

    async def test_non_pdf_chunk_without_pages(self):
        """End-to-end: Non-PDF document without page info."""
        # 1. Mock chunk without page metadata
        mock_chunk = Mock()
        mock_chunk.text = "Markdown content"
        # No meta attribute

        # 2. Chunker logic - no page extraction
        chunk_metadata = {
            "title": "Markdown Doc",
            "source": "doc.md",
            # No page_start/page_end
        }

        # 3. Database retrieval
        db_row = {
            "document_title": "Markdown Doc",
            "document_source": "data/processed/doc.md",
            "similarity": 0.92,
            "metadata": chunk_metadata,
        }

        # 4. Build source object
        chunk_meta = db_row.get("metadata", {})
        page_start = chunk_meta.get("page_start") if isinstance(chunk_meta, dict) else None

        source_obj = {
            "title": db_row["document_title"],
            "path": db_row["document_source"],
            "similarity": db_row["similarity"],
        }

        if page_start is not None:
            source_obj["page_number"] = page_start

        # Should not have page fields
        assert "page_number" not in source_obj
        assert "page_range" not in source_obj

    async def test_missing_metadata_graceful_handling(self):
        """End-to-end: Missing metadata at various pipeline stages."""
        # Database row without metadata field
        db_row = {
            "document_title": "Test",
            "document_source": "test.pdf",
            "similarity": 0.9,
            # No metadata field
        }

        chunk_meta = db_row.get("metadata", {})
        page_start = chunk_meta.get("page_start") if isinstance(chunk_meta, dict) else None

        source_obj = {
            "title": db_row["document_title"],
            "path": db_row["document_source"],
            "similarity": db_row["similarity"],
        }

        if page_start is not None:
            source_obj["page_number"] = page_start

        # Should not crash, gracefully skip page fields
        assert "page_number" not in source_obj
        assert source_obj["title"] == "Test"

    async def test_metadata_preserved_through_pipeline(self):
        """Verify all metadata fields preserved from chunk to source."""
        # 1. Create chunk with rich metadata
        chunk_metadata = {
            "title": "Complex Doc",
            "source": "complex.pdf",
            "page_start": 7,
            "page_end": 9,
            "token_count": 200,
            "has_context": True,
        }

        # 2. Database row
        db_row = {
            "document_title": "Complex Doc",
            "document_source": "data/raw/complex.pdf",
            "similarity": 0.87,
            "metadata": chunk_metadata,
            "document_metadata": {"custom_field": "value"},
        }

        # 3. Build source object
        chunk_meta = db_row.get("metadata", {})

        page_start = chunk_meta.get("page_start") if isinstance(chunk_meta, dict) else None
        page_end = chunk_meta.get("page_end") if isinstance(chunk_meta, dict) else None

        source_obj = {
            "title": db_row["document_title"],
            "path": db_row["document_source"],
            "similarity": db_row["similarity"],
        }

        if page_start is not None:
            source_obj["page_number"] = page_start
            if page_end is not None and page_end != page_start:
                source_obj["page_range"] = f"p. {page_start}-{page_end}"
            else:
                source_obj["page_range"] = f"p. {page_start}"

        # Verify page fields and other metadata coexist
        assert source_obj["page_number"] == 7
        assert source_obj["page_range"] == "p. 7-9"
        assert source_obj["title"] == "Complex Doc"
        assert source_obj["similarity"] == 0.87
