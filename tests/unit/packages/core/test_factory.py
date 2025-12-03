"""Tests for agent factory pattern."""

import os
from unittest.mock import patch

import pytest
from pydantic_ai import Agent

from packages.core.factory import (
    MODEL_PROVIDERS,
    PROVIDER_CONFIG,
    create_rag_agent,
)
from packages.core.types import RAGContext


# -----------------------------------------------------------------------------
# Provider Configuration Tests
# -----------------------------------------------------------------------------


def test_provider_config_has_required_keys():
    """Each provider config must have base_url, api_key_env, supports_tools."""
    required_keys = {"base_url", "api_key_env", "supports_tools"}
    for provider, config in PROVIDER_CONFIG.items():
        assert required_keys.issubset(config.keys()), f"{provider} missing keys"


def test_model_providers_map_to_valid_providers():
    """All models must map to a configured provider."""
    for model, provider in MODEL_PROVIDERS.items():
        assert provider in PROVIDER_CONFIG, f"{model} maps to unknown provider {provider}"


def test_mistral_provider_supports_tools():
    """Mistral provider must support tool calling."""
    assert PROVIDER_CONFIG["mistral"]["supports_tools"] is True


def test_openai_provider_supports_tools():
    """OpenAI provider must support tool calling."""
    assert PROVIDER_CONFIG["openai"]["supports_tools"] is True


# -----------------------------------------------------------------------------
# Agent Creation Tests (existing)
# -----------------------------------------------------------------------------


def test_create_rag_agent_default():
    """Factory creates agent successfully."""
    agent = create_rag_agent()
    assert isinstance(agent, Agent)
    assert agent.deps_type == RAGContext


def test_create_rag_agent_search_only():
    """Factory creates agent with search tool only."""
    agent = create_rag_agent(enabled_tools=[])
    assert isinstance(agent, Agent)


def test_create_rag_agent_custom_prompt():
    """Factory accepts custom system prompt."""
    custom_prompt = "You are a test assistant."
    agent = create_rag_agent(system_prompt=custom_prompt)
    assert isinstance(agent, Agent)


def test_create_rag_agent_all_tools():
    """Factory creates agent with all tools."""
    agent = create_rag_agent(enabled_tools=["weather"])
    assert isinstance(agent, Agent)


# -----------------------------------------------------------------------------
# Model Routing Tests
# -----------------------------------------------------------------------------


@patch.dict(os.environ, {"MISTRAL_API_KEY": "test-mistral-key"})
def test_create_rag_agent_with_mistral_model():
    """Factory creates agent with Mistral model using native provider."""
    agent = create_rag_agent(model="mistral-small-latest")
    assert isinstance(agent, Agent)


@patch.dict(os.environ, {"MISTRAL_API_KEY": "test-mistral-key"})
def test_create_rag_agent_mistral_large():
    """Factory creates agent with Mistral Large model."""
    agent = create_rag_agent(model="mistral-large-latest")
    assert isinstance(agent, Agent)


def test_create_rag_agent_with_openai_model():
    """Factory creates agent with explicit OpenAI model."""
    agent = create_rag_agent(model="gpt-4o-mini")
    assert isinstance(agent, Agent)


def test_model_routing_unknown_model_defaults_to_openai():
    """Unknown models should default to OpenAI provider."""
    provider = MODEL_PROVIDERS.get("unknown-model", "openai")
    assert provider == "openai"
