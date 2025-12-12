"""Tests for RAG agent functionality."""

import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

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
        """get_last_sources should return sources and clear them from context."""
        agent_mod = get_agent_module()

        # Create mock context with sources
        mock_context = MagicMock()
        mock_context.last_search_sources = [
            {"title": "Doc1", "path": "path1", "similarity": 0.9},
            {"title": "Doc2", "path": "path2", "similarity": 0.8},
        ]

        sources = agent_mod.get_last_sources(mock_context)

        assert len(sources) == 2
        assert sources[0]["title"] == "Doc1"
        # Should be cleared after retrieval
        assert mock_context.last_search_sources == []

    def test_get_last_sources_empty(self):
        """get_last_sources with no sources returns empty list."""
        agent_mod = get_agent_module()

        mock_context = MagicMock()
        mock_context.last_search_sources = []

        sources = agent_mod.get_last_sources(mock_context)

        assert sources == []


class TestRAGContextCreation:
    """Test RAG context creation."""

    @pytest.mark.asyncio
    async def test_create_rag_context_initializes_dependencies(self):
        """create_rag_context should initialize db_client and embedder."""
        agent_mod = get_agent_module()

        with (
            patch("packages.core.agent.SupabaseRestClient") as mock_db_class,
            patch("packages.ingestion.embedder.create_embedder") as mock_embedder_factory,
        ):
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            mock_embedder = MagicMock()
            mock_embedder_factory.return_value = mock_embedder

            context = await agent_mod.create_rag_context()

            mock_db_class.assert_called_once()
            mock_db.initialize.assert_awaited_once()
            mock_embedder_factory.assert_called_once()
            assert context.db_client == mock_db
            assert context.embedder == mock_embedder
            assert context.last_search_sources == []


class TestSystemPrompt:
    """Test system prompt configuration."""

    def _get_system_prompt(self, agent):
        """Helper to get system prompt string from PydanticAI agent."""
        # PydanticAI stores system prompts in _system_prompts tuple
        prompts = agent._system_prompts
        return " ".join(prompts) if prompts else ""

    def _create_test_agent(self):
        """Create agent for testing using the factory."""
        from packages.core.factory import create_rag_agent

        return create_rag_agent()

    def test_agent_has_system_prompt(self):
        """Agent should have a system prompt configured."""
        agent = self._create_test_agent()

        assert agent is not None
        prompt = self._get_system_prompt(agent)
        assert len(prompt) > 100

    def test_system_prompt_instructs_knowledge_base_search(self):
        """System prompt should instruct agent to search knowledge base."""
        agent = self._create_test_agent()

        prompt_lower = self._get_system_prompt(agent).lower()
        # Should instruct to search knowledge base (French OR English)
        has_kb_reference = any(
            term in prompt_lower
            for term in [
                "base de connaissances",
                "base de données",
                "knowledge base",
                "search_knowledge_base",
            ]
        )
        assert has_kb_reference, "Prompt should reference knowledge base"

    def test_system_prompt_handles_missing_info(self):
        """System prompt should handle missing information gracefully."""
        agent = self._create_test_agent()

        prompt_lower = self._get_system_prompt(agent).lower()
        # Should handle case when info isn't found (French OR English)
        has_missing_info_handling = any(
            term in prompt_lower
            for term in [
                "aucune information",
                "pas trouvé",
                "no relevant",
                "not found",
                "politely refuse",
            ]
        )
        assert has_missing_info_handling, "Prompt should handle missing info"
        assert "cite" in prompt_lower or "sources" in prompt_lower
