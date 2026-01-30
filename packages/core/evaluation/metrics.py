"""Standard Information Retrieval metrics for RAG evaluation.

Implements standard IR metrics for measuring retrieval quality:
- Precision@K: Fraction of retrieved items that are relevant
- Recall@K: Fraction of relevant items that were retrieved
- MRR (Mean Reciprocal Rank): Average of 1/rank of first relevant item
- NDCG@K (Normalized Discounted Cumulative Gain): Rewards relevant items ranked higher
- Hit Rate: Binary indicator of whether any relevant item was retrieved
"""

import math
from dataclasses import dataclass
from typing import List, Set, Union


@dataclass(frozen=True)
class RetrievalMetrics:
    """Container for retrieval evaluation metrics.

    All metrics are in [0, 1] range where higher is better.
    """

    precision_at_k: float
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    hit_rate: float
    k: int  # The K value used for @K metrics

    def to_dict(self) -> dict:
        """Convert to dictionary with formatted metric names."""
        return {
            f"precision@{self.k}": round(self.precision_at_k, 4),
            f"recall@{self.k}": round(self.recall_at_k, 4),
            "mrr": round(self.mrr, 4),
            f"ndcg@{self.k}": round(self.ndcg_at_k, 4),
            f"hit_rate@{self.k}": round(self.hit_rate, 4),
        }

    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"P@{self.k}={self.precision_at_k:.3f} "
            f"R@{self.k}={self.recall_at_k:.3f} "
            f"MRR={self.mrr:.3f} "
            f"NDCG@{self.k}={self.ndcg_at_k:.3f} "
            f"Hit@{self.k}={self.hit_rate:.3f}"
        )


def _to_set(items: Union[List[str], Set[str]]) -> Set[str]:
    """Convert list to set if needed."""
    return set(items) if isinstance(items, list) else items


def calculate_precision_at_k(
    retrieved_ids: List[str],
    relevant_ids: Union[List[str], Set[str]],
    k: int,
) -> float:
    """Calculate Precision@K: fraction of top-K retrieved items that are relevant.

    Precision@K = |relevant ∩ retrieved[:k]| / k

    Args:
        retrieved_ids: Ordered list of retrieved document/chunk IDs
        relevant_ids: Set or list of ground truth relevant IDs
        k: Number of top results to consider

    Returns:
        Precision score in [0, 1]

    Example:
        >>> calculate_precision_at_k(['a', 'b', 'c', 'd'], {'a', 'c'}, k=4)
        0.5  # 2 relevant in top 4
    """
    if k <= 0:
        return 0.0

    relevant_set = _to_set(relevant_ids)
    retrieved_at_k = retrieved_ids[:k]

    if not retrieved_at_k:
        return 0.0

    relevant_retrieved = sum(1 for doc_id in retrieved_at_k if doc_id in relevant_set)
    return relevant_retrieved / k


def calculate_recall_at_k(
    retrieved_ids: List[str],
    relevant_ids: Union[List[str], Set[str]],
    k: int,
) -> float:
    """Calculate Recall@K: fraction of all relevant items that were retrieved in top-K.

    Recall@K = |relevant ∩ retrieved[:k]| / |relevant|

    Args:
        retrieved_ids: Ordered list of retrieved document/chunk IDs
        relevant_ids: Set or list of ground truth relevant IDs
        k: Number of top results to consider

    Returns:
        Recall score in [0, 1]

    Example:
        >>> calculate_recall_at_k(['a', 'b', 'c'], {'a', 'c', 'e'}, k=3)
        0.667  # 2 of 3 relevant items found
    """
    relevant_set = _to_set(relevant_ids)

    if not relevant_set:
        return 1.0  # No relevant items means perfect recall by definition

    if k <= 0:
        return 0.0

    retrieved_at_k = set(retrieved_ids[:k])
    relevant_retrieved = len(relevant_set & retrieved_at_k)

    return relevant_retrieved / len(relevant_set)


