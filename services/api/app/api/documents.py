"""Document serving API endpoints."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pathlib import Path
import mimetypes

router = APIRouter(prefix="/documents", tags=["documents"])

# Documents directory relative to project root
# From /services/api/app/api/documents.py, need 5 parents to reach project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"


def find_document(filename: str) -> Path | None:
    """
    Search for a document file recursively in the documents directory.

    Args:
        filename: The filename to search for

    Returns:
        The full path if found, None otherwise
    """
    for path in DOCUMENTS_DIR.rglob(filename):
        if path.is_file():
            return path
    return None


@router.get("/{file_path:path}")
async def get_document(file_path: str):
    """
    Serve a document file.

    Args:
        file_path: Path to the document relative to documents directory

    Returns:
        The document file
    """
    # Resolve the full path
    full_path = DOCUMENTS_DIR / file_path

    # Security check: ensure path is within documents directory
    try:
        full_path = full_path.resolve()
        if not str(full_path).startswith(str(DOCUMENTS_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Check if file exists at exact path
    if not full_path.exists():
        # Try recursive search for filename
        filename = Path(file_path).name
        found_path = find_document(filename)
        if found_path:
            full_path = found_path
        else:
            raise HTTPException(status_code=404, detail=f"Document not found: {file_path}")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Get mime type - force PDF for .pdf files
    mime_type, _ = mimetypes.guess_type(str(full_path))

    # Explicitly set PDF mime type for .pdf files
    if full_path.suffix.lower() == '.pdf':
        mime_type = 'application/pdf'
    elif mime_type is None:
        mime_type = 'application/octet-stream'

    # Read file and return with inline disposition for browser display
    with open(full_path, "rb") as f:
        content = f.read()

    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{full_path.name}"'
        }
    )
