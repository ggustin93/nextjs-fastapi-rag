"""Document serving API endpoints."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import mimetypes

router = APIRouter(prefix="/documents", tags=["documents"])

# Documents directory relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"


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

    # Check if file exists
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Document not found: {file_path}")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Get mime type
    mime_type, _ = mimetypes.guess_type(str(full_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=full_path,
        media_type=mime_type,
        filename=full_path.name
    )
