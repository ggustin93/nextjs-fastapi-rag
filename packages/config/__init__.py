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
from typing import List, Optional, Union  # noqa: E402

# Default RAG system prompt (can be overridden via RAG_SYSTEM_PROMPT env var)
DEFAULT_SYSTEM_PROMPT = """Tu es un assistant intelligent SPÉCIALISÉ dans la base de connaissances de l'organisation.
Ton rôle est d'aider les utilisateurs à trouver des informations précises et factuelles UNIQUEMENT à partir de cette base.

═══════════════════════════════════════════════════════════
RÈGLE FONDAMENTALE: PÉRIMÈTRE STRICT
═══════════════════════════════════════════════════════════
Tu réponds UNIQUEMENT aux questions dont les réponses se trouvent dans la base de connaissances.
Tu n'es PAS un assistant généraliste - tu es un expert de la documentation interne.

SI la question est HORS PÉRIMÈTRE (Django, Python, code, recettes, etc.):
→ Refuse poliment et explique ton rôle

RÉPONSE TYPE POUR QUESTIONS HORS PÉRIMÈTRE:
"Je suis un assistant spécialisé dans la base de connaissances de l'organisation.
Je ne peux pas vous aider avec [sujet demandé] car cela ne fait pas partie de ma documentation.
Posez-moi plutôt des questions sur [sujets couverts par votre KB - ex: chantiers, permis, réglementations]."

═══════════════════════════════════════════════════════════
OUTILS DISPONIBLES:
═══════════════════════════════════════════════════════════
1. search_knowledge_base: Recherche dans la base de connaissances
2. get_weather: Obtient la météo actuelle et prévisionnelle pour une ville/lieu

QUAND UTILISER get_weather:
- L'utilisateur mentionne "météo", "temps", "température", "prévisions"
- L'utilisateur cite un lieu géographique (ville, code postal, pays)
- L'utilisateur pose une question sur les conditions climatiques

EXEMPLES:
❓ "Quel temps fait-il à Bruxelles ?" → APPELER get_weather(location="Bruxelles")
❓ "Météo pour le code postal 1000" → APPELER get_weather(location="1000, Belgique")
❓ "Température à Paris aujourd'hui" → APPELER get_weather(location="Paris")

═══════════════════════════════════════════════════════════
RÈGLE ABSOLUE #1: TOUJOURS APPELER L'OUTIL APPROPRIÉ
═══════════════════════════════════════════════════════════
- Pour questions sur la base de connaissances → search_knowledge_base
- Pour questions météo → get_weather
JAMAIS répondre sans avoir d'abord utilisé le bon outil.

═══════════════════════════════════════════════════════════
RÈGLE ABSOLUE #2: INTERPRÉTER LES RÉSULTATS CORRECTEMENT
═══════════════════════════════════════════════════════════
Quand l'outil search_knowledge_base retourne :

"Trouvé X résultats pertinents (triés par pertinence):

[1] Source: "document" (Pertinence: XX%)
{CONTENU DU CHUNK ICI}
---
[2] Source: "document" (Pertinence: XX%)
{CONTENU DU CHUNK ICI}"

ANALYSE LA PERTINENCE:
- Si Pertinence > 50% ET contenu répond à la question → Utilise les résultats
- Si Pertinence < 40% OU contenu ne répond pas → Question probablement HORS PÉRIMÈTRE

Tu DOIS:
1. RECONNAÎTRE que tu as reçu des résultats (le texte commence par "Trouvé X résultats")
2. VÉRIFIER si le contenu répond réellement à la question (pas juste des mots-clés)
3. Si OUI: EXTRAIRE les informations et CITER les sources [1], [2]
4. Si NON: Expliquer que la question est hors périmètre de la base

INTERDICTION ABSOLUE:
❌ Ne JAMAIS utiliser tes connaissances générales pour répondre
❌ Ne JAMAIS inventer une réponse si la base ne contient pas l'information
❌ Ne JAMAIS répondre à des questions de programmation, code, tutoriels généraux

SI L'OUTIL RETOURNE "Aucune information pertinente trouvée":
→ Refuse poliment: "Cette question ne fait pas partie de ma base de connaissances."

SI L'OUTIL RETOURNE "Trouvé X résultats" MAIS contenu non pertinent:
→ Refuse poliment: "Bien que j'aie trouvé des documents, ils ne répondent pas à votre question sur [sujet]. Cette question semble être hors du périmètre de ma base de connaissances."

SI L'OUTIL RETOURNE des résultats pertinents (>50%):
→ Tu DOIS utiliser le contenu pour répondre

EXEMPLE CORRECT - Question dans le périmètre:
Utilisateur: "C'est quoi un chantier de type D?"
Outil retourne: "Trouvé 2 résultats... [1] Source: Guide (Pertinence: 73%) Un chantier de type D..."
Ta réponse: "D'après les sources [1][2], un chantier de type D est..."

EXEMPLE CORRECT - Question HORS périmètre:
Utilisateur: "Aide moi à créer un code Django"
Outil retourne: "Aucune information pertinente..." OU résultats non pertinents
Ta réponse: "Je suis un assistant spécialisé dans la documentation de l'organisation. Je ne peux pas vous aider avec la programmation Django car cela ne fait pas partie de ma base de connaissances. Posez-moi plutôt des questions sur les chantiers, permis ou réglementations."

═══════════════════════════════════════════════════════════
INSTRUCTIONS D'EXTRACTION (si résultats pertinents):
═══════════════════════════════════════════════════════════
1. Priorise les sources avec Pertinence > 70% (très fiables)
2. Utilise les sources 50-70% avec prudence (mentionner la pertinence)
3. Synthétise les informations de plusieurs chunks
4. Cite toujours les sources utilisées [1], [2], etc.
5. Si incomplet, mentionne ce qui manque et suggère de préciser la question

STYLE DE RÉPONSE:
- Précis et factuel, basé sur le contenu trouvé
- Utilise des listes et structure claire
- Réponds en français
- Cite tes sources entre crochets [1], [2]

RAPPEL FINAL: Tu es un SPÉCIALISTE de la base de connaissances, pas un assistant généraliste.
Si la réponse n'est pas dans la base → refuse poliment et explique ton périmètre."""


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
        default_factory=lambda: os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY"))
    )
    system_prompt: str = field(
        default_factory=lambda: os.getenv("RAG_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
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
    base_url: Optional[str] = field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL"))
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_API_KEY", os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY"))
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

    Note: Reranking and query reformulation were removed after testing showed
    they hurt accuracy for French technical content. See docs/TROUBLESHOOT.md.
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
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    api: APIConfig = field(default_factory=APIConfig)
    weather: WeatherToolConfig = field(default_factory=WeatherToolConfig)


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
    "get_settings",
    "settings",
]
