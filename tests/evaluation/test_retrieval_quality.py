"""Tests for RAG evaluation framework.

Tests the metrics calculations, ground truth loading, and evaluator functionality.
"""

import json
import math
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.core.evaluation.ground_truth import (
    GroundTruthDataset,
    QueryDifficulty,
    QueryGroundTruth,
    QueryIntent,
    create_sample_dataset,
)
from packages.core.evaluation.metrics import (
    RetrievalMetrics,
    calculate_all_metrics,
    calculate_hit_rate,
    calculate_mrr,
    calculate_ndcg,
    calculate_precision_at_k,
    calculate_recall_at_k,
)

# =============================================================================
# Metrics Tests
# =============================================================================


class TestPrecisionAtK:
    """Tests for Precision@K metric."""

    def test_perfect_precision(self):
        """All retrieved items are relevant."""
        retrieved = ["a", "b", "c", "d"]
        relevant = {"a", "b", "c", "d"}
        assert calculate_precision_at_k(retrieved, relevant, k=4) == 1.0

    def test_no_relevant_retrieved(self):
        """No retrieved items are relevant."""
        retrieved = ["a", "b", "c", "d"]
        relevant = {"e", "f"}
        assert calculate_precision_at_k(retrieved, relevant, k=4) == 0.0

    def test_partial_precision(self):
        """Some retrieved items are relevant."""
        retrieved = ["a", "b", "c", "d"]
        relevant = {"a", "c"}
        assert calculate_precision_at_k(retrieved, relevant, k=4) == 0.5

    def test_k_less_than_retrieved(self):
        """K is less than total retrieved."""
        retrieved = ["a", "b", "c", "d"]
        relevant = {"a", "b"}
        assert calculate_precision_at_k(retrieved, relevant, k=2) == 1.0

    def test_k_greater_than_retrieved(self):
        """K is greater than total retrieved."""
        retrieved = ["a", "b"]
        relevant = {"a", "b", "c"}
        # P@4 with only 2 items: 2 relevant / 4 = 0.5
        assert calculate_precision_at_k(retrieved, relevant, k=4) == 0.5

    def test_empty_retrieved(self):
        """No items retrieved."""
        assert calculate_precision_at_k([], {"a", "b"}, k=5) == 0.0

    def test_zero_k(self):
        """K is zero."""
        assert calculate_precision_at_k(["a", "b"], {"a"}, k=0) == 0.0

    def test_accepts_list_for_relevant(self):
        """Relevant IDs can be a list."""
        retrieved = ["a", "b", "c"]
        relevant = ["a", "c"]
        assert calculate_precision_at_k(retrieved, relevant, k=3) == pytest.approx(2 / 3)


class TestRecallAtK:
    """Tests for Recall@K metric."""

    def test_perfect_recall(self):
        """All relevant items are retrieved."""
        retrieved = ["a", "b", "c", "d"]
        relevant = {"a", "c"}
        assert calculate_recall_at_k(retrieved, relevant, k=4) == 1.0

    def test_no_recall(self):
        """No relevant items are retrieved."""
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b"}
        assert calculate_recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_partial_recall(self):
        """Some relevant items are retrieved."""
        retrieved = ["a", "b", "c"]
        relevant = {"a", "c", "e"}
        assert calculate_recall_at_k(retrieved, relevant, k=3) == pytest.approx(2 / 3)

    def test_empty_relevant(self):
        """No relevant items exist (perfect recall by definition)."""
        retrieved = ["a", "b"]
        relevant = set()
        assert calculate_recall_at_k(retrieved, relevant, k=2) == 1.0

    def test_k_limits_search(self):
        """K limits the search window."""
        retrieved = ["a", "b", "c", "d"]
        relevant = {"d"}
        assert calculate_recall_at_k(retrieved, relevant, k=2) == 0.0
        assert calculate_recall_at_k(retrieved, relevant, k=4) == 1.0


class TestMRR:
    """Tests for Mean Reciprocal Rank metric."""

    def test_first_position(self):
        """First relevant item is at position 1."""
        retrieved = ["a", "b", "c"]
        relevant = {"a"}
        assert calculate_mrr(retrieved, relevant) == 1.0

    def test_second_position(self):
        """First relevant item is at position 2."""
        retrieved = ["x", "a", "b"]
        relevant = {"a", "b"}
        assert calculate_mrr(retrieved, relevant) == 0.5

    def test_third_position(self):
        """First relevant item is at position 3."""
        retrieved = ["x", "y", "a"]
        relevant = {"a"}
        assert calculate_mrr(retrieved, relevant) == pytest.approx(1 / 3)

    def test_no_relevant_found(self):
        """No relevant items in retrieved list."""
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b"}
        assert calculate_mrr(retrieved, relevant) == 0.0

    def test_empty_relevant(self):
        """No relevant items defined (perfect score by definition)."""
        retrieved = ["a", "b"]
        assert calculate_mrr(retrieved, set()) == 1.0


