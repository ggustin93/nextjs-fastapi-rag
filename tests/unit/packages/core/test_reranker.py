"""Tests for cross-encoder reranker module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.reranker import (
    BGEReranker,
    CohereReranker,
    HybridReranker,
    RerankerConfig,
    clear_reranker_cache,
    rerank_results,
)


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {"content": "Machine learning is a subset of AI", "similarity": 0.8},
        {"content": "The weather today is sunny and warm", "similarity": 0.7},
        {"content": "Deep learning uses neural networks", "similarity": 0.75},
        {"content": "Python is a programming language", "similarity": 0.6},
    ]


@pytest.fixture
def reranker_config():
    """Default reranker configuration for tests."""
    return RerankerConfig(
        enabled=True,
        model="BAAI/bge-reranker-v2-m3",
        top_k=3,
        batch_size=32,
        fallback_enabled=True,
    )


class TestRerankerConfig:
    """Tests for RerankerConfig dataclass."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = RerankerConfig()
        assert config.enabled is False
        assert config.model == "BAAI/bge-reranker-v2-m3"
        assert config.top_k == 10
        assert config.batch_size == 32
        assert config.fallback_enabled is True
        assert config.device == "auto"

    def test_config_is_frozen(self):
        """Config is immutable."""
        config = RerankerConfig()
        with pytest.raises(Exception):  # FrozenInstanceError
            config.enabled = True


class TestBGEReranker:
    """Tests for BGE cross-encoder reranker."""

    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self, reranker_config):
        """Handles empty document list gracefully."""
        reranker = BGEReranker(reranker_config)
        result = await reranker.rerank("test query", [], top_k=3)
        assert result == []

    @pytest.mark.asyncio
    async def test_rerank_with_mocked_model(self, reranker_config, sample_documents):
        """Reranker scores and sorts documents correctly with mocked model."""
        reranker = BGEReranker(reranker_config)

        # Mock the transformers model
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}

        mock_model = MagicMock()
        mock_output = MagicMock()
        # Return scores that put ML doc first, deep learning second
        import torch

        mock_output.logits = torch.tensor([[0.9], [0.1], [0.8], [0.3]])
        mock_model.return_value = mock_output
        mock_model.to = MagicMock(return_value=mock_model)
        mock_model.eval = MagicMock()

        # Patch at transformers module level since import happens inside _lazy_init
        with (
            patch("transformers.AutoTokenizer") as mock_auto_tokenizer,
            patch("transformers.AutoModelForSequenceClassification") as mock_auto_model,
        ):
            mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer
            mock_auto_model.from_pretrained.return_value = mock_model

            result = await reranker.rerank("What is machine learning?", sample_documents, top_k=3)

        # Should return top 3 sorted by score
        assert len(result) == 3
        assert all("rerank_score" in doc for doc in result)
        # Scores should be normalized 0-1
        assert all(0 <= doc["rerank_score"] <= 1 for doc in result)
        # Should be sorted descending
        assert result[0]["rerank_score"] >= result[1]["rerank_score"]

    def test_normalize_scores(self, reranker_config):
        """Score normalization works correctly."""
        reranker = BGEReranker(reranker_config)

        # Test normal case
        scores = [1.0, 5.0, 3.0]
        normalized = reranker._normalize_scores(scores)
        assert normalized == [0.0, 1.0, 0.5]

        # Test empty list
        assert reranker._normalize_scores([]) == []

        # Test single value
        normalized = reranker._normalize_scores([5.0])
        assert normalized == [0.5]  # Returns 0.5 when min==max

        # Test all same values
        normalized = reranker._normalize_scores([3.0, 3.0, 3.0])
        assert normalized == [0.5, 0.5, 0.5]


class TestCohereReranker:
    """Tests for Cohere API reranker."""

    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self, reranker_config):
        """Handles empty document list gracefully."""
        reranker = CohereReranker(reranker_config)
        result = await reranker.rerank("test query", [], top_k=3)
        assert result == []

    @pytest.mark.asyncio
    async def test_rerank_with_mocked_client(self, reranker_config, sample_documents):
        """Reranker works with mocked Cohere client."""
        reranker = CohereReranker(reranker_config)

        # Mock Cohere response
        mock_result = MagicMock()
        mock_result.index = 0
        mock_result.relevance_score = 0.95

        mock_response = MagicMock()
        mock_response.results = [mock_result]

        mock_client = MagicMock()
        mock_client.rerank = AsyncMock(return_value=mock_response)

        with (
            patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}),
            patch("cohere.AsyncClient", return_value=mock_client),
        ):
            result = await reranker.rerank("What is ML?", sample_documents, top_k=1)

        assert len(result) == 1
        assert result[0]["rerank_score"] == 0.95

    @pytest.mark.asyncio
    async def test_missing_api_key(self, reranker_config, sample_documents):
        """Raises error when COHERE_API_KEY is not set."""
        reranker = CohereReranker(reranker_config)

        with patch.dict("os.environ", {}, clear=True):
            # Remove COHERE_API_KEY from environment
            import os

            if "COHERE_API_KEY" in os.environ:
                del os.environ["COHERE_API_KEY"]

            with pytest.raises(Exception):  # ValueError or ImportError
                await reranker.rerank("test", sample_documents, top_k=1)


