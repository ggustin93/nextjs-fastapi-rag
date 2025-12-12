"""Centralized configuration management for nextjs-fastapi-rag.

This module provides type-safe configuration with environment variable support
and sensible defaults. Supports multiple LLM providers including OpenAI,
Chutes.ai (Bittensor), Ollama, and any OpenAI-compatible API.

Usage:
    from packages.config import settings

    # Access domain configs
    model = settings.llm.create_model()  # For PydanticAI Agent
    batch_size = settings.embedding.batch_size
    origins = settings.api.cors_origins

Environment Variables:
    See .env.example for full documentation of available settings.
"""

# Load .env BEFORE any settings are read (must be first)
from dotenv import load_dotenv

load_dotenv()

import os  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from functools import lru_cache  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import List, Optional, Union  # noqa: E402

from packages.utils.prompt_loader import load_prompt  # noqa: E402

# Project root is 2 levels up from packages/config/__init__.py
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


def _get_clean_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with validation and comment stripping.

    Handles common .env file issues:
    - Strips whitespace
    - Treats comment-only values as None
    - Validates no invalid characters like '#' in actual values

    Args:
        key: Environment variable name
        default: Default value if not found or invalid

    Returns:
        Cleaned value or default
    """
    value = os.getenv(key)

    if not value:
        return default

    # Strip whitespace
    value = value.strip()

    # Treat empty or comment-only values as None
    if not value or value.startswith("#"):
        return default

    # Validate no inline comments (invalid API keys)
    if "#" in value:
        # Log warning but return default instead of failing
        import logging

        logging.warning(
            f"Environment variable {key} contains '#' - likely malformed comment. "
            f"Using default value. Check your .env file."
        )
        return default

    return value


# Minimal fallback system prompt (full prompt loaded from config/prompts/system_prompt.txt)
# This is only used if no custom prompt file is found
DEFAULT_SYSTEM_PROMPT_FALLBACK = """You are a knowledge base assistant.

You answer questions ONLY from your organization's knowledge base.
You are NOT a general assistant.

AVAILABLE TOOLS:
1. search_knowledge_base: Search the knowledge base

RULES:
- Always call search_knowledge_base before answering
- Only use information from the search results
- Cite sources with [1], [2], etc.
- If no relevant results, politely refuse

