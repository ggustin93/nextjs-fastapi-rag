"""
Health check API endpoints for production readiness.

This module provides comprehensive health check endpoints following
Kubernetes-style liveness and readiness probe patterns.

Endpoints:
    - GET /health/liveness: Basic liveness check (is service running?)
    - GET /health/readiness: Full readiness check (can service handle requests?)
    - GET /health/detailed: Detailed health status with component checks
"""

import logging
import os
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Track service start time for uptime calculation
SERVICE_START_TIME = datetime.utcnow()


class HealthStatus(BaseModel):
    """Health status response model."""

    status: str
    timestamp: str
    version: Optional[str] = None


class ComponentHealth(BaseModel):
    """Individual component health status."""

    name: str
    status: str
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class DetailedHealthStatus(BaseModel):
    """Detailed health status with component checks."""

    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    components: List[ComponentHealth]
    environment: Optional[str] = None


async def check_database_health() -> ComponentHealth:
    """
    Check Supabase database connectivity and health.

    Returns:
        ComponentHealth with database status and latency.
    """
    start_time = time.time()
    try:
        from packages.utils.supabase_client import SupabaseRestClient

        client = SupabaseRestClient()
        await client.initialize()

        # Simple connectivity test - count documents
        # This validates both REST API and database connectivity
        await client.execute_rpc("count_documents", {})
        await client.close()

        latency_ms = (time.time() - start_time) * 1000
        return ComponentHealth(
            name="database",
            status="healthy",
            latency_ms=round(latency_ms, 2),
            message="Supabase connection successful",
        )
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.warning(f"Database health check failed: {e}")
        return ComponentHealth(
            name="database",
            status="degraded",
            latency_ms=round(latency_ms, 2),
            message=f"Connection issue: {str(e)[:100]}",
        )


async def check_openai_health() -> ComponentHealth:
    """
    Check OpenAI API connectivity (lightweight check).

    Returns:
        ComponentHealth with OpenAI status.
    """
    start_time = time.time()
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ComponentHealth(
                name="openai",
                status="unhealthy",
                message="OPENAI_API_KEY not configured",
            )

        # Just verify the key format (don't make actual API call to save costs)
        if api_key.startswith("sk-") and len(api_key) > 20:
            latency_ms = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="openai",
                status="healthy",
                latency_ms=round(latency_ms, 2),
                message="API key configured",
            )
        else:
            return ComponentHealth(
                name="openai",
                status="degraded",
                message="API key format may be invalid",
            )
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.warning(f"OpenAI health check failed: {e}")
        return ComponentHealth(
            name="openai",
            status="unhealthy",
            latency_ms=round(latency_ms, 2),
            message=str(e)[:100],
        )


async def check_embedder_health() -> ComponentHealth:
    """
    Check embedding service health.

    Returns:
        ComponentHealth with embedder status.
    """
    start_time = time.time()
    try:
        from packages.ingestion.embedder import create_embedder

        # Just verify embedder can be created without making API calls
        create_embedder()
        latency_ms = (time.time() - start_time) * 1000
        return ComponentHealth(
            name="embedder",
            status="healthy",
            latency_ms=round(latency_ms, 2),
            message="Embedder initialized",
        )
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.warning(f"Embedder health check failed: {e}")
        return ComponentHealth(
            name="embedder",
            status="unhealthy",
            latency_ms=round(latency_ms, 2),
            message=str(e)[:100],
        )


@router.get("/liveness", response_model=HealthStatus)
async def liveness():
    """
    Basic liveness check - is the service running?

    This endpoint should return 200 OK if the service process is alive.
    Used by container orchestrators (Kubernetes, Docker) to detect crashed services.

    Returns:
        HealthStatus with "alive" status.
    """
    try:
        from packages.__version__ import __version__
    except ImportError:
        __version__ = "unknown"

    return HealthStatus(
        status="alive",
        timestamp=datetime.utcnow().isoformat(),
        version=__version__,
    )


@router.get("/readiness", response_model=HealthStatus)
async def readiness(response: Response):
    """
    Readiness check - can the service handle requests?

    Verifies critical dependencies (database, external services) are available.
    Used to determine if the service should receive traffic.

    Returns:
        HealthStatus with "ready" or "not_ready" status.
        Returns 503 if not ready.
    """
    try:
        from packages.__version__ import __version__
    except ImportError:
        __version__ = "unknown"

    # Check critical components
    db_health = await check_database_health()
    openai_health = await check_openai_health()

    # Service is ready if database is healthy and OpenAI is configured
    is_ready = (
        db_health.status == "healthy"
        and openai_health.status in ["healthy", "degraded"]
    )

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthStatus(
            status="not_ready",
            timestamp=datetime.utcnow().isoformat(),
            version=__version__,
        )

    return HealthStatus(
        status="ready",
        timestamp=datetime.utcnow().isoformat(),
        version=__version__,
    )


@router.get("/detailed", response_model=DetailedHealthStatus)
async def detailed_health():
    """
    Detailed health status with all component checks.

    Provides comprehensive health information including:
    - Service uptime
    - Individual component health (database, OpenAI, embedder)
    - Response latencies
    - Environment information

    Returns:
        DetailedHealthStatus with component-level health information.
    """
    try:
        from packages.__version__ import __version__
    except ImportError:
        __version__ = "unknown"

    # Calculate uptime
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()

    # Run all health checks
    components = [
        await check_database_health(),
        await check_openai_health(),
        await check_embedder_health(),
    ]

    # Determine overall status
    unhealthy_count = sum(1 for c in components if c.status == "unhealthy")
    degraded_count = sum(1 for c in components if c.status == "degraded")

    if unhealthy_count > 0:
        overall_status = "unhealthy"
    elif degraded_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return DetailedHealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version=__version__,
        uptime_seconds=round(uptime, 2),
        components=components,
        environment=os.getenv("ENVIRONMENT", "development"),
    )


@router.get("/")
async def health_root():
    """
    Root health endpoint - backwards compatible simple health check.

    Returns:
        Simple health status dict.
    """
    return {"status": "healthy", "service": "rag-agent"}


@router.get("/cache")
async def cache_stats():
    """
    Get cache statistics for monitoring.

    Returns statistics for all global caches including:
    - Hit/miss counts
    - Hit rate percentage
    - Current cache sizes
    - Eviction counts

    Returns:
        Dictionary with cache statistics.
    """
    try:
        from packages.utils.cache import get_all_cache_stats

        return {
            "status": "ok",
            "caches": get_all_cache_stats(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.warning(f"Cache stats retrieval failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.post("/cache/clear")
async def clear_caches():
    """
    Clear all caches.

    Use this endpoint to force cache invalidation after
    bulk data changes or during troubleshooting.

    Returns:
        Confirmation message.
    """
    try:
        from packages.utils.cache import clear_all_caches

        clear_all_caches()
        return {
            "status": "ok",
            "message": "All caches cleared",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Cache clear failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
