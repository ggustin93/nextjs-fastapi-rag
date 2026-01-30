"""RAG Evaluator for measuring retrieval quality.

Provides async evaluation of RAG pipelines against ground truth datasets,
following PydanticAI patterns for dependency injection.

Usage:
    from packages.core.evaluation import RAGEvaluator, GroundTruthDataset

    dataset = GroundTruthDataset.from_json("data/evaluation/ground_truth.json")
    evaluator = RAGEvaluator(db_client, embedder)

    # Evaluate full dataset
    report = await evaluator.evaluate_dataset(dataset)
    print(report.summary())

    # Find optimal similarity threshold
    results = await evaluator.run_threshold_experiment(dataset, [0.2, 0.25, 0.3])
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from packages.core.evaluation.ground_truth import (
    GroundTruthDataset,
    QueryDifficulty,
    QueryGroundTruth,
    QueryIntent,
)
from packages.core.evaluation.metrics import RetrievalMetrics, calculate_all_metrics

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    """Protocol for embedding generators (duck typing)."""

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query."""
        ...


class DBClient(Protocol):
    """Protocol for database clients with hybrid search (duck typing)."""

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        limit: int,
        similarity_threshold: float,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Execute hybrid search."""
        ...


@dataclass
class QueryEvaluationResult:
    """Evaluation result for a single query."""

    query: str
    metrics: RetrievalMetrics
    retrieved_ids: List[str]
    expected_ids: set[str]
    intent: QueryIntent
    difficulty: QueryDifficulty
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "metrics": self.metrics.to_dict(),
            "retrieved_count": len(self.retrieved_ids),
            "expected_count": len(self.expected_ids),
            "intent": self.intent.value,
            "difficulty": self.difficulty.value,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class EvaluationReport:
    """Comprehensive evaluation report with aggregate metrics.

    Provides overall metrics plus breakdowns by intent and difficulty.
    """

    dataset_name: str
    total_queries: int
    aggregate_metrics: RetrievalMetrics
    by_intent: Dict[str, RetrievalMetrics] = field(default_factory=dict)
    by_difficulty: Dict[str, RetrievalMetrics] = field(default_factory=dict)
    query_results: List[QueryEvaluationResult] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    avg_latency_ms: float = 0.0

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"=== RAG Evaluation Report: {self.dataset_name} ===",
            f"Total queries: {self.total_queries}",
            f"Parameters: {self.parameters}",
            f"Avg latency: {self.avg_latency_ms:.0f}ms",
            "",
            "Overall Metrics:",
            f"  {self.aggregate_metrics}",
            "",
        ]

        if self.by_intent:
            lines.append("By Intent:")
            for intent, metrics in sorted(self.by_intent.items()):
                lines.append(f"  {intent}: {metrics}")
            lines.append("")

        if self.by_difficulty:
            lines.append("By Difficulty:")
            for diff, metrics in sorted(self.by_difficulty.items()):
                lines.append(f"  {diff}: {metrics}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "dataset_name": self.dataset_name,
            "total_queries": self.total_queries,
            "aggregate_metrics": self.aggregate_metrics.to_dict(),
            "by_intent": {k: v.to_dict() for k, v in self.by_intent.items()},
            "by_difficulty": {k: v.to_dict() for k, v in self.by_difficulty.items()},
            "parameters": self.parameters,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "query_results": [r.to_dict() for r in self.query_results],
        }


class RAGEvaluator:
    """Evaluator for RAG retrieval quality.

    Uses dependency injection for database client and embedder,
    following PydanticAI patterns.

    Args:
        db_client: Database client with hybrid_search method
        embedder: Embedding generator with embed_query method
        default_k: Default K for @K metrics (default: 10)
        default_limit: Default search result limit (default: 30)
    """

    def __init__(
        self,
        db_client: DBClient,
        embedder: Embedder,
        default_k: int = 10,
        default_limit: int = 30,
    ):
        self.db_client = db_client
        self.embedder = embedder
        self.default_k = default_k
        self.default_limit = default_limit

    async def evaluate_query(
        self,
        ground_truth: QueryGroundTruth,
        similarity_threshold: float = 0.25,
        limit: Optional[int] = None,
        k: Optional[int] = None,
        **search_kwargs,
    ) -> QueryEvaluationResult:
        """Evaluate a single query against ground truth.

        Args:
            ground_truth: Query with expected relevant document IDs
            similarity_threshold: Minimum similarity for retrieval
            limit: Maximum results to retrieve
            k: K for @K metrics
            **search_kwargs: Additional arguments for hybrid_search

        Returns:
            QueryEvaluationResult with metrics
        """
        import time

        limit = limit or self.default_limit
        k = k or self.default_k

        start_time = time.perf_counter()

        # Generate embedding
        query_embedding = await self.embedder.embed_query(ground_truth.query)

        # Execute search
        results = await self.db_client.hybrid_search(
            query_text=ground_truth.query,
            query_embedding=query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
            **search_kwargs,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Extract retrieved IDs (use chunk_id or document_id based on ground truth format)
        # Prefer chunk_id for chunk-level evaluation, document_id for doc-level
        retrieved_ids = []
        for r in results:
            # Check both chunk_id and document_id
            if "chunk_id" in r and r["chunk_id"]:
                retrieved_ids.append(str(r["chunk_id"]))
            elif "document_id" in r and r["document_id"]:
                retrieved_ids.append(str(r["document_id"]))

        # Calculate metrics
        metrics = calculate_all_metrics(
            retrieved_ids=retrieved_ids,
            relevant_ids=ground_truth.expected_doc_ids,
            k=k,
        )

        return QueryEvaluationResult(
            query=ground_truth.query,
            metrics=metrics,
            retrieved_ids=retrieved_ids,
            expected_ids=ground_truth.expected_doc_ids,
            intent=ground_truth.intent,
            difficulty=ground_truth.difficulty,
            latency_ms=latency_ms,
        )

    async def evaluate_dataset(
        self,
        dataset: GroundTruthDataset,
        similarity_threshold: float = 0.25,
        limit: Optional[int] = None,
        k: Optional[int] = None,
        include_out_of_scope: bool = False,
        **search_kwargs,
    ) -> EvaluationReport:
        """Evaluate entire dataset and generate comprehensive report.

        Args:
            dataset: Ground truth dataset to evaluate
            similarity_threshold: Minimum similarity for retrieval
            limit: Maximum results to retrieve per query
            k: K for @K metrics
            include_out_of_scope: Whether to include out-of-scope queries
            **search_kwargs: Additional arguments for hybrid_search

        Returns:
            EvaluationReport with aggregate and stratified metrics
        """
        k = k or self.default_k
        limit = limit or self.default_limit

        # Filter dataset if needed
        eval_dataset = dataset if include_out_of_scope else dataset.exclude_out_of_scope()

        if not eval_dataset.queries:
            logger.warning("Empty dataset after filtering")
            return EvaluationReport(
                dataset_name=dataset.name,
                total_queries=0,
                aggregate_metrics=RetrievalMetrics(0, 0, 0, 0, 0, k),
                parameters={
                    "similarity_threshold": similarity_threshold,
                    "limit": limit,
                    "k": k,
                },
            )

        # Evaluate all queries
        logger.info(f"Evaluating {len(eval_dataset)} queries from {dataset.name}")
        results: List[QueryEvaluationResult] = []

        for ground_truth in eval_dataset:
            result = await self.evaluate_query(
                ground_truth=ground_truth,
                similarity_threshold=similarity_threshold,
                limit=limit,
                k=k,
                **search_kwargs,
            )
            results.append(result)

        # Compute aggregate metrics
        aggregate = self._aggregate_metrics(results, k)

        # Compute by-intent metrics
        by_intent = {}
        for intent in QueryIntent:
            intent_results = [r for r in results if r.intent == intent]
            if intent_results:
                by_intent[intent.value] = self._aggregate_metrics(intent_results, k)

        # Compute by-difficulty metrics
        by_difficulty = {}
        for diff in QueryDifficulty:
            diff_results = [r for r in results if r.difficulty == diff]
            if diff_results:
                by_difficulty[diff.value] = self._aggregate_metrics(diff_results, k)

        # Compute average latency
        avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0

        return EvaluationReport(
            dataset_name=dataset.name,
            total_queries=len(results),
            aggregate_metrics=aggregate,
            by_intent=by_intent,
            by_difficulty=by_difficulty,
            query_results=results,
            parameters={
                "similarity_threshold": similarity_threshold,
                "limit": limit,
                "k": k,
                **search_kwargs,
            },
            avg_latency_ms=avg_latency,
        )

    def _aggregate_metrics(self, results: List[QueryEvaluationResult], k: int) -> RetrievalMetrics:
        """Compute average metrics across multiple query results."""
        if not results:
            return RetrievalMetrics(0, 0, 0, 0, 0, k)

        n = len(results)
        return RetrievalMetrics(
            precision_at_k=sum(r.metrics.precision_at_k for r in results) / n,
            recall_at_k=sum(r.metrics.recall_at_k for r in results) / n,
            mrr=sum(r.metrics.mrr for r in results) / n,
            ndcg_at_k=sum(r.metrics.ndcg_at_k for r in results) / n,
            hit_rate=sum(r.metrics.hit_rate for r in results) / n,
            k=k,
        )

    async def run_threshold_experiment(
        self,
        dataset: GroundTruthDataset,
        thresholds: List[float],
        **eval_kwargs,
    ) -> Dict[float, EvaluationReport]:
        """Run evaluation at multiple similarity thresholds.

        Useful for finding optimal threshold that balances precision and recall.

        Args:
            dataset: Ground truth dataset to evaluate
            thresholds: List of similarity thresholds to test
            **eval_kwargs: Additional arguments for evaluate_dataset

        Returns:
            Dictionary mapping threshold to evaluation report

        Example:
            results = await evaluator.run_threshold_experiment(
                dataset, [0.2, 0.25, 0.3, 0.35]
            )
            for threshold, report in results.items():
                print(f"Threshold {threshold}: MRR={report.aggregate_metrics.mrr:.3f}")
        """
        logger.info(f"Running threshold experiment with {len(thresholds)} values")

        results = {}
        for threshold in sorted(thresholds):
            logger.info(f"Evaluating at threshold={threshold}")
            report = await self.evaluate_dataset(
                dataset=dataset,
                similarity_threshold=threshold,
                **eval_kwargs,
            )
            results[threshold] = report

        # Log summary
        logger.info("Threshold experiment results:")
        for threshold, report in results.items():
            logger.info(
                f"  {threshold:.2f}: "
                f"MRR={report.aggregate_metrics.mrr:.3f} "
                f"Recall={report.aggregate_metrics.recall_at_k:.3f} "
                f"Precision={report.aggregate_metrics.precision_at_k:.3f}"
            )

        return results


async def main():
    """Example usage of RAG evaluator (for testing)."""
    from packages.core.evaluation.ground_truth import create_sample_dataset

    # Create sample dataset
    dataset = create_sample_dataset()
    print(dataset.summary())
    print()

    # Save to file for reference
    dataset.to_json("data/evaluation/sample_ground_truth.json")
    print("Saved sample dataset to data/evaluation/sample_ground_truth.json")


if __name__ == "__main__":
    asyncio.run(main())
