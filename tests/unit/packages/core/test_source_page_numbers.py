"""
Tests for page number handling in source objects (agent.py).
"""


class TestSourcePageNumberFormatting:
    """Test source object construction with page fields."""

    def test_source_with_single_page(self):
        """Source object for single page chunk."""
        # Mock database row
        row = {
            "document_title": "Test Document",
            "document_source": "data/processed/test.pdf",
            "similarity": 0.95,
            "metadata": {"page_start": 5, "page_end": 5},
        }

        # Extract fields
        doc_title = row["document_title"]
        doc_source = row["document_source"]
        similarity = row["similarity"]
        chunk_metadata = row.get("metadata", {})

        page_start = chunk_metadata.get("page_start") if isinstance(chunk_metadata, dict) else None
        page_end = chunk_metadata.get("page_end") if isinstance(chunk_metadata, dict) else None

        # Build source object
        source_obj = {"title": doc_title, "path": doc_source, "similarity": similarity}

        if page_start is not None:
            source_obj["page_number"] = page_start
            if page_end is not None and page_end != page_start:
                source_obj["page_range"] = f"p. {page_start}-{page_end}"
            else:
                source_obj["page_range"] = f"p. {page_start}"

        assert source_obj["page_number"] == 5
        assert source_obj["page_range"] == "p. 5"
        assert source_obj["similarity"] == 0.95

    def test_source_with_page_range(self):
        """Source object for multi-page chunk."""
        row = {
            "document_title": "Multi-Page Doc",
            "document_source": "data/raw/report.pdf",
            "similarity": 0.88,
            "metadata": {"page_start": 3, "page_end": 7},
        }

        chunk_metadata = row.get("metadata", {})
        page_start = chunk_metadata.get("page_start")
        page_end = chunk_metadata.get("page_end")

        source_obj = {
            "title": row["document_title"],
            "path": row["document_source"],
            "similarity": row["similarity"],
        }

        if page_start is not None:
            source_obj["page_number"] = page_start
            if page_end is not None and page_end != page_start:
                source_obj["page_range"] = f"p. {page_start}-{page_end}"
            else:
                source_obj["page_range"] = f"p. {page_start}"

        assert source_obj["page_number"] == 3
        assert source_obj["page_range"] == "p. 3-7"

    def test_source_without_page_info(self):
        """Source object without page metadata (e.g., markdown file)."""
        row = {
            "document_title": "Markdown Doc",
            "document_source": "data/processed/doc.md",
            "similarity": 0.92,
            "metadata": {},
        }

        chunk_metadata = row.get("metadata", {})
        page_start = chunk_metadata.get("page_start") if isinstance(chunk_metadata, dict) else None
        page_end = chunk_metadata.get("page_end") if isinstance(chunk_metadata, dict) else None

        source_obj = {
            "title": row["document_title"],
            "path": row["document_source"],
            "similarity": row["similarity"],
        }

        if page_start is not None:
            source_obj["page_number"] = page_start
            if page_end is not None and page_end != page_start:
                source_obj["page_range"] = f"p. {page_start}-{page_end}"
            else:
                source_obj["page_range"] = f"p. {page_start}"

        # Should not have page fields
        assert "page_number" not in source_obj
        assert "page_range" not in source_obj

    def test_source_with_url_and_pages(self):
        """Source object with both URL and page info (scraped PDF)."""
        row = {
            "document_title": "Web PDF",
            "document_source": "data/processed/scraped/doc.pdf",
            "similarity": 0.85,
            "document_metadata": {"url": "https://example.com/doc.pdf"},
            "metadata": {"page_start": 10, "page_end": 12},
        }

        doc_metadata = row.get("document_metadata", {})
        chunk_metadata = row.get("metadata", {})

        original_url = doc_metadata.get("url") if isinstance(doc_metadata, dict) else None
        page_start = chunk_metadata.get("page_start") if isinstance(chunk_metadata, dict) else None
        page_end = chunk_metadata.get("page_end") if isinstance(chunk_metadata, dict) else None

        source_obj = {
            "title": row["document_title"],
            "path": row["document_source"],
            "similarity": row["similarity"],
        }

        if page_start is not None:
            source_obj["page_number"] = page_start
            if page_end is not None and page_end != page_start:
                source_obj["page_range"] = f"p. {page_start}-{page_end}"
            else:
                source_obj["page_range"] = f"p. {page_start}"

        if original_url:
            source_obj["url"] = original_url

        assert source_obj["page_number"] == 10
        assert source_obj["page_range"] == "p. 10-12"
        assert source_obj["url"] == "https://example.com/doc.pdf"

    def test_source_with_invalid_metadata_type(self):
        """Handle non-dict metadata gracefully."""
        row = {
            "document_title": "Test",
            "document_source": "test.pdf",
            "similarity": 0.9,
            "metadata": "invalid",  # Not a dict
        }

        chunk_metadata = row.get("metadata", {})
        page_start = chunk_metadata.get("page_start") if isinstance(chunk_metadata, dict) else None

        source_obj = {
            "title": row["document_title"],
            "path": row["document_source"],
            "similarity": row["similarity"],
        }

        if page_start is not None:
            source_obj["page_number"] = page_start

        # Should not crash, just skip page fields
        assert "page_number" not in source_obj

    def test_source_with_page_start_only(self):
        """Handle case where only page_start exists."""
        row = {
            "document_title": "Test",
            "document_source": "test.pdf",
            "similarity": 0.9,
            "metadata": {
                "page_start": 8
                # No page_end
            },
        }

        chunk_metadata = row.get("metadata", {})
        page_start = chunk_metadata.get("page_start")
        page_end = chunk_metadata.get("page_end")

        source_obj = {
            "title": row["document_title"],
            "path": row["document_source"],
            "similarity": row["similarity"],
        }

        if page_start is not None:
            source_obj["page_number"] = page_start
            if page_end is not None and page_end != page_start:
                source_obj["page_range"] = f"p. {page_start}-{page_end}"
            else:
                source_obj["page_range"] = f"p. {page_start}"

        assert source_obj["page_number"] == 8
        assert source_obj["page_range"] == "p. 8"

    def test_page_number_zero_indexed(self):
        """Handle zero-indexed page numbers (if applicable)."""
        row = {
            "document_title": "Test",
            "document_source": "test.pdf",
            "similarity": 0.9,
            "metadata": {"page_start": 0, "page_end": 0},
        }

        chunk_metadata = row.get("metadata", {})
        page_start = chunk_metadata.get("page_start")
        page_end = chunk_metadata.get("page_end")

        source_obj = {
            "title": row["document_title"],
            "path": row["document_source"],
            "similarity": row["similarity"],
        }

        # Page 0 is valid (some systems are zero-indexed)
        if page_start is not None:
            source_obj["page_number"] = page_start
            if page_end is not None and page_end != page_start:
                source_obj["page_range"] = f"p. {page_start}-{page_end}"
            else:
                source_obj["page_range"] = f"p. {page_start}"

        assert source_obj["page_number"] == 0
        assert source_obj["page_range"] == "p. 0"
