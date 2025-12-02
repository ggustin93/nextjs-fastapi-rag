"""
Main ingestion script for processing documents into vector DB.
"""

import argparse
import asyncio
import glob
import logging
import os
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv

from .chunker import ChunkingConfig, create_chunker
from .embedder import create_embedder
from .extractors.metadata_extractor import MetadataExtractor
from .models import IngestionConfig, IngestionResult
from .persistence.postgres_persistence import PostgresPersistence
from .readers.document_reader import DocumentReader

# Import utilities
try:
    from ..utils.db_utils import close_database, initialize_database
    from ..utils.supabase_client import SupabaseRestClient
except ImportError:
    # For direct execution or testing
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from packages.utils.db_utils import close_database, initialize_database
    from packages.utils.supabase_client import SupabaseRestClient

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DocumentIngestionPipeline:
    """Pipeline for ingesting documents into vector DB."""

    def __init__(
        self,
        config: IngestionConfig,
        documents_folder: str = "documents",
        clean_before_ingest: bool = True,
        use_rest_api: bool = True,
    ):
        """
        Initialize ingestion pipeline.

        Args:
            config: Ingestion configuration
            documents_folder: Folder containing markdown documents
            clean_before_ingest: Whether to clean existing data before ingestion (default: True)
            use_rest_api: Whether to use REST API instead of direct PostgreSQL connection (default: True)
        """
        self.config = config

        # Security: Validate and normalize documents_folder path
        normalized_path = os.path.abspath(os.path.normpath(documents_folder))
        project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if not normalized_path.startswith(project_root):
            raise ValueError(f"Documents folder must be within project directory: {project_root}")
        self.documents_folder = normalized_path

        self.clean_before_ingest = clean_before_ingest
        self.use_rest_api = use_rest_api

        # Initialize components
        self.chunker_config = ChunkingConfig(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            max_chunk_size=config.max_chunk_size,
        )

        self.chunker = create_chunker(self.chunker_config)
        self.embedder = create_embedder()

        # Initialize delegated components (extracted modules)
        self.reader = DocumentReader()
        self.extractor = MetadataExtractor()
        self.rest_client = SupabaseRestClient() if use_rest_api else None
        self.persistence = PostgresPersistence(
            use_rest_api=use_rest_api, rest_client=self.rest_client
        )

        self._initialized = False

    async def initialize(self):
        """Initialize database connections."""
        if self._initialized:
            return

        logger.info("Initializing ingestion pipeline...")

        # Initialize database connections
        if self.use_rest_api:
            if self.rest_client:
                await self.rest_client.initialize()
                logger.info("Using Supabase REST API (HTTPS)")
        else:
            await initialize_database()
            logger.info("Using direct PostgreSQL connection")

        self._initialized = True
        logger.info("Ingestion pipeline initialized")

    async def close(self):
        """Close database connections."""
        if self._initialized:
            if self.use_rest_api and self.rest_client:
                await self.rest_client.close()
            else:
                await close_database()
            self._initialized = False

    async def ingest_documents(
        self, progress_callback: Optional[callable] = None
    ) -> List[IngestionResult]:
        """
        Ingest all documents from the documents folder.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            List of ingestion results
        """
        if not self._initialized:
            await self.initialize()

        # Clean existing data if requested using delegated persistence
        if self.clean_before_ingest:
            await self.persistence.clean_database()

        # Find all supported document files
        document_files = self._find_document_files()

        if not document_files:
            logger.warning(f"No supported document files found in {self.documents_folder}")
            return []

        logger.info(f"Found {len(document_files)} document files to process")

        results = []

        for i, file_path in enumerate(document_files):
            try:
                logger.info(f"Processing file {i + 1}/{len(document_files)}: {file_path}")

                result = await self._ingest_single_document(file_path)
                results.append(result)

                if progress_callback:
                    progress_callback(i + 1, len(document_files))

            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                results.append(
                    IngestionResult(
                        document_id="",
                        title=os.path.basename(file_path),
                        chunks_created=0,
                        processing_time_ms=0,
                        errors=[str(e)],
                    )
                )

        # Log summary
        total_chunks = sum(r.chunks_created for r in results)
        total_errors = sum(len(r.errors) for r in results)

        logger.info(
            f"Ingestion complete: {len(results)} documents, {total_chunks} chunks, {total_errors} errors"
        )

        return results

    async def _ingest_single_document(self, file_path: str) -> IngestionResult:
        """
        Ingest a single document.

        Args:
            file_path: Path to the document file

        Returns:
            Ingestion result
        """
        start_time = datetime.now()

        # Read document using delegated reader (returns tuple: content, docling_doc)
        document_content, docling_doc = self.reader.read(file_path)
        document_title = self.extractor.extract_title(document_content, file_path)
        document_source = os.path.relpath(file_path, self.documents_folder)

        # Extract metadata using delegated extractor
        document_metadata = self.extractor.extract_metadata(document_content, file_path)

        logger.info(f"Processing document: {document_title}")

        # Chunk the document - pass DoclingDocument for HybridChunker
        chunks = await self.chunker.chunk_document(
            content=document_content,
            title=document_title,
            source=document_source,
            metadata=document_metadata,
            docling_doc=docling_doc,  # Pass DoclingDocument for HybridChunker
        )

        if not chunks:
            logger.warning(f"No chunks created for {document_title}")
            return IngestionResult(
                document_id="",
                title=document_title,
                chunks_created=0,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                errors=["No chunks created"],
            )

        logger.info(f"Created {len(chunks)} chunks")

        # Generate embeddings
        embedded_chunks = await self.embedder.embed_chunks(chunks)
        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")

        # Save to PostgreSQL using delegated persistence
        document_id = await self.persistence.save_document(
            title=document_title,
            source=document_source,
            content=document_content,
            chunks=embedded_chunks,
            metadata=document_metadata,
        )

        logger.info(f"Saved document to PostgreSQL with ID: {document_id}")

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return IngestionResult(
            document_id=document_id,
            title=document_title,
            chunks_created=len(chunks),
            processing_time_ms=processing_time,
        )

    def _find_document_files(self) -> List[str]:
        """Find all supported document files in the documents folder."""
        if not os.path.exists(self.documents_folder):
            logger.error(f"Documents folder not found: {self.documents_folder}")
            return []

        # Supported file patterns - Docling + text formats + audio
        patterns = [
            "*.md",
            "*.markdown",
            "*.txt",  # Text formats
            "*.pdf",  # PDF
            "*.docx",
            "*.doc",  # Word
            "*.pptx",
            "*.ppt",  # PowerPoint
            "*.xlsx",
            "*.xls",  # Excel
            "*.html",
            "*.htm",  # HTML
            "*.mp3",
            "*.wav",
            "*.m4a",
            "*.flac",  # Audio formats
        ]
        files = []

        for pattern in patterns:
            files.extend(
                glob.glob(os.path.join(self.documents_folder, "**", pattern), recursive=True)
            )

        # Filter out examples/ and web/ directories (not documents to ingest)
        files = [f for f in files if "/examples/" not in f and "/web/" not in f]

        return sorted(files)


