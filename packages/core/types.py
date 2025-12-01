from dataclasses import dataclass, field
from typing import Any, Optional

from packages.core.config import DomainConfig
from packages.utils.supabase_client import SupabaseRestClient


@dataclass
class WeatherConfig:
    """Weather API configuration."""

    base_url: str = "https://api.open-meteo.com/v1/forecast"
    geocode_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    cache_ttl_seconds: int = 900  # 15 minutes
    timeout_seconds: int = 5
    temperature_unit: str = "celsius"


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
    domain_config: Optional[DomainConfig] = None
    weather_config: WeatherConfig = field(default_factory=WeatherConfig)
    last_search_sources: list = field(default_factory=list)
    cited_source_indices: set[int] = field(default_factory=set)
    # External API configs can be added optionally:
    # external_api_config: Optional[ExternalAPIConfig] = None
