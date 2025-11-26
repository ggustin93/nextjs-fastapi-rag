"""
Middleware components for the API.

This package contains middleware for:
- Performance monitoring with request timing and slow request logging
"""

from .performance import PerformanceMiddleware

__all__ = [
    "PerformanceMiddleware",
]
