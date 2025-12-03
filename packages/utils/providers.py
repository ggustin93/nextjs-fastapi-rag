"""Provider configuration for OpenAI-compatible embedding APIs."""

import openai

from packages.config import settings


def get_embedding_client() -> openai.AsyncOpenAI:
    """Get OpenAI-compatible client for embeddings.

    Validates API key format and provides clear error messages for common issues.

    Raises:
        ValueError: If API key is missing, invalid, or malformed
    """
    api_key = (
        settings.embedding.api_key
        if hasattr(settings.embedding, "api_key")
        else settings.llm.api_key
    )
    base_url = settings.embedding.base_url if hasattr(settings.embedding, "base_url") else None

    # Validate API key is present (unless using custom base_url without auth)
    if not api_key and not base_url:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required. "
            "Please set it in your .env file with a valid OpenAI API key "
            "from https://platform.openai.com/api-keys"
        )

    # Validate API key format if provided
    if api_key:
        # Strip and check for common issues
        api_key_stripped = api_key.strip()

        # Detect malformed keys (comments, placeholders, etc.)
        if (
            not api_key_stripped
            or api_key_stripped.startswith("#")
            or "your-api-key" in api_key_stripped.lower()
            or "sk-your" in api_key_stripped.lower()
            or "sk-or-your" in api_key_stripped.lower()
        ):
            raise ValueError(
                "Invalid OPENAI_API_KEY detected. "
                "Please set a valid OpenAI API key in your .env file. "
                "Keys should start with 'sk-' followed by your actual key. "
                "Check for inline comments in your .env file - they should be on separate lines."
            )

        api_key = api_key_stripped

    kwargs = {"api_key": api_key or "not-needed"}
    if base_url:
        kwargs["base_url"] = base_url

    return openai.AsyncOpenAI(**kwargs)


def get_embedding_model() -> str:
    """Get embedding model name from settings."""
    return settings.embedding.model
