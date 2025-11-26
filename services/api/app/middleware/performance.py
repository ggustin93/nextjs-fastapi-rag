"""
Simple performance logging middleware for FastAPI.

Provides:
- Request timing with X-Response-Time header
- Slow request logging for debugging

This is a simplified version focused on debugging value without
unused metrics aggregation infrastructure.
"""

import logging
import time
from typing import Callable, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging slow requests and adding response time headers.

    Args:
        app: ASGI application
        slow_request_threshold_ms: Threshold for logging slow requests (default: 500ms)
        exclude_paths: Paths to exclude from timing (default: health endpoints)
    """

    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold_ms: float = 500.0,
        exclude_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.exclude_paths = exclude_paths or ["/health", "/favicon.ico", "/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log timing."""
        path = request.url.path

        # Skip excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)

        # Time the request
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Request failed: {request.method} {path} - {e}")
            raise

        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Add timing header
        response.headers["X-Response-Time"] = f"{latency_ms:.2f}ms"

        # Log slow requests
        if latency_ms > self.slow_request_threshold_ms:
            logger.warning(
                f"Slow request: {request.method} {path} - {latency_ms:.2f}ms "
                f"(threshold: {self.slow_request_threshold_ms}ms)"
            )

        return response