def calculate_mrr(
    retrieved_ids: List[str],
    relevant_ids: Union[List[str], Set[str]],
) -> float:
    """Calculate Mean Reciprocal Rank: 1 / rank of first relevant item.

    MRR = 1 / rank_of_first_relevant_item

    This metric is useful when only the first relevant result matters
    (e.g., navigational queries, factoid questions).

    Args:
        retrieved_ids: Ordered list of retrieved document/chunk IDs
        relevant_ids: Set or list of ground truth relevant IDs

    Returns:
        MRR score in [0, 1], or 0 if no relevant item found

    Example:
        >>> calculate_mrr(['a', 'b', 'c', 'd'], {'c', 'e'})
        0.333  # First relevant item at position 3
    """
    relevant_set = _to_set(relevant_ids)

    if not relevant_set:
        return 1.0  # No relevant items means perfect score

    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_set:
            return 1.0 / rank

    return 0.0  # No relevant item found


def calculate_ndcg(
    retrieved_ids: List[str],
    relevant_ids: Union[List[str], Set[str]],
    k: int,
) -> float:
    """Calculate Normalized Discounted Cumulative Gain at K.

    NDCG rewards having relevant items ranked higher. Uses binary relevance
    (1 if relevant, 0 otherwise).

    DCG@K = Σ(rel_i / log2(i + 1)) for i in 1..K
    NDCG@K = DCG@K / IDCG@K (ideal DCG)

    Args:
        retrieved_ids: Ordered list of retrieved document/chunk IDs
        relevant_ids: Set or list of ground truth relevant IDs
        k: Number of top results to consider

    Returns:
        NDCG score in [0, 1]

    Example:
        >>> calculate_ndcg(['a', 'b', 'c', 'd'], {'a', 'd'}, k=4)
        0.765  # Relevant items at positions 1 and 4
    """
    if k <= 0:
        return 0.0

    relevant_set = _to_set(relevant_ids)

    if not relevant_set:
        return 1.0  # No relevant items means perfect score

    # Calculate DCG
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        if doc_id in relevant_set:
            # Binary relevance: rel_i = 1 if relevant, 0 otherwise
            # Using log2(i + 2) because i is 0-indexed
            dcg += 1.0 / math.log2(i + 2)

    # Calculate IDCG (ideal DCG with all relevant items at top)
    num_relevant = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(num_relevant))

    if idcg == 0:
        return 0.0

    return dcg / idcg


def calculate_hit_rate(
    retrieved_ids: List[str],
    relevant_ids: Union[List[str], Set[str]],
    k: int,
) -> float:
    """Calculate Hit Rate@K: binary indicator if any relevant item in top-K.

    Hit Rate = 1 if |relevant ∩ retrieved[:k]| > 0, else 0

    Simple pass/fail metric useful for measuring basic retrieval success.

    Args:
        retrieved_ids: Ordered list of retrieved document/chunk IDs
        relevant_ids: Set or list of ground truth relevant IDs
        k: Number of top results to consider

    Returns:
        1.0 if at least one relevant item in top-K, else 0.0

    Example:
        >>> calculate_hit_rate(['a', 'b', 'c'], {'c', 'e'}, k=3)
        1.0  # Found 'c' in top 3
    """
    if k <= 0:
        return 0.0

    relevant_set = _to_set(relevant_ids)

    if not relevant_set:
        return 1.0  # No relevant items means automatic hit

    for doc_id in retrieved_ids[:k]:
        if doc_id in relevant_set:
            return 1.0

    return 0.0


def calculate_all_metrics(
    retrieved_ids: List[str],
    relevant_ids: Union[List[str], Set[str]],
    k: int = 10,
) -> RetrievalMetrics:
    """Calculate all retrieval metrics at once.

    Convenience function to compute all metrics in a single call.

    Args:
        retrieved_ids: Ordered list of retrieved document/chunk IDs
        relevant_ids: Set or list of ground truth relevant IDs
        k: Number of top results to consider for @K metrics

    Returns:
        RetrievalMetrics dataclass with all metrics
    """
    return RetrievalMetrics(
        precision_at_k=calculate_precision_at_k(retrieved_ids, relevant_ids, k),
        recall_at_k=calculate_recall_at_k(retrieved_ids, relevant_ids, k),
        mrr=calculate_mrr(retrieved_ids, relevant_ids),
        ndcg_at_k=calculate_ndcg(retrieved_ids, relevant_ids, k),
        hit_rate=calculate_hit_rate(retrieved_ids, relevant_ids, k),
        k=k,
    )
