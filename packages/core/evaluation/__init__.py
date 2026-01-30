"""RAG Evaluation Framework.

Provides tools for measuring retrieval quality using standard IR metrics:
- Precision@K: Relevant items in top K / K
- Recall@K: Relevant items in top K / total relevant
- MRR: 1 / rank of first relevant item
- NDCG@K: Rewards relevant items ranked higher
- Hit Rate: Did any relevant item appear in top K?

Usage:
    from packages.core.evaluation import RAGEvaluator, GroundTruthDataset

    dataset = GroundTruthDataset.from_json("data/evaluation/ground_truth.json")
    evaluator = RAGEvaluator(db_client, embedder)
    report = await evaluator.evaluate_dataset(dataset)
    print(report.summary())
"""

from packages.core.evaluation.evaluator import EvaluationReport, RAGEvaluator
from packages.core.evaluation.ground_truth import GroundTruthDataset, QueryGroundTruth
from packages.core.evaluation.metrics import (
    RetrievalMetrics,
    calculate_hit_rate,
    calculate_mrr,
    calculate_ndcg,
    calculate_precision_at_k,
    calculate_recall_at_k,
)

__all__ = [
    # Metrics
    "RetrievalMetrics",
    "calculate_precision_at_k",
    "calculate_recall_at_k",
    "calculate_mrr",
    "calculate_ndcg",
    "calculate_hit_rate",
    # Ground Truth
    "QueryGroundTruth",
    "GroundTruthDataset",
    # Evaluator
    "RAGEvaluator",
    "EvaluationReport",
]
