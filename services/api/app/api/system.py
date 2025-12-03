"""System information and configuration API endpoints."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter

from packages.config import settings
from packages.core.factory import MODEL_PROVIDERS

router = APIRouter(prefix="/system", tags=["system"])

# Data directory paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Model display info (id -> display properties)
# Provider is derived from MODEL_PROVIDERS in factory.py
MODEL_DISPLAY_INFO = {
    "gpt-4o-mini": {"name": "GPT-4o Mini", "description": "Fast, cost-effective"},
    "mistral-small-latest": {
        "name": "Mistral Small",
        "description": "Fast, efficient with tool support",
    },
    "mistral-large-latest": {
        "name": "Mistral Large",
        "description": "Frontier model, advanced reasoning",
    },
}


@router.get("/config")
async def get_system_config():
    """
    Get current system configuration including LLM, embeddings, chunking, and vector DB settings.

    Returns detailed configuration of the RAG system including:
    - Language model configuration (provider, model, temperature)
    - Embeddings configuration (model, dimensions, provider)
    - Chunking strategy (size, overlap)
    - Vector database information
    """
    # Get embedding dimensions from model name
    embedding_dimensions = 1536  # default for text-embedding-3-small
    if "text-embedding-3-large" in settings.embedding.model:
        embedding_dimensions = 3072
    elif "ada-002" in settings.embedding.model:
        embedding_dimensions = 1536

    return {
        "llm": {
            "model": settings.llm.model,
            "provider": settings.llm.provider,
            "temperature": 0.7,  # Default temperature for chat
        },
        "embeddings": {
            "model": settings.embedding.model,
            "provider": "OpenAI" if not settings.embedding.base_url else "Custom",
            "dimensions": embedding_dimensions,
        },
        "chunking": {
            "strategy": "Recursive Character Text Splitter",
            "chunk_size": settings.chunking.chunk_size,
            "chunk_overlap": settings.chunking.chunk_overlap,
        },
        "vector_db": {
            "provider": "Supabase pgvector",
            "collection": "documents",
        },
        "retrieval": {
            "query_expansion_enabled": settings.search.query_expansion_enabled,
            "query_expansion_model": settings.search.query_expansion_model,
            "title_rerank_enabled": settings.search.title_rerank_enabled,
            "title_rerank_boost": settings.search.title_rerank_boost,
            "rrf_k": settings.search.rrf_k,
            "similarity_threshold": settings.search.similarity_threshold,
        },
    }


@router.get("/models")
async def get_available_models():
    """
    Get list of available LLM models for user selection.

    Returns a list of models that users can choose from in the chat interface.
    Model provider is derived from MODEL_PROVIDERS in factory.py (single source of truth).
    """
    models = []
    current_model = settings.llm.model

    for model_id, display_info in MODEL_DISPLAY_INFO.items():
        provider = MODEL_PROVIDERS.get(model_id, "openai")
        models.append(
            {
                "id": model_id,
                "name": display_info["name"],
                "provider": provider,
                "description": display_info["description"],
                "is_current": model_id == current_model,
            }
        )

    return {"models": models, "current": current_model}


@router.get("/documents")
async def get_ingested_documents():
    """
    Get list of all ingested documents with metadata.

    Returns information about documents in both raw and processed directories:
    - Filename and full path
    - File size in bytes
    - File type (pdf, markdown, html, etc.)
    - Last modified timestamp (as ingested_at)
    """
    documents = []

    # Scan raw directory for PDFs and other documents
    if RAW_DIR.exists():
        for file_path in RAW_DIR.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                # Determine file type
                suffix = file_path.suffix.lower()
                if suffix == ".pdf":
                    file_type = "pdf"
                elif suffix in [".md", ".markdown"]:
                    file_type = "markdown"
                elif suffix in [".html", ".htm"]:
                    file_type = "html"
                elif suffix in [".txt", ".text"]:
                    file_type = "text"
                elif suffix in [".json"]:
                    file_type = "json"
                else:
                    file_type = "other"

                # Get file stats
                stats = file_path.stat()

                documents.append(
                    {
                        "filename": file_path.name,
                        "path": str(file_path.relative_to(PROJECT_ROOT)),
                        "size": stats.st_size,
                        "ingested_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                        "type": file_type,
                    }
                )

    # Scan processed directory for scraped content
    if PROCESSED_DIR.exists():
        for file_path in PROCESSED_DIR.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                # Determine file type
                suffix = file_path.suffix.lower()
                if suffix in [".md", ".markdown"]:
                    file_type = "markdown"
                elif suffix in [".html", ".htm"]:
                    file_type = "html"
                elif suffix in [".json"]:
                    file_type = "json"
                else:
                    file_type = "other"

                # Get file stats
                stats = file_path.stat()

                documents.append(
                    {
                        "filename": file_path.name,
                        "path": str(file_path.relative_to(PROJECT_ROOT)),
                        "size": stats.st_size,
                        "ingested_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                        "type": file_type,
                    }
                )

    # Sort by most recently ingested
    documents.sort(key=lambda x: x["ingested_at"], reverse=True)

    return {"documents": documents}


@router.get("/sources")
async def get_scraped_sources():
    """
    Get list of scraped websites and their metadata.

    Returns information about web sources that have been scraped:
    - Source URL
    - Page title
    - Number of pages scraped
    - Timestamp of scraping operation
    """
    sources = []

    # Scan processed/scraped directory for website metadata
    scraped_dir = PROCESSED_DIR / "scraped"
    if scraped_dir.exists():
        # Group files by website (by parent directory)
        website_dirs = {}
        for file_path in scraped_dir.rglob("*.md"):
            if file_path.is_file():
                # Use parent directory as website grouping
                website_name = file_path.parent.name
                if website_name not in website_dirs:
                    website_dirs[website_name] = {
                        "files": [],
                        "latest_mtime": 0,
                    }

                stats = file_path.stat()
                website_dirs[website_name]["files"].append(file_path)
                website_dirs[website_name]["latest_mtime"] = max(
                    website_dirs[website_name]["latest_mtime"], stats.st_mtime
                )

        # Create source entries for each website
        for website_name, data in website_dirs.items():
            # Try to extract URL from first file's frontmatter or filename
            url = f"https://{website_name}"  # Default fallback
            title = website_name.replace("-", " ").title()  # Default title

            # Try to read URL from first file
            if data["files"]:
                try:
                    with open(data["files"][0], "r", encoding="utf-8") as f:
                        content = f.read(500)  # Read first 500 chars
                        # Look for URL in frontmatter or content
                        if "http" in content:
                            lines = content.split("\n")
                            for line in lines[:10]:  # Check first 10 lines
                                if "http" in line:
                                    # Extract URL
                                    parts = line.split("http")
                                    if len(parts) > 1:
                                        url_part = "http" + parts[1].split()[0].strip("[]()\"',")
                                        url = url_part
                                        break
                except Exception:
                    pass  # Use default if reading fails

            sources.append(
                {
                    "url": url,
                    "title": title,
                    "pages_count": len(data["files"]),
                    "scraped_at": datetime.fromtimestamp(data["latest_mtime"]).isoformat(),
                }
            )

    # Sort by most recently scraped
    sources.sort(key=lambda x: x["scraped_at"], reverse=True)

    return {"sources": sources}