class TestNDCG:
    """Tests for NDCG@K metric."""

    def test_perfect_ndcg(self):
        """All relevant items at top positions."""
        retrieved = ["a", "b", "c", "d"]
        relevant = {"a", "b"}
        assert calculate_ndcg(retrieved, relevant, k=4) == 1.0

    def test_worst_ndcg(self):
        """Relevant items at worst positions."""
        retrieved = ["x", "y", "z", "a"]
        relevant = {"a"}
        # DCG = 1/log2(5) ≈ 0.431, IDCG = 1/log2(2) = 1.0
        assert calculate_ndcg(retrieved, relevant, k=4) == pytest.approx(1 / math.log2(5), rel=0.01)

    def test_no_relevant_retrieved(self):
        """No relevant items retrieved."""
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b"}
        assert calculate_ndcg(retrieved, relevant, k=3) == 0.0

    def test_empty_relevant(self):
        """No relevant items defined (perfect score)."""
        retrieved = ["a", "b"]
        assert calculate_ndcg(retrieved, set(), k=2) == 1.0

    def test_k_limits_scope(self):
        """K limits the scope of calculation."""
        retrieved = ["x", "y", "a", "b"]
        relevant = {"a", "b"}
        # At k=2, neither a nor b are in scope
        assert calculate_ndcg(retrieved, relevant, k=2) == 0.0


class TestHitRate:
    """Tests for Hit Rate@K metric."""

    def test_hit(self):
        """At least one relevant item found."""
        retrieved = ["x", "a", "y"]
        relevant = {"a"}
        assert calculate_hit_rate(retrieved, relevant, k=3) == 1.0

    def test_miss(self):
        """No relevant items found."""
        retrieved = ["x", "y", "z"]
        relevant = {"a"}
        assert calculate_hit_rate(retrieved, relevant, k=3) == 0.0

    def test_k_boundary(self):
        """Hit/miss depends on K."""
        retrieved = ["x", "y", "a"]
        relevant = {"a"}
        assert calculate_hit_rate(retrieved, relevant, k=2) == 0.0
        assert calculate_hit_rate(retrieved, relevant, k=3) == 1.0


class TestCalculateAllMetrics:
    """Tests for the convenience function."""

    def test_returns_metrics_object(self):
        """Returns a RetrievalMetrics dataclass."""
        retrieved = ["a", "b", "c"]
        relevant = {"a", "c"}
        metrics = calculate_all_metrics(retrieved, relevant, k=3)

        assert isinstance(metrics, RetrievalMetrics)
        assert metrics.k == 3
        assert 0 <= metrics.precision_at_k <= 1
        assert 0 <= metrics.recall_at_k <= 1
        assert 0 <= metrics.mrr <= 1
        assert 0 <= metrics.ndcg_at_k <= 1
        assert metrics.hit_rate in [0.0, 1.0]

    def test_to_dict(self):
        """Metrics can be serialized to dictionary."""
        metrics = RetrievalMetrics(
            precision_at_k=0.5,
            recall_at_k=0.667,
            mrr=1.0,
            ndcg_at_k=0.8,
            hit_rate=1.0,
            k=3,
        )
        d = metrics.to_dict()

        assert d["precision@3"] == 0.5
        assert d["recall@3"] == 0.667
        assert d["mrr"] == 1.0
        assert d["ndcg@3"] == 0.8
        assert d["hit_rate@3"] == 1.0


# =============================================================================
# Ground Truth Tests
# =============================================================================


