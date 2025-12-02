"""Tests for agent factory pattern."""

from pydantic_ai import Agent

from packages.core.factory import create_rag_agent
from packages.core.types import RAGContext


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