For detailed customization, create: config/prompts/system_prompt.txt"""


def _load_system_prompt() -> str:
    """Load system prompt from file with fallback.

    Search order:
    1. RAG_SYSTEM_PROMPT env var (full content)
    2. RAG_SYSTEM_PROMPT_FILE env var (file path)
    3. config/prompts/system_prompt.txt (default location)
    4. Built-in minimal fallback
    """
    return load_prompt(
        default_prompt=DEFAULT_SYSTEM_PROMPT_FALLBACK,
        prompt_name="system_prompt",
        env_var_content="RAG_SYSTEM_PROMPT",
        env_var_file="RAG_SYSTEM_PROMPT_FILE",
        default_path=PROJECT_ROOT / "config" / "prompts" / "system_prompt.txt",
    )


@dataclass(frozen=True)
class LLMConfig:
    """LLM model configuration with multi-provider support.

    Supports OpenAI, Chutes.ai, Ollama, and any OpenAI-compatible API.

    Environment Variables:
        LLM_PROVIDER: Provider name for model identifier (default: "openai")
        LLM_MODEL: Model name (default: "gpt-4o-mini")
        LLM_BASE_URL: Custom API base URL for OpenAI-compatible APIs
        LLM_API_KEY: API key (falls back to OPENAI_API_KEY)
        RAG_SYSTEM_PROMPT: Custom system prompt for RAG agent (optional)

    Example - Chutes.ai:
        LLM_BASE_URL=https://myuser-my-chute.chutes.ai/v1
        LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
        LLM_API_KEY=your-chutes-api-key

    Example - Custom prompt:
        RAG_SYSTEM_PROMPT="Tu es un expert juridique belge..."
    """

    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", os.getenv("LLM_CHOICE", "gpt-4"))
    )
    base_url: Optional[str] = field(default_factory=lambda: os.getenv("LLM_BASE_URL"))
    api_key: Optional[str] = field(
        default_factory=lambda: _get_clean_env("LLM_API_KEY") or _get_clean_env("OPENAI_API_KEY")
    )
    system_prompt: str = field(default_factory=_load_system_prompt)

    @property
    def model_identifier(self) -> str:
        """Get model identifier in provider:model format.

        Used for simple Agent() instantiation when not using custom provider.
        """
        return f"{self.provider}:{self.model}"

    def create_model(self) -> Union[str, "OpenAIModel"]:  # noqa: F821
        """Create PydanticAI model with proper provider configuration.

        Returns OpenAIModel with custom provider if LLM_BASE_URL is set,
        otherwise returns model_identifier string for default OpenAI behavior.

        This method enables seamless support for:
        - Chutes.ai (Bittensor decentralized AI)
        - Ollama (local models)
        - Any OpenAI-compatible API

        Returns:
            Either a model identifier string or OpenAIModel instance.
        """
        # If custom base_url is set, use OpenAIProvider with that URL
        if self.base_url:
            from pydantic_ai.models.openai import OpenAIModel
            from pydantic_ai.providers.openai import OpenAIProvider

            provider = OpenAIProvider(
                base_url=self.base_url,
                api_key=self.api_key or "api-key-not-set",
            )
            return OpenAIModel(self.model, provider=provider)

        # Otherwise, return model identifier for default behavior
        return self.model_identifier


@dataclass(frozen=True)
class EmbeddingConfig:
    """Embedding model configuration with multi-provider support.

    Supports OpenAI, Chutes.ai, Ollama, and any OpenAI-compatible API.

    Environment Variables:
        EMBEDDING_MODEL: Model name (default: "text-embedding-3-small")
        EMBEDDING_BASE_URL: Custom API base URL for OpenAI-compatible APIs
        EMBEDDING_API_KEY: API key (falls back to LLM_API_KEY, then OPENAI_API_KEY)
        EMBEDDING_BATCH_SIZE: Batch size for processing (default: 100)
        EMBEDDING_MAX_RETRIES: Max retry attempts (default: 3)
        EMBEDDING_RETRY_DELAY: Delay between retries in seconds (default: 1.0)
        EMBEDDING_CACHE_MAX_SIZE: Max cache entries (default: 1000)
        EMBEDDING_TOKENIZER_MODEL: Tokenizer for chunking (default: "sentence-transformers/all-MiniLM-L6-v2")

    Example - Chutes.ai embeddings:
        EMBEDDING_BASE_URL=https://myuser-my-chute.chutes.ai/v1
        EMBEDDING_MODEL=your-embedding-model
        EMBEDDING_API_KEY=your-chutes-api-key
    """

    model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    )
    base_url: Optional[str] = field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL"))
    api_key: Optional[str] = field(
        default_factory=lambda: (
            _get_clean_env("EMBEDDING_API_KEY")
            or _get_clean_env("LLM_API_KEY")
            or _get_clean_env("OPENAI_API_KEY")
        )
    )
    batch_size: int = field(default_factory=lambda: int(os.getenv("EMBEDDING_BATCH_SIZE", "100")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("EMBEDDING_MAX_RETRIES", "3")))
    retry_delay: float = field(
        default_factory=lambda: float(os.getenv("EMBEDDING_RETRY_DELAY", "1.0"))
    )
    cache_max_size: int = field(
        default_factory=lambda: int(os.getenv("EMBEDDING_CACHE_MAX_SIZE", "1000"))
    )
    tokenizer_model: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_TOKENIZER_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
    )


@dataclass(frozen=True)
class DatabaseConfig:
    """Database connection pool configuration.

    Environment Variables:
        DB_POOL_MIN_SIZE: Minimum pool connections (default: 1)
        DB_POOL_MAX_SIZE: Maximum pool connections (default: 5)
        DB_COMMAND_TIMEOUT: Command timeout in seconds (default: 60)
        DB_CONNECTION_TIMEOUT: Connection timeout in seconds (default: 30)
    """

    pool_min_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_MIN_SIZE", "1")))
    pool_max_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_MAX_SIZE", "5")))
    command_timeout: int = field(default_factory=lambda: int(os.getenv("DB_COMMAND_TIMEOUT", "60")))
    connection_timeout: int = field(
        default_factory=lambda: int(os.getenv("DB_CONNECTION_TIMEOUT", "30"))
    )


@dataclass(frozen=True)
class ChunkingConfig:
    """Document chunking configuration.

    Environment Variables:
        CHUNK_SIZE: Target chunk size in characters (default: 1000)
        CHUNK_OVERLAP: Overlap between chunks (default: 200)
        CHUNK_MAX_SIZE: Maximum chunk size (default: 2000)
        CHUNK_MIN_SIZE: Minimum chunk size (default: 100)
        CHUNK_MAX_TOKENS: Maximum tokens per chunk (default: 512)
    """

    chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1000")))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200")))
    max_chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_MAX_SIZE", "2000")))
    min_chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_MIN_SIZE", "100")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("CHUNK_MAX_TOKENS", "512")))


@dataclass(frozen=True)
class SearchConfig:
    """RAG search configuration.

    Environment Variables:
        SEARCH_DEFAULT_LIMIT: Default number of results (default: 30)
        SEARCH_MAX_LIMIT: Maximum allowed results (default: 100)
        SEARCH_SIMILARITY_THRESHOLD: Minimum similarity score (default: 0.25)
        OUT_OF_SCOPE_THRESHOLD: If max similarity is below this, question is likely out of scope (default: 0.40)
        MAX_CHUNKS_PER_DOCUMENT: Maximum chunks to retrieve per document (default: 5)
        RRF_K: Reciprocal Rank Fusion k parameter (default: 50, lower = more weight to top results)
        EXCLUDE_TOC: Exclude Table of Contents chunks from search (default: true)
        TITLE_RERANK_ENABLED: Enable title-based re-ranking (default: true)
        TITLE_RERANK_BOOST: Max boost factor for title matches (default: 0.15)
        TITLE_RERANK_CLASSIFIERS: Comma-separated classifiers for keyword extraction (default: "type,classe,categorie,niveau,phase,etape,version")
        QUERY_EXPANSION_ENABLED: Enable LLM-based query expansion for vocabulary mismatch (default: true)

    Note: Reranking and query reformulation were removed after testing showed
    they hurt accuracy for French technical content. See docs/TROUBLESHOOT.md.
    Title-based re-ranking is different - it boosts documents whose titles match query keywords.
    Query expansion uses a fast LLM call to add domain-specific synonyms before search.
    """

    default_limit: int = field(default_factory=lambda: int(os.getenv("SEARCH_DEFAULT_LIMIT", "30")))
    max_limit: int = field(default_factory=lambda: int(os.getenv("SEARCH_MAX_LIMIT", "100")))
    # Lowered from 0.4 to 0.25 - catches more relevant chunks including definitions
    # See docs/TROUBLESHOOT.md for evidence
    similarity_threshold: float = field(
        default_factory=lambda: float(os.getenv("SEARCH_SIMILARITY_THRESHOLD", "0.25"))
    )
    # Threshold for detecting out-of-scope questions
    # If best result similarity is below this, the question is likely not covered by the KB
    out_of_scope_threshold: float = field(
        default_factory=lambda: float(os.getenv("OUT_OF_SCOPE_THRESHOLD", "0.40"))
    )
    max_chunks_per_document: int = field(
        default_factory=lambda: int(os.getenv("MAX_CHUNKS_PER_DOCUMENT", "5"))
    )
    rrf_k: int = field(default_factory=lambda: int(os.getenv("RRF_K", "50")))
    exclude_toc: bool = field(
        default_factory=lambda: os.getenv("EXCLUDE_TOC", "true").lower() == "true"
    )
    # Title-based re-ranking configuration
    title_rerank_enabled: bool = field(
        default_factory=lambda: os.getenv("TITLE_RERANK_ENABLED", "true").lower() == "true"
    )
    title_rerank_boost: float = field(
        default_factory=lambda: float(os.getenv("TITLE_RERANK_BOOST", "0.15"))
    )
    title_rerank_classifiers: List[str] = field(
        default_factory=lambda: os.getenv(
            "TITLE_RERANK_CLASSIFIERS", "type,classe,categorie,niveau,phase,etape,version"
        ).split(",")
    )
    # Query expansion - uses LLM to add synonyms for vocabulary mismatch
    query_expansion_enabled: bool = field(
        default_factory=lambda: os.getenv("QUERY_EXPANSION_ENABLED", "true").lower() == "true"
    )
    query_expansion_model: str = field(
        default_factory=lambda: os.getenv("QUERY_EXPANSION_MODEL", "gpt-4o-mini")
    )


@dataclass(frozen=True)
class APIConfig:
    """API server configuration.

    Environment Variables:
        API_HOST: Server host (default: "0.0.0.0")
        API_PORT: Server port (default: 8000)
        SLOW_REQUEST_THRESHOLD_MS: Slow request logging threshold (default: 500)
        CORS_ORIGINS: Comma-separated allowed origins
    """

    host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    slow_request_threshold_ms: float = field(
        default_factory=lambda: float(os.getenv("SLOW_REQUEST_THRESHOLD_MS", "500"))
    )
    cors_origins: List[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000",
        ).split(",")
    )


@dataclass(frozen=True)
class WeatherToolConfig:
    """Weather API tool configuration using Open-Meteo.

    Open-Meteo is a free weather API with no API key required.
    Includes geocoding support for city name → coordinates conversion.

    Environment Variables:
        WEATHER_BASE_URL: Open-Meteo forecast endpoint (default: "https://api.open-meteo.com/v1/forecast")
        WEATHER_GEOCODE_URL: Open-Meteo geocoding endpoint (default: "https://geocoding-api.open-meteo.com/v1/search")
        WEATHER_CACHE_TTL: Cache time-to-live in seconds (default: 900 = 15 minutes)
        WEATHER_TIMEOUT: API request timeout in seconds (default: 5)
        WEATHER_TEMPERATURE_UNIT: Temperature unit - "celsius" or "fahrenheit" (default: "celsius")
    """

    base_url: str = field(
        default_factory=lambda: os.getenv(
            "WEATHER_BASE_URL", "https://api.open-meteo.com/v1/forecast"
        )
    )
    geocode_url: str = field(
        default_factory=lambda: os.getenv(
            "WEATHER_GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search"
        )
    )
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("WEATHER_CACHE_TTL", "900"))
    )
    timeout_seconds: int = field(default_factory=lambda: int(os.getenv("WEATHER_TIMEOUT", "5")))
    temperature_unit: str = field(
        default_factory=lambda: os.getenv("WEATHER_TEMPERATURE_UNIT", "celsius")
    )


@dataclass(frozen=True)
class OsirisWorksiteConfig:
    """OSIRIS Brussels worksite API configuration.

    OSIRIS provides Brussels worksite data via GeoJSON API with Basic authentication.

    Environment Variables:
        OSIRIS_BASE_URL: OSIRIS API endpoint (default: "https://api.osiris.brussels/geoserver/ogc/features/v1/collections/api:WORKSITES/items")
        OSIRIS_USERNAME: Basic auth username (default: "cdco")
        OSIRIS_PASSWORD: Basic auth password (required - set in .env)
        OSIRIS_CACHE_TTL: Cache time-to-live in seconds (default: 900 = 15 minutes)
        OSIRIS_TIMEOUT: API request timeout in seconds (default: 10)
    """

    base_url: str = field(
        default_factory=lambda: os.getenv(
            "OSIRIS_BASE_URL",
            "https://api.osiris.brussels/geoserver/ogc/features/v1/collections/api:WORKSITES/items",
        )
    )
    username: str = field(default_factory=lambda: os.getenv("OSIRIS_USERNAME", "cdco"))
    password: Optional[str] = field(default_factory=lambda: _get_clean_env("OSIRIS_PASSWORD"))
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("OSIRIS_CACHE_TTL", "900"))
    )
    timeout_seconds: int = field(default_factory=lambda: int(os.getenv("OSIRIS_TIMEOUT", "10")))


@dataclass(frozen=True)
class Settings:
    """Main application settings aggregating all domain configs.

    Usage:
        from packages.config import settings

        # LLM configuration (supports Chutes.ai, Ollama, etc.)
        agent = Agent(settings.llm.create_model())

        # Other configs
        batch_size = settings.embedding.batch_size
        pool_size = settings.database.pool_max_size
        weather_config = settings.weather.base_url
        osiris_config = settings.osiris.username
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    api: APIConfig = field(default_factory=APIConfig)
    weather: WeatherToolConfig = field(default_factory=WeatherToolConfig)
    osiris: OsirisWorksiteConfig = field(default_factory=OsirisWorksiteConfig)

    # RAG agent tool configuration
    # Environment Variable: ENABLED_TOOLS - JSON array of tool names (e.g., '["weather"]')
    # None = all tools, [] = search only, ["weather"] = search + weather
    enabled_tools: Optional[List[str]] = field(
        default_factory=lambda: (
            None
            if not os.getenv("ENABLED_TOOLS")
            else __import__("json").loads(os.getenv("ENABLED_TOOLS"))
        )
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings singleton.

    Settings are loaded once and cached for the lifetime of the application.
    To reload settings, clear the cache: get_settings.cache_clear()
    """
    return Settings()


# Convenience export - import as: from packages.config import settings
settings = get_settings()

# Export all config classes for type hints
__all__ = [
    "Settings",
    "LLMConfig",
    "EmbeddingConfig",
    "DatabaseConfig",
    "ChunkingConfig",
    "SearchConfig",
    "APIConfig",
    "WeatherToolConfig",
    "OsirisWorksiteConfig",
    "get_settings",
    "settings",
    "PROJECT_ROOT",
]