class TestQueryGroundTruth:
    """Tests for QueryGroundTruth dataclass."""

    def test_from_dict(self):
        """Create from dictionary."""
        data = {
            "query": "Test query?",
            "expected_doc_ids": ["doc1", "doc2"],
            "intent": "definition",
            "difficulty": "easy",
            "notes": "Test note",
        }
        gt = QueryGroundTruth.from_dict(data)

        assert gt.query == "Test query?"
        assert gt.expected_doc_ids == {"doc1", "doc2"}
        assert gt.intent == QueryIntent.DEFINITION
        assert gt.difficulty == QueryDifficulty.EASY
        assert gt.notes == "Test note"

    def test_to_dict(self):
        """Convert to dictionary."""
        gt = QueryGroundTruth(
            query="Test?",
            expected_doc_ids={"doc1"},
            intent=QueryIntent.PROCEDURE,
            difficulty=QueryDifficulty.HARD,
        )
        d = gt.to_dict()

        assert d["query"] == "Test?"
        assert d["expected_doc_ids"] == ["doc1"]
        assert d["intent"] == "procedure"
        assert d["difficulty"] == "hard"

    def test_defaults(self):
        """Default values are applied."""
        gt = QueryGroundTruth(query="Test?", expected_doc_ids=set())
        assert gt.intent == QueryIntent.DEFINITION
        assert gt.difficulty == QueryDifficulty.MEDIUM
        assert gt.notes is None


class TestGroundTruthDataset:
    """Tests for GroundTruthDataset class."""

    def test_create_sample_dataset(self):
        """Sample dataset creation works."""
        dataset = create_sample_dataset()

        assert len(dataset) > 0
        assert dataset.name
        assert dataset.version

    def test_iteration(self):
        """Dataset is iterable."""
        dataset = create_sample_dataset()
        queries = list(dataset)
        assert len(queries) == len(dataset)

    def test_json_round_trip(self):
        """Dataset survives JSON serialization."""
        dataset = create_sample_dataset()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            dataset.to_json(temp_path)
            loaded = GroundTruthDataset.from_json(temp_path)

            assert loaded.name == dataset.name
            assert loaded.version == dataset.version
            assert len(loaded) == len(dataset)

            for orig, loaded_q in zip(dataset.queries, loaded.queries):
                assert orig.query == loaded_q.query
                assert orig.intent == loaded_q.intent
                assert orig.difficulty == loaded_q.difficulty
        finally:
            temp_path.unlink()

    def test_filter_by_intent(self):
        """Filtering by intent works."""
        dataset = create_sample_dataset()
        filtered = dataset.filter_by_intent(QueryIntent.DEFINITION)

        assert all(q.intent == QueryIntent.DEFINITION for q in filtered)

    def test_filter_by_difficulty(self):
        """Filtering by difficulty works."""
        dataset = create_sample_dataset()
        filtered = dataset.filter_by_difficulty(QueryDifficulty.EASY)

        assert all(q.difficulty == QueryDifficulty.EASY for q in filtered)

    def test_exclude_out_of_scope(self):
        """Excluding out-of-scope queries works."""
        dataset = create_sample_dataset()
        filtered = dataset.exclude_out_of_scope()

        assert all(q.intent != QueryIntent.OUT_OF_SCOPE for q in filtered)

    def test_statistics(self):
        """Dataset statistics are computed correctly."""
        dataset = create_sample_dataset()
        stats = dataset.get_statistics()

        assert stats["total_queries"] == len(dataset)
        assert "by_intent" in stats
        assert "by_difficulty" in stats
        assert "avg_expected_docs" in stats


# =============================================================================
# Evaluator Tests
# =============================================================================


