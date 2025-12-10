"""
FastAPI application entry point for RAG Agent API.

This module initializes the FastAPI application with:
- CORS middleware for frontend communication
- Performance monitoring middleware
- API routers for chat, documents, and health endpoints
- OpenAPI documentation
- Lifespan management for singleton RAG resources

Configuration is loaded from centralized settings in packages.config.
See packages/config/__init__.py for available environment variables.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

# Add project root to path for package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_ai import Agent

from app.api import chat, documents, health, proxy, system, worksites
from app.middleware import PerformanceMiddleware
from packages.__version__ import __version__
from packages.config import settings
from packages.core.factory import create_rag_agent
from packages.core.types import RAGContext
from packages.utils.supabase_client import SupabaseRestClient

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


# =============================================================================
# Application State: Singleton Resources
# =============================================================================


@dataclass
class AppState:
    """Application-level singleton resources.

    These resources are initialized once at startup and shared across all requests
    to avoid connection pool exhaustion and improve performance.

    - agent: Stateless PydanticAI agent (same config for all requests)
    - db_client: Shared Supabase client with connection pooling
    - embedder: Shared embedding model (lazy-loaded OpenAI client)
    """

    agent: Optional[Agent] = None
    db_client: Optional[SupabaseRestClient] = None
    embedder: Optional[object] = None  # EmbeddingGenerator type

    def create_rag_context(self) -> RAGContext:
        """Create per-request RAGContext using shared resources.

        The context wraps shared resources but has per-request mutable state
        (last_search_sources) for request isolation.
        """
        return RAGContext(
            db_client=self.db_client,
            embedder=self.embedder,
            weather_config=settings.weather,
            last_search_sources=[],  # Per-request mutable state
        )


# Global app state instance
app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle for singleton resources.

    Startup: Initialize shared agent, database client, and embedder once.
    Shutdown: Clean up database connections gracefully.

    This prevents connection pool exhaustion by reusing resources across requests.
    """
    global app_state

    # === STARTUP ===
    logger.info("🚀 Initializing RAG singleton resources...")

    try:
        # 1. Initialize database client (shared connection pool)
        app_state.db_client = SupabaseRestClient()
        await app_state.db_client.initialize()
        logger.info("✅ Supabase client initialized (shared connection pool)")

        # 2. Initialize embedder (lazy-loaded OpenAI client)
        from packages.ingestion.embedder import create_embedder

        app_state.embedder = create_embedder()
        logger.info("✅ Embedder initialized (shared OpenAI client)")

        # 3. Create stateless agent (reused for all requests)
        app_state.agent = create_rag_agent()
        logger.info(f"✅ RAG agent initialized with model: {settings.llm.model}")

        logger.info("🎉 All RAG resources initialized successfully")

    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG resources: {e}", exc_info=True)
        raise

    yield  # Application runs here

    # === SHUTDOWN ===
    logger.info("🧹 Cleaning up RAG resources...")

    if app_state.db_client:
        await app_state.db_client.close()
        logger.info("✅ Supabase client closed")

    logger.info("👋 RAG resources cleanup complete")


# Configure logging with INFO level to show debug logs
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Initialize FastAPI app with lifespan management
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
        {"name": "system", "description": "System configuration and data inventory"},
    ],
    lifespan=lifespan,  # Use lifespan for singleton resource management
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
app.include_router(system.router, prefix="/api/v1")
app.include_router(worksites.router, prefix="/api/v1")
app.include_router(proxy.router, prefix="/api/v1")


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
