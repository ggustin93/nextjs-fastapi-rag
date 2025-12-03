"""
Docling HybridChunker implementation for intelligent document splitting.

This module uses Docling's built-in HybridChunker which combines:
- Token-aware chunking (uses actual tokenizer)
- Document structure preservation (headings, sections, tables)
- Semantic boundary respect (paragraphs, code blocks)
- Contextualized output (chunks include heading hierarchy)

Benefits over custom chunking:
- Fast (no LLM API calls)
- Token-precise (not character-based estimates)
- Better for RAG (chunks include document context)
- Battle-tested (maintained by Docling team)
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from docling.chunking import HybridChunker
from docling_core.types.doc import DocItemLabel, DoclingDocument
from dotenv import load_dotenv
from transformers import AutoTokenizer

from packages.config import settings as app_settings

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for chunking with defaults from centralized settings."""

    chunk_size: int | None = None
    chunk_overlap: int | None = None
    max_chunk_size: int | None = None
    min_chunk_size: int | None = None
    max_tokens: int | None = None

    def __post_init__(self):
        """Apply defaults from settings and validate configuration."""
        # Apply defaults from centralized settings
        if self.chunk_size is None:
            self.chunk_size = app_settings.chunking.chunk_size
        if self.chunk_overlap is None:
            self.chunk_overlap = app_settings.chunking.chunk_overlap
        if self.max_chunk_size is None:
            self.max_chunk_size = app_settings.chunking.max_chunk_size
        if self.min_chunk_size is None:
            self.min_chunk_size = app_settings.chunking.min_chunk_size
        if self.max_tokens is None:
            self.max_tokens = app_settings.chunking.max_tokens

        # Validate
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        if self.min_chunk_size <= 0:
            raise ValueError("Minimum chunk size must be positive")


# TOC element labels from Docling (primary detection)
TOC_LABELS = {DocItemLabel.DOCUMENT_INDEX}

# Fallback TOC detection patterns for French documents (when Docling labels unavailable)
TOC_HEADER_PATTERNS = [
    r"table\s*(des\s*)?mati[èe]res?",  # "Table des matières" anywhere
    r"^\s*sommaire\s*$",  # "Sommaire" as full line
    r"^\s*contents?\s*$",  # "Contents" as full line
]

TOC_LINE_PATTERNS = [
    r"\.{3,}\s*\d+",  # Dot leaders: "Section name.......12"
    r"^[A-Z\s\.]+\s+\d+\s*$",  # "CHAPTER NAME    12"
    r"^\d+\.\s+.{5,50}\s+\d+\s*$",  # "1.2 Section name   15"
]


def is_toc_from_docling(chunk_meta) -> bool:
    """
    Detect TOC using Docling's native element labels.

    This is the preferred detection method as it uses Docling's
    document structure analysis rather than regex patterns.

    Args:
        chunk_meta: Docling chunk metadata containing doc_items

    Returns:
        True if any doc_item has a TOC-related label
    """
    if not chunk_meta or not hasattr(chunk_meta, "doc_items"):
        return False

    for item in chunk_meta.doc_items or []:
        if hasattr(item, "label") and item.label in TOC_LABELS:
            return True
    return False


def is_toc_chunk(content: str) -> bool:
    """
    Detect if chunk is likely a Table of Contents entry.

    Identifies TOC patterns based on:
    - TOC header keywords (sommaire, table des matières)
    - Dot leaders (........) with page numbers
    - Lines with trailing page numbers
    - Section number + title + page number patterns

    Args:
        content: Chunk text content

    Returns:
        True if chunk appears to be TOC content
    """
    if not content or len(content.strip()) < 10:
        return False

    # Check for TOC headers anywhere in content
    for pattern in TOC_HEADER_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True

    lines = content.strip().split("\n")

    # Count lines with TOC-like patterns
    toc_indicator_lines = 0
    for line in lines:
        stripped = line.strip()
        # Pattern: text followed by whitespace/dots and 1-3 digit number at end
        if re.search(r"[\s\.]+\d{1,3}\s*$", stripped):
            toc_indicator_lines += 1
        # Check for dot leaders
        if re.search(r"\.{3,}", stripped):
            toc_indicator_lines += 1

    # If more than 40% of lines have TOC indicators, likely TOC
    if len(lines) > 0 and toc_indicator_lines / len(lines) > 0.4:
        return True

    # Check against known TOC line patterns
    for pattern in TOC_LINE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            return True

    return False


@dataclass
class DocumentChunk:
    """Represents a document chunk with optional embedding."""

    content: str
    index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any]
    token_count: Optional[int] = None
    embedding: Optional[List[float]] = None  # For embedder compatibility
    is_toc: bool = False  # True if chunk is Table of Contents content

    def __post_init__(self):
        """Calculate token count and detect TOC if not provided."""
        if self.token_count is None:
            # Rough estimation: ~4 characters per token
            self.token_count = len(self.content) // 4
        # Auto-detect TOC if not explicitly set
        if not self.is_toc:
            self.is_toc = is_toc_chunk(self.content)


