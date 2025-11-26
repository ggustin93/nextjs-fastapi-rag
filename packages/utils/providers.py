"""Provider configuration for OpenAI-compatible embedding APIs."""

import openai

from packages.config import settings


def get_embedding_client() -> openai.AsyncOpenAI:
    """Get OpenAI-compatible client for embeddings."""
    api_key = settings.embedding.api_key if hasattr(settings.embedding, 'api_key') else settings.llm.api_key
    base_url = settings.embedding.base_url if hasattr(settings.embedding, 'base_url') else None

    if not api_key and not base_url:
        raise ValueError("LLM_API_KEY or OPENAI_API_KEY environment variable is required")

    kwargs = {"api_key": api_key or "not-needed"}
    if base_url:
        kwargs["base_url"] = base_url

    return openai.AsyncOpenAI(**kwargs)


def get_embedding_model() -> str:
    """Get embedding model name from settings."""
    return settings.embedding.model
