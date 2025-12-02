from dataclasses import dataclass, field
from typing import Any, Optional

from packages.config import WeatherToolConfig
from packages.utils.supabase_client import SupabaseRestClient

# Alias for backward compatibility - WeatherToolConfig is the canonical version
WeatherConfig = WeatherToolConfig


@dataclass
class RAGContext:
    """RAG agent runtime context with dependency injection.

    All dependencies are initialized once and reused across search operations
    to avoid repeated client/model initialization overhead.

    Note: Reranker was removed - hybrid search with RRF provides good ranking.
    See docs/TROUBLESHOOT.md for evidence that reranking hurt accuracy.
    """

    db_client: SupabaseRestClient
    embedder: Optional[Any] = None  # Cached EmbeddingGenerator for query embedding
    weather_config: WeatherToolConfig = field(default_factory=WeatherToolConfig)
    last_search_sources: list = field(default_factory=list)
    cited_source_indices: set[int] = field(default_factory=set)
