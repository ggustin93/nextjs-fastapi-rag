"""Tests for RAG agent functionality."""

import importlib
import sys
from unittest.mock import AsyncMock, patch

import pytest


def get_agent_module():
    """Get a fresh reference to the agent module."""
    # Force reimport if needed
    if "packages.core.agent" in sys.modules:
        return importlib.import_module("packages.core.agent")
    return __import__("packages.core.agent", fromlist=[""])


class TestAgentHelpers:
    """Test agent helper functions."""

    def test_get_last_sources_returns_and_clears(self):
        """get_last_sources should return sources and clear them."""
        agent_mod = get_agent_module()

        # Set some test sources
        agent_mod.last_search_sources = [
            {"title": "Doc1", "path": "path1", "similarity": 0.9},
            {"title": "Doc2", "path": "path2", "similarity": 0.8},
        ]

        sources = agent_mod.get_last_sources()

        assert len(sources) == 2
        assert sources[0]["title"] == "Doc1"
        # Should be cleared after retrieval
        assert agent_mod.last_search_sources == []

    def test_get_last_sources_empty(self):
        """get_last_sources with no sources returns empty list."""
        agent_mod = get_agent_module()

        agent_mod.last_search_sources = []
        sources = agent_mod.get_last_sources()

        assert sources == []


class TestDatabaseInitialization:
    """Test database connection management."""

    @pytest.mark.asyncio
    async def test_initialize_db_creates_client(self):
        """initialize_db should create REST client."""
        agent_mod = get_agent_module()

        agent_mod.rest_client = None

        with patch("packages.core.agent.SupabaseRestClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance

            await agent_mod.initialize_db()

            mock_client.assert_called_once()
            mock_instance.initialize.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_db_closes_client(self):
        """close_db should close REST client."""
        agent_mod = get_agent_module()

        mock_client = AsyncMock()
        agent_mod.rest_client = mock_client

        await agent_mod.close_db()

        mock_client.close.assert_awaited_once()


class TestSystemPrompt:
    """Test system prompt configuration."""

    def _get_system_prompt(self, agent_mod):
        """Helper to get system prompt string from PydanticAI agent."""
        # PydanticAI stores system prompts in _system_prompts tuple
        prompts = agent_mod.agent._system_prompts
        return " ".join(prompts) if prompts else ""

    def test_agent_has_system_prompt(self):
        """Agent should have a system prompt configured."""
        agent_mod = get_agent_module()

        assert agent_mod.agent is not None
        prompt = self._get_system_prompt(agent_mod)
        assert len(prompt) > 100

    def test_system_prompt_instructs_knowledge_base_search(self):
        """System prompt should instruct agent to search knowledge base."""
        agent_mod = get_agent_module()

        prompt_lower = self._get_system_prompt(agent_mod).lower()
        # Should instruct to search knowledge base before answering (French)
        assert "base de connaissances" in prompt_lower or "base de données" in prompt_lower
        # Check for search instruction - prompt uses "cherché" (past participle)
        assert "cherché" in prompt_lower or "appeler search" in prompt_lower

    def test_system_prompt_handles_missing_info(self):
        """System prompt should handle missing information gracefully."""
        agent_mod = get_agent_module()

        prompt_lower = self._get_system_prompt(agent_mod).lower()
        # Should handle case when info isn't found (French)
        # Prompt discusses "aucune information pertinente" scenario
        assert "aucune information" in prompt_lower or "pas trouvé" in prompt_lower
        assert "cite" in prompt_lower or "sources" in prompt_lower
