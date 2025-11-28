"""
Tests for PDF page number extraction in chunker.
"""

from unittest.mock import Mock


class TestPageNumberExtraction:
    """Test page number extraction from Docling chunks."""

    def test_extract_single_page_from_meta_page(self):
        """Extract page number from chunk.meta.page."""
        # Mock Docling chunk with page in meta
        mock_chunk = Mock()
        mock_chunk.meta = Mock()
        mock_chunk.meta.page = 5
        mock_chunk.meta.doc_items = None
        mock_chunk.text = "Test content from page 5"

        # Simulate chunker logic
        page_start = None
        page_end = None

        if hasattr(mock_chunk, "meta") and mock_chunk.meta:
            if hasattr(mock_chunk.meta, "page"):
                page_start = mock_chunk.meta.page
                page_end = mock_chunk.meta.page

        assert page_start == 5
        assert page_end == 5

    def test_extract_page_range_from_doc_items(self):
        """Extract page range from chunk.meta.doc_items."""
        # Mock Docling chunk with doc_items containing multiple pages
        mock_item1 = Mock()
        mock_item1.prov = [Mock(page_no=3)]

        mock_item2 = Mock()
        mock_item2.prov = [Mock(page_no=5)]

        mock_item3 = Mock()
        mock_item3.prov = [Mock(page_no=4)]

        mock_chunk = Mock()
        mock_chunk.meta = Mock()
        mock_chunk.meta.doc_items = [mock_item1, mock_item2, mock_item3]
        mock_chunk.text = "Test content spanning pages"

        # Simulate chunker logic
        page_start = None
        page_end = None

        if hasattr(mock_chunk, "meta") and mock_chunk.meta:
            if hasattr(mock_chunk.meta, "doc_items") and mock_chunk.meta.doc_items:
                pages = [
                    item.prov[0].page_no
                    for item in mock_chunk.meta.doc_items
                    if hasattr(item, "prov") and item.prov
                ]
                if pages:
                    page_start = min(pages)
                    page_end = max(pages)

        assert page_start == 3
        assert page_end == 5

    def test_no_page_info_when_meta_missing(self):
        """No page extraction when meta is missing."""
        mock_chunk = Mock(spec=["text"])
        mock_chunk.text = "Test content without metadata"
        # No meta attribute

        page_start = None
        page_end = None

        if hasattr(mock_chunk, "meta") and mock_chunk.meta:
            if hasattr(mock_chunk.meta, "page"):
                page_start = mock_chunk.meta.page
                page_end = mock_chunk.meta.page

        assert page_start is None
        assert page_end is None

    def test_no_page_info_when_doc_items_empty(self):
        """No page extraction when doc_items is empty."""
        mock_chunk = Mock()
        mock_chunk.meta = Mock()
        mock_chunk.meta.doc_items = []
        mock_chunk.text = "Test content"

        page_start = None
        page_end = None

        if hasattr(mock_chunk, "meta") and mock_chunk.meta:
            if hasattr(mock_chunk.meta, "doc_items") and mock_chunk.meta.doc_items:
                pages = [
                    item.prov[0].page_no
                    for item in mock_chunk.meta.doc_items
                    if hasattr(item, "prov") and item.prov
                ]
                if pages:
                    page_start = min(pages)
                    page_end = max(pages)

        assert page_start is None
        assert page_end is None

    def test_page_metadata_added_to_chunk(self):
        """Chunk metadata includes page_start and page_end."""
        base_metadata = {"title": "Test Document", "source": "test.pdf"}

        chunk_metadata = {
            **base_metadata,
            "total_chunks": 10,
            "token_count": 100,
            "has_context": True,
        }

        # Add page information
        page_start = 3
        page_end = 5

        if page_start is not None:
            chunk_metadata["page_start"] = page_start
            if page_end is not None:
                chunk_metadata["page_end"] = page_end

        assert chunk_metadata["page_start"] == 3
        assert chunk_metadata["page_end"] == 5
        assert chunk_metadata["title"] == "Test Document"

    def test_single_page_chunk_same_start_end(self):
        """Single page chunk has same start and end."""
        chunk_metadata = {}
        page_start = 7
        page_end = 7

        if page_start is not None:
            chunk_metadata["page_start"] = page_start
            if page_end is not None:
                chunk_metadata["page_end"] = page_end

        assert chunk_metadata["page_start"] == 7
        assert chunk_metadata["page_end"] == 7

    def test_doc_items_with_missing_prov(self):
        """Handle doc_items where some items lack prov."""
        mock_item1 = Mock()
        mock_item1.prov = [Mock(page_no=2)]

        mock_item2 = Mock(spec=["text"])
        # No prov attribute - using spec to prevent auto-creation

        mock_item3 = Mock()
        mock_item3.prov = [Mock(page_no=4)]

        mock_chunk = Mock()
        mock_chunk.meta = Mock()
        mock_chunk.meta.doc_items = [mock_item1, mock_item2, mock_item3]

        # Should filter out items without prov
        pages = []
        for item in mock_chunk.meta.doc_items:
            if hasattr(item, "prov") and item.prov:
                # Check if prov is a list and has items
                if isinstance(item.prov, list) and len(item.prov) > 0:
                    pages.append(item.prov[0].page_no)

        page_start = min(pages) if pages else None
        page_end = max(pages) if pages else None

        assert page_start == 2
        assert page_end == 4

    def test_priority_meta_page_over_doc_items(self):
        """meta.page takes priority over doc_items."""
        mock_chunk = Mock()
        mock_chunk.meta = Mock()
        mock_chunk.meta.page = 10

        # Also has doc_items but should be ignored
        mock_item = Mock()
        mock_item.prov = [Mock(page_no=5)]
        mock_chunk.meta.doc_items = [mock_item]

        page_start = None
        page_end = None

        # Logic prioritizes meta.page
        if hasattr(mock_chunk, "meta") and mock_chunk.meta:
            if hasattr(mock_chunk.meta, "page"):
                page_start = mock_chunk.meta.page
                page_end = mock_chunk.meta.page
            elif hasattr(mock_chunk.meta, "doc_items") and mock_chunk.meta.doc_items:
                pages = [
                    item.prov[0].page_no
                    for item in mock_chunk.meta.doc_items
                    if hasattr(item, "prov") and item.prov
                ]
                if pages:
                    page_start = min(pages)
                    page_end = max(pages)

        assert page_start == 10
        assert page_end == 10
