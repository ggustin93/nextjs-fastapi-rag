"""
Tests for embedding cache.
"""

from packages.ingestion.embedder import EmbeddingCache


class TestEmbeddingCache:
    """Test EmbeddingCache behavior."""

    def test_cache_miss(self):
        """Cache should return None for missing keys."""
        cache = EmbeddingCache()
        result = cache.get("nonexistent text")
        assert result is None

    def test_cache_hit(self):
        """Cache should return stored embedding."""
        cache = EmbeddingCache()
        embedding = [0.1, 0.2, 0.3]

        cache.put("test text", embedding)
        result = cache.get("test text")

        assert result == embedding

    def test_cache_different_keys(self):
        """Different text should have different cache entries."""
        cache = EmbeddingCache()

        cache.put("text 1", [1.0, 1.0])
        cache.put("text 2", [2.0, 2.0])

        assert cache.get("text 1") == [1.0, 1.0]
        assert cache.get("text 2") == [2.0, 2.0]

    def test_cache_eviction(self):
        """Cache should evict oldest entry when full."""
        cache = EmbeddingCache(max_size=2)

        cache.put("text1", [1.0])
        cache.put("text2", [2.0])
        cache.put("text3", [3.0])  # Should evict text1

        assert cache.get("text1") is None
        assert cache.get("text2") == [2.0]
        assert cache.get("text3") == [3.0]

    def test_cache_update_access_time(self):
        """Accessing an entry should update its access time."""
        cache = EmbeddingCache(max_size=2)

        cache.put("text1", [1.0])
        cache.put("text2", [2.0])

        # Access text1 to make it more recent
        cache.get("text1")

        # Add text3, should evict text2 (oldest now)
        cache.put("text3", [3.0])

        assert cache.get("text1") == [1.0]  # Still there
        assert cache.get("text2") is None  # Evicted
        assert cache.get("text3") == [3.0]

    def test_default_max_size(self):
        """Default max size should be 1000."""
        cache = EmbeddingCache()
        assert cache.max_size == 1000

    def test_custom_max_size(self):
        """Custom max size should be respected."""
        cache = EmbeddingCache(max_size=50)
        assert cache.max_size == 50