class DoclingHybridChunker:
    """
    Docling HybridChunker wrapper for intelligent document splitting.

    This chunker uses Docling's built-in HybridChunker which:
    - Respects document structure (sections, paragraphs, tables)
    - Is token-aware (fits embedding model limits)
    - Preserves semantic coherence
    - Includes heading context in chunks
    """

    def __init__(self, config: ChunkingConfig):
        """
        Initialize chunker.

        Args:
            config: Chunking configuration
        """
        self.config = config

        # Initialize tokenizer for token-aware chunking (from settings)
        model_id = app_settings.embedding.tokenizer_model
        logger.info(f"Initializing tokenizer: {model_id}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)

        # Create HybridChunker
        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
            max_tokens=config.max_tokens,
            merge_peers=True,  # Merge small adjacent chunks
        )

        logger.info(f"HybridChunker initialized (max_tokens={config.max_tokens})")

    async def chunk_document(
        self,
        content: str,
        title: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        docling_doc: Optional[DoclingDocument] = None,
    ) -> List[DocumentChunk]:
        """
        Chunk a document using Docling's HybridChunker.

        Args:
            content: Document content (markdown format)
            title: Document title
            source: Document source
            metadata: Additional metadata
            docling_doc: Optional pre-converted DoclingDocument (for efficiency)

        Returns:
            List of document chunks with contextualized content
        """
        if not content.strip():
            return []

        base_metadata = {
            "title": title,
            "source": source,
            "chunk_method": "hybrid",
            **(metadata or {}),
        }

        # If we don't have a DoclingDocument, we need to create one from markdown
        if docling_doc is None:
            # For markdown content, we need to convert it to DoclingDocument
            # This is a simplified version - in practice, content comes from
            # Docling's document converter in the ingestion pipeline
            logger.warning("No DoclingDocument provided, using simple chunking fallback")
            return self._simple_fallback_chunk(content, base_metadata)

        try:
            # Use HybridChunker to chunk the DoclingDocument
            chunk_iter = self.chunker.chunk(dl_doc=docling_doc)
            chunks = list(chunk_iter)

            # Convert Docling chunks to DocumentChunk objects
            document_chunks = []
            current_pos = 0

            for i, chunk in enumerate(chunks):
                # Get contextualized text (includes heading hierarchy)
                contextualized_text = self.chunker.contextualize(chunk=chunk)

                # Count actual tokens
                token_count = len(self.tokenizer.encode(contextualized_text))

                # Extract page information from chunk (for PDFs)
                page_start = None
                page_end = None

                # Docling chunks have page information in their metadata
                if hasattr(chunk, "meta") and chunk.meta:
                    # Try to get page from meta.page or meta.doc_items
                    if hasattr(chunk.meta, "page"):
                        page_start = chunk.meta.page
                        page_end = chunk.meta.page
                    elif hasattr(chunk.meta, "doc_items") and chunk.meta.doc_items:
                        # Get page range from doc_items (list of document items in chunk)
                        pages = [
                            item.prov[0].page_no
                            for item in chunk.meta.doc_items
                            if hasattr(item, "prov") and item.prov
                        ]
                        if pages:
                            page_start = min(pages)
                            page_end = max(pages)

                # Create chunk metadata
                chunk_metadata = {
                    **base_metadata,
                    "total_chunks": len(chunks),
                    "token_count": token_count,
                    "has_context": True,  # Flag indicating contextualized chunk
                }

                # Add page information if available
                if page_start is not None:
                    chunk_metadata["page_start"] = page_start
                    if page_end is not None:
                        chunk_metadata["page_end"] = page_end

                # Detect TOC using Docling labels (primary) or content patterns (fallback)
                chunk_is_toc = False
                if hasattr(chunk, "meta") and chunk.meta:
                    chunk_is_toc = is_toc_from_docling(chunk.meta)

                # Estimate character positions
                start_char = current_pos
                end_char = start_char + len(contextualized_text)

                document_chunks.append(
                    DocumentChunk(
                        content=contextualized_text.strip(),
                        index=i,
                        start_char=start_char,
                        end_char=end_char,
                        metadata=chunk_metadata,
                        token_count=token_count,
                        is_toc=chunk_is_toc,  # Set from Docling label detection
                    )
                )

                current_pos = end_char

            logger.info(f"Created {len(document_chunks)} chunks using HybridChunker")
            return document_chunks

        except Exception as e:
            logger.error(f"HybridChunker failed: {e}, falling back to simple chunking")
            return self._simple_fallback_chunk(content, base_metadata)

    def _simple_fallback_chunk(
        self, content: str, base_metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Simple fallback chunking when HybridChunker can't be used.

        This is used when:
        - No DoclingDocument is provided
        - HybridChunker fails

        Args:
            content: Content to chunk
            base_metadata: Base metadata for chunks

        Returns:
            List of document chunks
        """
        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap

        # Simple sliding window approach
        start = 0
        chunk_index = 0

        while start < len(content):
            end = start + chunk_size

            if end >= len(content):
                # Last chunk
                chunk_text = content[start:]
            else:
                # Try to end at sentence boundary
                chunk_end = end
                for i in range(end, max(start + self.config.min_chunk_size, end - 200), -1):
                    if i < len(content) and content[i] in ".!?\n":
                        chunk_end = i + 1
                        break
                chunk_text = content[start:chunk_end]
                end = chunk_end

            if chunk_text.strip():
                token_count = len(self.tokenizer.encode(chunk_text))

                chunks.append(
                    DocumentChunk(
                        content=chunk_text.strip(),
                        index=chunk_index,
                        start_char=start,
                        end_char=end,
                        metadata={
                            **base_metadata,
                            "chunk_method": "simple_fallback",
                            "total_chunks": -1,  # Will update after
                        },
                        token_count=token_count,
                    )
                )

                chunk_index += 1

            # Move forward with overlap
            start = end - overlap

        # Update total chunks
        for chunk in chunks:
            chunk.metadata["total_chunks"] = len(chunks)

        logger.info(f"Created {len(chunks)} chunks using simple fallback")
        return chunks


# Factory function
def create_chunker(config: ChunkingConfig) -> DoclingHybridChunker:
    """Create chunker instance."""
    return DoclingHybridChunker(config)