async def main():
    """Main function for running ingestion."""
    parser = argparse.ArgumentParser(description="Ingest documents into vector DB")
    parser.add_argument("--documents", "-d", default="documents", help="Documents folder path")
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip cleaning existing data before ingestion (default: cleans automatically)",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=1000, help="Chunk size for splitting documents"
    )
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap size")
    parser.add_argument("--no-semantic", action="store_true", help="Disable semantic chunking")
    # Graph-related arguments removed
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create ingestion configuration
    config = IngestionConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        use_semantic_chunking=not args.no_semantic,
    )

    # Create and run pipeline - clean by default unless --no-clean is specified
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder=args.documents,
        clean_before_ingest=not args.no_clean,  # Clean by default
    )

    def progress_callback(current: int, total: int):
        print(f"Progress: {current}/{total} documents processed")

    try:
        start_time = datetime.now()

        results = await pipeline.ingest_documents(progress_callback)

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # Print summary
        print("\n" + "=" * 50)
        print("INGESTION SUMMARY")
        print("=" * 50)
        print(f"Documents processed: {len(results)}")
        print(f"Total chunks created: {sum(r.chunks_created for r in results)}")
        # Graph-related stats removed
        print(f"Total errors: {sum(len(r.errors) for r in results)}")
        print(f"Total processing time: {total_time:.2f} seconds")
        print()

        # Print individual results
        for result in results:
            status = "✓" if not result.errors else "✗"
            print(f"{status} {result.title}: {result.chunks_created} chunks")

            if result.errors:
                for error in result.errors:
                    print(f"  Error: {error}")

    except KeyboardInterrupt:
        print("\nIngestion interrupted by user")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
