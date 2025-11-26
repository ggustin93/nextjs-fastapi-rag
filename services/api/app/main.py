"""
FastAPI application entry point for RAG Agent API.

This module initializes the FastAPI application with:
- CORS middleware for frontend communication
- Performance monitoring middleware
- API routers for chat, documents, and health endpoints
- OpenAPI documentation

Configuration is loaded from centralized settings in packages.config.
See packages/config/__init__.py for available environment variables.
"""

import os
import sys

# Add project root to path for package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, documents, health
from app.middleware import PerformanceMiddleware
from packages.__version__ import __version__
from packages.config import settings

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="nextjs-fastapi-rag API",
    description="""
## RESTful API for conversational RAG

This API provides:
- **Chat**: Stream chat responses with RAG-powered knowledge retrieval
- **Documents**: Serve and manage ingested documents
- **Health**: Comprehensive health checks for monitoring

### API Versioning
- Current version: v1
- Base path: `/api/v1`
- Versioning strategy: URL path prefix
""",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "chat", "description": "Chat and conversation endpoints"},
        {"name": "documents", "description": "Document retrieval and management"},
        {"name": "health", "description": "Health checks and monitoring"},
    ],
)

# Configure CORS for frontend (from centralized settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Type", "Content-Disposition", "X-Response-Time"],
)

# Add performance monitoring middleware (threshold from centralized settings)
app.add_middleware(
    PerformanceMiddleware,
    slow_request_threshold_ms=settings.api.slow_request_threshold_ms,
    exclude_paths=["/health", "/favicon.ico", "/docs", "/redoc", "/openapi.json"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "nextjs-fastapi-rag API",
        "version": __version__,
        "docs": "/docs",
        "health": {
            "liveness": "/api/v1/health/liveness",
            "readiness": "/api/v1/health/readiness",
            "detailed": "/api/v1/health/detailed",
        },
    }


@app.get("/health")
async def health_legacy():
    """Legacy global health check endpoint (kept for backwards compatibility)."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
