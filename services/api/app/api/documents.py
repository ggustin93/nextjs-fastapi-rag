"""Document serving API endpoints."""

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/documents", tags=["documents"])

# Data directory relative to project root
# From /services/api/app/api/documents.py, need 5 parents to reach project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Search paths for documents (raw PDFs and processed scraped content)
SEARCH_DIRS = [
    DATA_DIR / "raw",
    DATA_DIR / "processed",
]


def find_document(filename: str) -> Path | None:
    """
    Search for a document file recursively in data directories.

    Args:
        filename: The filename to search for

    Returns:
        The full path if found, None otherwise
    """
    for search_dir in SEARCH_DIRS:
        if search_dir.exists():
            for path in search_dir.rglob(filename):
                # Security: Skip symlinks to prevent traversal attacks
                if path.is_file() and not path.is_symlink():
                    # Verify path is still within allowed directory
                    try:
                        path.resolve().relative_to(search_dir.resolve())
                        return path
                    except ValueError:
                        continue
    return None


@router.get("/{file_path:path}")
async def get_document(file_path: str):
    """
    Serve a document file.
    Handles paths like "raw/file.pdf" or "data/raw/file.pdf" gracefully.

    Args:
        file_path: Path to the document relative to documents directory

    Returns:
        The document file
    """
    # Security: Sanitize input path first
    clean_path = Path(file_path).as_posix()
    if ".." in clean_path or clean_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    # Strip common prefixes to ensure correct resolution relative to DATA_DIR
    # This prevents the ".../data/data/..." issue
    if clean_path.startswith("documents/"):
        clean_path = clean_path.replace("documents/", "", 1)
    if clean_path.startswith("data/"):
        clean_path = clean_path.replace("data/", "", 1)

    # Resolve the full path - try each search directory
    full_path = DATA_DIR / clean_path

    # Security check: ensure path is within data directory (check BEFORE any operations)
    try:
        resolved_data_dir = DATA_DIR.resolve()
        full_path = full_path.resolve()
        full_path.relative_to(resolved_data_dir)  # Raises ValueError if outside
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Check if file exists at exact path
    if not full_path.exists():
        # Try recursive search for filename
        filename = Path(clean_path).name
        found_path = find_document(filename)
        if found_path:
            full_path = found_path
        else:
            raise HTTPException(status_code=404, detail=f"Document not found: {clean_path}")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Get mime type - force PDF for .pdf files
    mime_type, _ = mimetypes.guess_type(str(full_path))

    # Explicitly set PDF mime type for .pdf files
    if full_path.suffix.lower() == ".pdf":
        mime_type = "application/pdf"
    elif mime_type is None:
        mime_type = "application/octet-stream"

    # Read file and return with inline disposition for browser display
    with open(full_path, "rb") as f:
        content = f.read()

    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'inline; filename="{full_path.name}"'},
    )
