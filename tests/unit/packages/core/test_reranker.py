"""Tests for cross-encoder reranking module."""

from unittest.mock import MagicMock, patch

import pytest


class TestRerankResults:
    """Test rerank_results function."""

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty(self):
        """Empty input should return empty list."""
        from packages.core.reranker import rerank_results

        result = await rerank_results("test query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_content_field_raises(self):
        """Results without 'content' field should raise ValueError."""
        from packages.core.reranker import rerank_results

        with pytest.raises(ValueError, match="missing 'content' field"):
            await rerank_results("test query", [{"title": "no content"}])

    @pytest.mark.asyncio
    async def test_rerank_with_mocked_encoder(self):
        """Test reranking with mocked cross-encoder."""
        from packages.core import reranker

        # Reset singleton for test isolation
        reranker._cross_encoder = None

        mock_encoder = MagicMock()
        mock_encoder.predict.return_value = [0.9, 0.5, 0.7]

        with patch.object(reranker, "get_cross_encoder", return_value=mock_encoder):
            results = [
                {"content": "First doc", "similarity": 0.8},
                {"content": "Second doc", "similarity": 0.6},
                {"content": "Third doc", "similarity": 0.7},
            ]

            reranked = await reranker.rerank_results("test query", results, top_k=2)

            # Should be sorted by rerank_score descending
            assert len(reranked) == 2
            assert reranked[0]["rerank_score"] == 0.9
            assert reranked[1]["rerank_score"] == 0.7

    @pytest.mark.asyncio
    async def test_rerank_graceful_fallback_on_error(self):
        """Should fallback to original results on encoder failure."""
        from packages.core import reranker

        # Reset singleton
        reranker._cross_encoder = None

        async def failing_encoder():
            raise RuntimeError("Encoder failed")

        with patch.object(reranker, "get_cross_encoder", side_effect=failing_encoder):
            results = [
                {"content": "Doc A", "similarity": 0.9},
                {"content": "Doc B", "similarity": 0.8},
                {"content": "Doc C", "similarity": 0.7},
            ]

            # Should return original results (truncated) without raising
            reranked = await reranker.rerank_results("test", results, top_k=2)
            assert len(reranked) == 2
            assert reranked[0]["content"] == "Doc A"

    @pytest.mark.asyncio
    async def test_top_k_limits_results(self):
        """top_k should limit the number of returned results."""
        from packages.core import reranker

        reranker._cross_encoder = None

        mock_encoder = MagicMock()
        mock_encoder.predict.return_value = [0.9, 0.8, 0.7, 0.6, 0.5]

        with patch.object(reranker, "get_cross_encoder", return_value=mock_encoder):
            results = [{"content": f"Doc {i}"} for i in range(5)]
            reranked = await reranker.rerank_results("test", results, top_k=3)

            assert len(reranked) == 3


class TestCrossEncoderSingleton:
    """Test cross-encoder initialization."""

    @pytest.mark.asyncio
    async def test_singleton_returns_same_instance(self):
        """get_cross_encoder should return singleton."""
        from packages.core import reranker

        # Reset for test
        reranker._cross_encoder = MagicMock()
        first_encoder = reranker._cross_encoder

        # Should return same instance
        encoder = await reranker.get_cross_encoder()
        assert encoder is first_encoder
