"""
Tests for chunking configuration and data structures.
"""

import pytest
from packages.ingestion.chunker import ChunkingConfig, DocumentChunk


class TestChunkingConfig:
    """Test ChunkingConfig validation."""

    def test_valid_config(self):
        """Valid configuration should work."""
        config = ChunkingConfig(chunk_size=500, chunk_overlap=100)
        assert config.chunk_size == 500
        assert config.chunk_overlap == 100

    def test_default_config(self):
        """Default configuration should have sensible values."""
        config = ChunkingConfig()
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.max_tokens == 512

    def test_overlap_must_be_less_than_size(self):
        """Overlap must be less than chunk size."""
        with pytest.raises(ValueError, match="overlap must be less than"):
            ChunkingConfig(chunk_size=100, chunk_overlap=200)

    def test_overlap_equal_to_size_raises(self):
        """Overlap equal to size should also raise."""
        with pytest.raises(ValueError, match="overlap must be less than"):
            ChunkingConfig(chunk_size=100, chunk_overlap=100)

    def test_min_chunk_size_must_be_positive(self):
        """Minimum chunk size must be positive."""
        with pytest.raises(ValueError, match="positive"):
            ChunkingConfig(min_chunk_size=0)


class TestDocumentChunk:
    """Test DocumentChunk data structure."""

    def test_basic_chunk_creation(self):
        """Create a basic chunk."""
        chunk = DocumentChunk(
            content="Test content",
            index=0,
            start_char=0,
            end_char=12,
            metadata={"title": "Test"}
        )
        assert chunk.content == "Test content"
        assert chunk.index == 0
        assert chunk.metadata["title"] == "Test"

    def test_token_count_estimation(self):
        """Token count is estimated if not provided."""
        content = "A" * 400  # 400 characters
        chunk = DocumentChunk(
            content=content,
            index=0,
            start_char=0,
            end_char=400,
            metadata={}
        )
        # Estimation: ~4 characters per token
        assert chunk.token_count == 100

    def test_explicit_token_count(self):
        """Explicit token count is used when provided."""
        chunk = DocumentChunk(
            content="Test",
            index=0,
            start_char=0,
            end_char=4,
            metadata={},
            token_count=50
        )
        assert chunk.token_count == 50

    def test_embedding_default_none(self):
        """Embedding should default to None."""
        chunk = DocumentChunk(
            content="Test",
            index=0,
            start_char=0,
            end_char=4,
            metadata={}
        )
        assert chunk.embedding is None
