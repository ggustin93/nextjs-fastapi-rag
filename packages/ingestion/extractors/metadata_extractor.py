"""
Metadata extraction module.

Extracts document metadata from various sources:
- YAML frontmatter (web scraped content)
- Markdown headers (# Title)
- File statistics (size, word count, line count)
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """
    Document metadata extractor.

    Extracts metadata from:
    - YAML frontmatter (for web scraped content with structured metadata)
    - Markdown headers (# Title format)
    - File properties (size, paths)
    - Content statistics (word count, line count)
    """

    def extract_title(self, content: str, file_path: str) -> str:
        """
        Extract title from document content or filename.

        Priority order:
        1. YAML frontmatter 'title' field
        2. First markdown header (# Title)
        3. Filename (fallback)

        Args:
            content: Document content
            file_path: Path to the document file

        Returns:
            Extracted title string
        """
        # Priority 1: Check YAML frontmatter for title (for scraped web content)
        if content.startswith("---"):
            try:
                import yaml

                end_marker = content.find("\n---\n", 4)
                if end_marker != -1:
                    frontmatter = content[4:end_marker]
                    yaml_metadata = yaml.safe_load(frontmatter)
                    if isinstance(yaml_metadata, dict) and "title" in yaml_metadata:
                        title = yaml_metadata["title"]
                        if title and isinstance(title, str) and title.strip():
                            return title.strip()
            except Exception as e:
                logger.debug(f"Could not extract title from YAML frontmatter: {e}")

        # Priority 2: Try to find markdown title
        lines = content.split("\n")
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()

        # Priority 3: Fallback to filename
        return os.path.splitext(os.path.basename(file_path))[0]

    def extract_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from document content.

        Extracts:
        - YAML frontmatter (all fields)
        - File statistics (size, line count, word count)
        - Ingestion timestamp

        Args:
            content: Document content
            file_path: Path to the document file

        Returns:
            Dictionary of metadata fields
        """
        metadata = {
            "file_path": file_path,
            "file_size": len(content),
            "ingestion_date": datetime.now().isoformat(),
        }

        # Try to extract YAML frontmatter
        if content.startswith("---"):
            try:
                import yaml

                end_marker = content.find("\n---\n", 4)
                if end_marker != -1:
                    frontmatter = content[4:end_marker]
                    yaml_metadata = yaml.safe_load(frontmatter)
                    if isinstance(yaml_metadata, dict):
                        metadata.update(yaml_metadata)
            except ImportError:
                logger.warning("PyYAML not installed, skipping frontmatter extraction")
            except Exception as e:
                logger.warning(f"Failed to parse frontmatter: {e}")

        # Extract some basic metadata from content
        lines = content.split("\n")
        metadata["line_count"] = len(lines)
        metadata["word_count"] = len(content.split())

        return metadata
