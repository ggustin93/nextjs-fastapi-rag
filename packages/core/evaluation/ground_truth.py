"""Ground truth dataset management for RAG evaluation.

Provides data structures and utilities for managing evaluation datasets
with queries and their expected relevant documents/chunks.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """Classification of query intent for stratified evaluation."""

    DEFINITION = "definition"  # "C'est quoi un type A?"
    PROCEDURE = "procedure"  # "Comment obtenir un permis?"
    DEADLINE = "deadline"  # "Quel est le délai?"
    CONTACT = "contact"  # "Qui contacter pour...?"
    LOCATION = "location"  # "Où se trouve...?"
    COMPARISON = "comparison"  # "Quelle différence entre...?"
    TROUBLESHOOTING = "troubleshooting"  # "Pourquoi mon dossier est refusé?"
    OUT_OF_SCOPE = "out_of_scope"  # Questions outside knowledge base


class QueryDifficulty(str, Enum):
    """Difficulty level for stratified evaluation."""

    EASY = "easy"  # Direct keyword match likely
    MEDIUM = "medium"  # Requires semantic understanding
    HARD = "hard"  # Requires multi-hop reasoning or rare vocabulary


@dataclass
class QueryGroundTruth:
    """Ground truth for a single evaluation query.

    Attributes:
        query: The search query text
        expected_doc_ids: Set of document/chunk IDs that are relevant
        intent: Classification of query intent
        difficulty: Difficulty level of the query
        notes: Optional notes about the query (e.g., why it's hard)
        metadata: Additional metadata for filtering/grouping
    """

    query: str
    expected_doc_ids: Set[str]
    intent: QueryIntent = QueryIntent.DEFINITION
    difficulty: QueryDifficulty = QueryDifficulty.MEDIUM
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryGroundTruth":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            query=data["query"],
            expected_doc_ids=set(data.get("expected_doc_ids", [])),
            intent=QueryIntent(data.get("intent", "definition")),
            difficulty=QueryDifficulty(data.get("difficulty", "medium")),
            notes=data.get("notes"),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (JSON serialization)."""
        result = {
            "query": self.query,
            "expected_doc_ids": list(self.expected_doc_ids),
            "intent": self.intent.value,
            "difficulty": self.difficulty.value,
        }
        if self.notes:
            result["notes"] = self.notes
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class GroundTruthDataset:
    """Collection of ground truth queries for evaluation.

    Attributes:
        name: Dataset name/identifier
        version: Dataset version string
        description: Human-readable description
        queries: List of ground truth queries
        metadata: Additional dataset metadata
    """

    name: str
    version: str
    queries: List[QueryGroundTruth]
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.queries)

    def __iter__(self) -> Iterator[QueryGroundTruth]:
        return iter(self.queries)

    def __getitem__(self, index: int) -> QueryGroundTruth:
        return self.queries[index]

    @classmethod
    def from_json(cls, path: str | Path) -> "GroundTruthDataset":
        """Load dataset from JSON file.

        Expected JSON format:
        {
            "name": "dataset_name",
            "version": "1.0",
            "description": "Optional description",
            "queries": [
                {
                    "query": "Question text",
                    "expected_doc_ids": ["doc-id-1", "doc-id-2"],
                    "intent": "definition",
                    "difficulty": "easy",
                    "notes": "Optional notes"
                }
            ]
        }
        """
        path = Path(path)
        logger.info(f"Loading ground truth dataset from {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        queries = [QueryGroundTruth.from_dict(q) for q in data.get("queries", [])]

        return cls(
            name=data.get("name", path.stem),
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            queries=queries,
            metadata=data.get("metadata", {}),
        )

    def to_json(self, path: str | Path) -> None:
        """Save dataset to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "queries": [q.to_dict() for q in self.queries],
            "metadata": self.metadata,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved ground truth dataset to {path}")

    def filter_by_intent(self, intent: QueryIntent) -> "GroundTruthDataset":
        """Return subset filtered by query intent."""
        filtered = [q for q in self.queries if q.intent == intent]
        return GroundTruthDataset(
            name=f"{self.name}_{intent.value}",
            version=self.version,
            description=f"Filtered by intent: {intent.value}",
            queries=filtered,
            metadata={**self.metadata, "filter_intent": intent.value},
        )

    def filter_by_difficulty(self, difficulty: QueryDifficulty) -> "GroundTruthDataset":
        """Return subset filtered by difficulty level."""
        filtered = [q for q in self.queries if q.difficulty == difficulty]
        return GroundTruthDataset(
            name=f"{self.name}_{difficulty.value}",
            version=self.version,
            description=f"Filtered by difficulty: {difficulty.value}",
            queries=filtered,
            metadata={**self.metadata, "filter_difficulty": difficulty.value},
        )

    def exclude_out_of_scope(self) -> "GroundTruthDataset":
        """Return subset excluding out-of-scope queries."""
        filtered = [q for q in self.queries if q.intent != QueryIntent.OUT_OF_SCOPE]
        return GroundTruthDataset(
            name=f"{self.name}_in_scope",
            version=self.version,
            description="Filtered to in-scope queries only",
            queries=filtered,
            metadata={**self.metadata, "exclude_out_of_scope": True},
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics."""
        intent_counts = {}
        difficulty_counts = {}

        for q in self.queries:
            intent_counts[q.intent.value] = intent_counts.get(q.intent.value, 0) + 1
            difficulty_counts[q.difficulty.value] = difficulty_counts.get(q.difficulty.value, 0) + 1

        return {
            "total_queries": len(self.queries),
            "by_intent": intent_counts,
            "by_difficulty": difficulty_counts,
            "avg_expected_docs": (
                sum(len(q.expected_doc_ids) for q in self.queries) / len(self.queries)
                if self.queries
                else 0
            ),
        }

    def add_query(self, query: QueryGroundTruth) -> None:
        """Add a query to the dataset."""
        self.queries.append(query)

    def summary(self) -> str:
        """Human-readable dataset summary."""
        stats = self.get_statistics()
        lines = [
            f"Dataset: {self.name} v{self.version}",
            f"Description: {self.description}" if self.description else "",
            f"Total queries: {stats['total_queries']}",
            "By intent:",
        ]
        for intent, count in stats["by_intent"].items():
            lines.append(f"  - {intent}: {count}")
        lines.append("By difficulty:")
        for diff, count in stats["by_difficulty"].items():
            lines.append(f"  - {diff}: {count}")
        lines.append(f"Avg expected docs per query: {stats['avg_expected_docs']:.1f}")
        return "\n".join(filter(None, lines))


def create_sample_dataset() -> GroundTruthDataset:
    """Create a sample ground truth dataset for French RAG evaluation.

    This is a template dataset. In production, you should:
    1. Run queries against your indexed documents
    2. Manually verify and annotate relevant chunks
    3. Build the expected_doc_ids from actual database UUIDs

    Returns:
        Sample GroundTruthDataset for testing the evaluation framework
    """
    queries = [
        QueryGroundTruth(
            query="C'est quoi un chantier de type A?",
            expected_doc_ids={"placeholder-type-a-doc"},  # Replace with actual UUIDs
            intent=QueryIntent.DEFINITION,
            difficulty=QueryDifficulty.EASY,
            notes="Direct definition query, should match title",
        ),
        QueryGroundTruth(
            query="Quelle est la différence entre type D et type E?",
            expected_doc_ids={"placeholder-type-d-doc", "placeholder-type-e-doc"},
            intent=QueryIntent.COMPARISON,
            difficulty=QueryDifficulty.MEDIUM,
            notes="Requires retrieving info from multiple documents",
        ),
        QueryGroundTruth(
            query="Comment faire une demande de permis d'urbanisme?",
            expected_doc_ids={"placeholder-procedure-doc"},
            intent=QueryIntent.PROCEDURE,
            difficulty=QueryDifficulty.MEDIUM,
        ),
        QueryGroundTruth(
            query="Quel est le délai pour une occupation de voirie?",
            expected_doc_ids={"placeholder-deadline-doc"},
            intent=QueryIntent.DEADLINE,
            difficulty=QueryDifficulty.EASY,
        ),
        QueryGroundTruth(
            query="Qui contacter en cas de problème avec Osiris?",
            expected_doc_ids={"placeholder-contact-doc"},
            intent=QueryIntent.CONTACT,
            difficulty=QueryDifficulty.EASY,
        ),
        QueryGroundTruth(
            query="Comment fonctionne le système de coordonnées Lambert?",
            expected_doc_ids=set(),  # Empty = out of scope
            intent=QueryIntent.OUT_OF_SCOPE,
            difficulty=QueryDifficulty.HARD,
            notes="Technical GIS question outside knowledge base scope",
        ),
        QueryGroundTruth(
            query="Quelle est la capitale de la Belgique?",
            expected_doc_ids=set(),
            intent=QueryIntent.OUT_OF_SCOPE,
            difficulty=QueryDifficulty.EASY,
            notes="General knowledge question, not in domain",
        ),
    ]

    return GroundTruthDataset(
        name="french_rag_evaluation_sample",
        version="1.0",
        description="Sample evaluation dataset for French RAG system (Osiris/Brussels worksites)",
        queries=queries,
        metadata={
            "language": "fr",
            "domain": "urban_planning",
            "created_by": "evaluation_framework",
        },
    )
