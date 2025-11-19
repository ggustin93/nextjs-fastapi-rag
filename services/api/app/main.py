"""FastAPI application entry point for Docling RAG Agent."""
import sys
import os

# Add project root to path for package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api import chat, documents
from packages.__version__ import __version__

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Docling RAG Agent API",
    description="RESTful API for conversational RAG using PydanticAI",
    version=__version__
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Type", "Content-Disposition"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Docling RAG Agent API",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/v1/chat/health"
    }


@app.get("/health")
async def health():
    """Global health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
