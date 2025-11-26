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

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional, Union


@dataclass(frozen=True)
class LLMConfig:
    """LLM model configuration with multi-provider support.

    Supports OpenAI, Chutes.ai, Ollama, and any OpenAI-compatible API.

    Environment Variables:
        LLM_PROVIDER: Provider name for model identifier (default: "openai")
        LLM_MODEL: Model name (default: "gpt-4o-mini")
        LLM_BASE_URL: Custom API base URL for OpenAI-compatible APIs
        LLM_API_KEY: API key (falls back to OPENAI_API_KEY)

    Example - Chutes.ai:
        LLM_BASE_URL=https://myuser-my-chute.chutes.ai/v1
        LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
        LLM_API_KEY=your-chutes-api-key
    """

    provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "openai")
    )
    model: str = field(
        default_factory=lambda: os.getenv(
            "LLM_MODEL", os.getenv("LLM_CHOICE", "gpt-4o-mini")
        )
    )
    base_url: Optional[str] = field(
        default_factory=lambda: os.getenv("LLM_BASE_URL")
    )
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv(
            "LLM_API_KEY", os.getenv("OPENAI_API_KEY")
        )
    )

    @property
    def model_identifier(self) -> str:
        """Get model identifier in provider:model format.

        Used for simple Agent() instantiation when not using custom provider.
        """
        return f"{self.provider}:{self.model}"

    def create_model(self) -> Union[str, "OpenAIChatModel"]:  # noqa: F821
        """Create PydanticAI model with proper provider configuration.

        Returns OpenAIChatModel with custom provider if LLM_BASE_URL is set,
        otherwise returns model_identifier string for default OpenAI behavior.

        This method enables seamless support for:
        - Chutes.ai (Bittensor decentralized AI)
        - Ollama (local models)
        - Any OpenAI-compatible API

        Returns:
            Either a model identifier string or OpenAIChatModel instance.
        """
        # If custom base_url is set, use OpenAIProvider with that URL
        if self.base_url:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            provider = OpenAIProvider(
                base_url=self.base_url,
                api_key=self.api_key or "api-key-not-set",
            )
            return OpenAIChatModel(self.model, provider=provider)

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
    base_url: Optional[str] = field(
        default_factory=lambda: os.getenv("EMBEDDING_BASE_URL")
    )
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_API_KEY", os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY"))
        )
    )
    batch_size: int = field(
        default_factory=lambda: int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))
    )
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

    pool_min_size: int = field(
        default_factory=lambda: int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    )
    pool_max_size: int = field(
        default_factory=lambda: int(os.getenv("DB_POOL_MAX_SIZE", "5"))
    )
    command_timeout: int = field(
        default_factory=lambda: int(os.getenv("DB_COMMAND_TIMEOUT", "60"))
    )
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

    chunk_size: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1000"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200"))
    )
    max_chunk_size: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_MAX_SIZE", "2000"))
    )
    min_chunk_size: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_MIN_SIZE", "100"))
    )
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_MAX_TOKENS", "512"))
    )


@dataclass(frozen=True)
class SearchConfig:
    """RAG search configuration.

    Environment Variables:
        SEARCH_DEFAULT_LIMIT: Default number of results (default: 10)
        SEARCH_MAX_LIMIT: Maximum allowed results (default: 50)
        SEARCH_SIMILARITY_THRESHOLD: Minimum similarity score (default: 0.3)
    """

    default_limit: int = field(
        default_factory=lambda: int(os.getenv("SEARCH_DEFAULT_LIMIT", "10"))
    )
    max_limit: int = field(
        default_factory=lambda: int(os.getenv("SEARCH_MAX_LIMIT", "50"))
    )
    similarity_threshold: float = field(
        default_factory=lambda: float(os.getenv("SEARCH_SIMILARITY_THRESHOLD", "0.3"))
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
class Settings:
    """Main application settings aggregating all domain configs.

    Usage:
        from packages.config import settings

        # LLM configuration (supports Chutes.ai, Ollama, etc.)
        agent = Agent(settings.llm.create_model())

        # Other configs
        batch_size = settings.embedding.batch_size
        pool_size = settings.database.pool_max_size
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    api: APIConfig = field(default_factory=APIConfig)


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
    "get_settings",
    "settings",
]
