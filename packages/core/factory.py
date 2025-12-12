"""Agent factory for consistent RAG agent creation."""

import os

from pydantic_ai import Agent

from packages.config import settings
from packages.core.tools import get_tools
from packages.core.types import RAGContext

# Provider configuration for model routing
PROVIDER_CONFIG = {
    "openai": {
        "base_url": None,  # Use default OpenAI API
        "api_key_env": "OPENAI_API_KEY",
        "supports_tools": True,
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "supports_tools": True,  # Mistral AI supports function calling
    },
    # "chutes": {
    #     "base_url": "https://llm.chutes.ai/v1",
    #     "api_key_env": "CHUTES_API_KEY",
    #     "supports_tools": False,  # Chutes API doesn't support OpenAI-style function calling
    # },
}

# Model to provider mapping
MODEL_PROVIDERS = {
    "gpt-4o-mini": "openai",
    "gpt-4o": "openai",
    "mistral-small-latest": "mistral",
    "mistral-large-latest": "mistral",
    # "Qwen/Qwen2.5-Coder-32B-Instruct": "chutes",
    # "deepseek-ai/DeepSeek-V3-0324": "chutes",
}


def create_rag_agent(
    system_prompt: str | None = None,
    enabled_tools: list[str] | None = None,
    deps_type=RAGContext,
    model: str | None = None,
) -> Agent:
    """Create RAG agent with consistent configuration.

    Args:
        system_prompt: Override default system prompt
        enabled_tools: List of tool names to enable.
                      None = all tools, [] = search only
        deps_type: Dependency type (RAGContext or None)
        model: Override LLM model (routes to correct provider automatically)

    Returns:
        Configured Agent instance
    """
    prompt = system_prompt or settings.llm.system_prompt

    # Create model instance
    if model:
        # Route to correct provider based on model
        provider_name = MODEL_PROVIDERS.get(model, "openai")
        provider_config = PROVIDER_CONFIG.get(provider_name, PROVIDER_CONFIG["openai"])

        base_url = provider_config["base_url"]
        api_key = os.getenv(provider_config["api_key_env"], "")
        supports_tools = provider_config.get("supports_tools", True)

        # Only enable tools if provider supports them
        if supports_tools:
            tools = get_tools(
                enabled_tools if enabled_tools is not None else settings.enabled_tools
            )
        else:
            tools = []  # No tools for providers that don't support function calling

        if provider_name == "mistral":
            # Native Mistral support with proper tool calling
            from pydantic_ai.models.mistral import MistralModel
            from pydantic_ai.providers.mistral import MistralProvider

            mistral_provider = MistralProvider(api_key=api_key)
            model_instance = MistralModel(model, provider=mistral_provider)
        elif base_url:
            # Custom provider (OpenAI-compatible APIs)
            from pydantic_ai.models.openai import OpenAIModel
            from pydantic_ai.providers.openai import OpenAIProvider

            provider = OpenAIProvider(base_url=base_url, api_key=api_key)
            model_instance = OpenAIModel(model, provider=provider)
        else:
            # Default OpenAI
            model_instance = model
    else:
        # Use default model from settings
        model_instance = settings.llm.create_model()
        tools = get_tools(enabled_tools if enabled_tools is not None else settings.enabled_tools)

    return Agent(
        model_instance,
        deps_type=deps_type,
        system_prompt=prompt,
        tools=tools,
    )