class TestRAGEvaluator:
    """Tests for RAGEvaluator class."""

    @pytest.fixture
    def mock_embedder(self):
        """Create mock embedder."""
        embedder = MagicMock()
        embedder.embed_query = AsyncMock(return_value=[0.1] * 1536)
        return embedder

    @pytest.fixture
    def mock_db_client(self):
        """Create mock database client."""
        client = MagicMock()
        client.hybrid_search = AsyncMock(
            return_value=[
                {"chunk_id": "chunk-1", "document_id": "doc-1", "similarity": 0.9},
                {"chunk_id": "chunk-2", "document_id": "doc-2", "similarity": 0.8},
                {"chunk_id": "chunk-3", "document_id": "doc-3", "similarity": 0.7},
            ]
        )
        return client

    @pytest.mark.asyncio
    async def test_evaluate_query(self, mock_db_client, mock_embedder):
        """Single query evaluation works."""
        from packages.core.evaluation.evaluator import RAGEvaluator

        evaluator = RAGEvaluator(mock_db_client, mock_embedder)

        ground_truth = QueryGroundTruth(
            query="Test query?",
            expected_doc_ids={"chunk-1", "chunk-3"},
            intent=QueryIntent.DEFINITION,
            difficulty=QueryDifficulty.EASY,
        )

        result = await evaluator.evaluate_query(ground_truth)

        assert result.query == "Test query?"
        assert result.metrics.hit_rate == 1.0  # chunk-1 found at position 1
        assert result.metrics.mrr == 1.0  # First relevant at position 1
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_evaluate_dataset(self, mock_db_client, mock_embedder):
        """Dataset evaluation works."""
        from packages.core.evaluation.evaluator import RAGEvaluator

        evaluator = RAGEvaluator(mock_db_client, mock_embedder)

        dataset = GroundTruthDataset(
            name="test",
            version="1.0",
            queries=[
                QueryGroundTruth(
                    query="Query 1?",
                    expected_doc_ids={"chunk-1"},
                    intent=QueryIntent.DEFINITION,
                    difficulty=QueryDifficulty.EASY,
                ),
                QueryGroundTruth(
                    query="Query 2?",
                    expected_doc_ids={"chunk-2"},
                    intent=QueryIntent.PROCEDURE,
                    difficulty=QueryDifficulty.MEDIUM,
                ),
            ],
        )

        report = await evaluator.evaluate_dataset(dataset)

        assert report.dataset_name == "test"
        assert report.total_queries == 2
        assert len(report.query_results) == 2
        assert "definition" in report.by_intent
        assert "procedure" in report.by_intent
        assert "easy" in report.by_difficulty
        assert "medium" in report.by_difficulty

    @pytest.mark.asyncio
    async def test_evaluate_dataset_excludes_out_of_scope(self, mock_db_client, mock_embedder):
        """Out-of-scope queries are excluded by default."""
        from packages.core.evaluation.evaluator import RAGEvaluator

        evaluator = RAGEvaluator(mock_db_client, mock_embedder)

        dataset = GroundTruthDataset(
            name="test",
            version="1.0",
            queries=[
                QueryGroundTruth(
                    query="In scope?",
                    expected_doc_ids={"chunk-1"},
                    intent=QueryIntent.DEFINITION,
                ),
                QueryGroundTruth(
                    query="Out of scope?",
                    expected_doc_ids=set(),
                    intent=QueryIntent.OUT_OF_SCOPE,
                ),
            ],
        )

        report = await evaluator.evaluate_dataset(dataset, include_out_of_scope=False)
        assert report.total_queries == 1

        report_with_oos = await evaluator.evaluate_dataset(dataset, include_out_of_scope=True)
        assert report_with_oos.total_queries == 2

    @pytest.mark.asyncio
    async def test_threshold_experiment(self, mock_db_client, mock_embedder):
        """Threshold experiment runs at multiple thresholds."""
        from packages.core.evaluation.evaluator import RAGEvaluator

        evaluator = RAGEvaluator(mock_db_client, mock_embedder)

        dataset = GroundTruthDataset(
            name="test",
            version="1.0",
            queries=[
                QueryGroundTruth(query="Test?", expected_doc_ids={"chunk-1"}),
            ],
        )

        results = await evaluator.run_threshold_experiment(dataset, thresholds=[0.2, 0.3, 0.4])

        assert len(results) == 3
        assert 0.2 in results
        assert 0.3 in results
        assert 0.4 in results

    @pytest.mark.asyncio
    async def test_report_summary(self, mock_db_client, mock_embedder):
        """Report summary is human-readable."""
        from packages.core.evaluation.evaluator import RAGEvaluator

        evaluator = RAGEvaluator(mock_db_client, mock_embedder)

        dataset = GroundTruthDataset(
            name="test",
            version="1.0",
            queries=[QueryGroundTruth(query="Test?", expected_doc_ids={"chunk-1"})],
        )

        report = await evaluator.evaluate_dataset(dataset)
        summary = report.summary()

        assert "test" in summary
        assert "Total queries: 1" in summary
        assert "MRR=" in summary

    @pytest.mark.asyncio
    async def test_report_to_dict(self, mock_db_client, mock_embedder):
        """Report can be serialized to dictionary."""
        from packages.core.evaluation.evaluator import RAGEvaluator

        evaluator = RAGEvaluator(mock_db_client, mock_embedder)

        dataset = GroundTruthDataset(
            name="test",
            version="1.0",
            queries=[QueryGroundTruth(query="Test?", expected_doc_ids={"chunk-1"})],
        )

        report = await evaluator.evaluate_dataset(dataset)
        d = report.to_dict()

        assert d["dataset_name"] == "test"
        assert d["total_queries"] == 1
        assert "aggregate_metrics" in d
        # Should be JSON-serializable
        json.dumps(d)
