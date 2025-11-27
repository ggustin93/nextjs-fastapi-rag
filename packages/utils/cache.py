"""Simple async LRU cache with TTL support."""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "max_size": self.max_size,
            "hit_rate_percent": round(self.hit_rate, 2),
        }


class AsyncLRUCache:
    """Thread-safe async LRU cache with TTL."""

    def __init__(self, max_size: int = 1000, ttl_seconds: Optional[float] = None):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()  # (value, expires_at)
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()
        self._stats = CacheStats(max_size=max_size)

    @property
    def stats(self) -> CacheStats:
        self._stats.size = len(self._cache)
        return self._stats

    def _is_expired(self, expires_at: Optional[float]) -> bool:
        return expires_at is not None and time.time() > expires_at

    def _evict_if_needed(self) -> None:
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
            self._stats.evictions += 1

    async def async_get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            value, expires_at = self._cache[key]
            if self._is_expired(expires_at):
                del self._cache[key]
                self._stats.misses += 1
                return None

            self._cache.move_to_end(key)
            self._stats.hits += 1
            return value

    async def async_set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Set value in cache."""
        async with self._lock:
            ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
            expires_at = time.time() + ttl if ttl else None

            if key not in self._cache:
                self._evict_if_needed()

            self._cache[key] = (value, expires_at)
            self._cache.move_to_end(key)

    async def async_delete(self, key: str) -> bool:
        """Delete entry from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()
        logger.info("Cache cleared")


def generate_cache_key(*args: Any, **kwargs: Any) -> str:
    """Generate cache key from arguments."""
    key_data = json.dumps(
        {"args": [str(a) for a in args], "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}},
        sort_keys=True,
    )
    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


# Global caches
document_metadata_cache: AsyncLRUCache = AsyncLRUCache(max_size=500, ttl_seconds=300)
embedding_cache: AsyncLRUCache = AsyncLRUCache(max_size=200, ttl_seconds=3600)
query_result_cache: AsyncLRUCache = AsyncLRUCache(max_size=100, ttl_seconds=60)


def get_all_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all caches."""
    return {
        "document_metadata": document_metadata_cache.stats.to_dict(),
        "embedding": embedding_cache.stats.to_dict(),
        "query_result": query_result_cache.stats.to_dict(),
    }


def clear_all_caches() -> None:
    """Clear all caches."""
    document_metadata_cache.clear()
    embedding_cache.clear()
    query_result_cache.clear()
    logger.info("All caches cleared")