class TestHybridReranker:
    """Tests for hybrid reranker with fallback."""

    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self, reranker_config):
        """Handles empty document list gracefully."""
        reranker = HybridReranker(reranker_config)
        result = await reranker.rerank("test query", [], top_k=3)
        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_on_bge_failure(self, reranker_config, sample_documents):
        """Falls back to Cohere when BGE fails."""
        reranker = HybridReranker(reranker_config)

        # Mock BGE to fail
        mock_bge = MagicMock()
        mock_bge.rerank = AsyncMock(side_effect=Exception("BGE failed"))

        # Mock Cohere to succeed
        mock_cohere = MagicMock()
        mock_cohere.rerank = AsyncMock(return_value=[{"content": "test", "rerank_score": 0.9}])

        reranker._primary = mock_bge
        reranker._fallback = mock_cohere

        result = await reranker.rerank("test", sample_documents, top_k=1)

        assert len(result) == 1
        assert result[0]["rerank_score"] == 0.9

    @pytest.mark.asyncio
    async def test_returns_original_on_complete_failure(self, reranker_config, sample_documents):
        """Returns original documents when all rerankers fail."""
        reranker = HybridReranker(reranker_config)

        # Mock both to fail
        mock_bge = MagicMock()
        mock_bge.rerank = AsyncMock(side_effect=Exception("BGE failed"))

        mock_cohere = MagicMock()
        mock_cohere.rerank = AsyncMock(side_effect=Exception("Cohere failed"))

        reranker._primary = mock_bge
        reranker._fallback = mock_cohere

        result = await reranker.rerank("test", sample_documents, top_k=3)

        # Should return original docs truncated to top_k
        assert len(result) == 3
        assert result[0]["content"] == sample_documents[0]["content"]

    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self, sample_documents):
        """Skips fallback when disabled."""
        config = RerankerConfig(
            enabled=True,
            fallback_enabled=False,
        )
        reranker = HybridReranker(config)

        # Mock BGE to fail
        mock_bge = MagicMock()
        mock_bge.rerank = AsyncMock(side_effect=Exception("BGE failed"))
        reranker._primary = mock_bge

        result = await reranker.rerank("test", sample_documents, top_k=2)

        # Should return original docs without trying Cohere
        assert len(result) == 2


class TestRerankResults:
    """Tests for the convenience function."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear reranker cache before each test."""
        clear_reranker_cache()
        yield
        clear_reranker_cache()

    @pytest.mark.asyncio
    async def test_disabled_passthrough(self, sample_documents):
        """Returns original results when disabled."""
        config = RerankerConfig(enabled=False)

        result = await rerank_results("test query", sample_documents, config)

        assert result == sample_documents

    @pytest.mark.asyncio
    async def test_empty_results_passthrough(self):
        """Handles empty results gracefully."""
        config = RerankerConfig(enabled=True)

        result = await rerank_results("test query", [], config)

        assert result == []

    @pytest.mark.asyncio
    async def test_uses_settings_when_no_config(self, sample_documents):
        """Uses settings when config not provided."""
        # Patch at packages.config since that's where settings is imported from
        with patch("packages.config.settings") as mock_settings:
            mock_settings.search.reranker_enabled = False

            result = await rerank_results("test", sample_documents)

            # Should use settings.reranker_enabled=False, so passthrough
            assert result == sample_documents


class TestScoreNormalization:
    """Tests for score normalization edge cases."""

    def test_negative_scores(self):
        """Handles negative scores correctly."""
        reranker = BGEReranker(RerankerConfig())
        scores = [-5.0, 0.0, 5.0]
        normalized = reranker._normalize_scores(scores)

        assert normalized[0] == 0.0  # -5.0 -> 0.0
        assert normalized[1] == 0.5  # 0.0 -> 0.5
        assert normalized[2] == 1.0  # 5.0 -> 1.0

    def test_large_scores(self):
        """Handles large score ranges."""
        reranker = BGEReranker(RerankerConfig())
        scores = [0.0, 1000.0]
        normalized = reranker._normalize_scores(scores)

        assert normalized[0] == 0.0
        assert normalized[1] == 1.0

    def test_close_scores(self):
        """Handles very close scores."""
        reranker = BGEReranker(RerankerConfig())
        scores = [0.999, 1.0, 1.001]
        normalized = reranker._normalize_scores(scores)

        # All should be in valid range
        assert all(0 <= s <= 1 for s in normalized)
        # Order should be preserved
        assert normalized[0] < normalized[1] < normalized[2]
