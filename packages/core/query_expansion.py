"""Query expansion module for RAG retrieval improvement.

This module provides a configurable query expansion system that uses LLM
to add domain-specific synonyms and technical terms to improve retrieval.

Architecture (SOLID):
- Single Responsibility: Only handles query expansion
- Open/Closed: Extensible via config files, not code changes
- Liskov Substitution: Any QueryExpander implementation can be swapped
- Interface Segregation: Minimal interface (expand method)
- Dependency Inversion: Depends on abstractions (settings), not concretions

Usage:
    from packages.core.query_expansion import get_query_expander

    expander = get_query_expander()
    expanded = await expander.expand("c'est quoi un type A?")
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

from packages.config import settings

logger = logging.getLogger(__name__)


class QueryExpander(ABC):
    """Abstract base class for query expansion strategies."""

    @abstractmethod
    async def expand(self, query: str) -> str:
        """Expand a query with additional terms for better retrieval.

        Args:
            query: Original user query

        Returns:
            Expanded query (original + additional terms)
        """
        pass


class NoOpQueryExpander(QueryExpander):
    """Pass-through expander that returns the original query."""

    async def expand(self, query: str) -> str:
        return query


class LLMQueryExpander(QueryExpander):
    """LLM-based query expander using configurable prompts.

    Loads domain-specific prompt from a file, allowing easy customization
    per organization without code changes.

    Prompt file location (in order of priority):
    1. QUERY_EXPANSION_PROMPT_FILE env var
    2. data/prompts/query_expansion.txt
    3. Built-in default prompt
    """

    # Default prompt template (used if no file found)
    DEFAULT_PROMPT = """You are a query reformulation assistant for document retrieval.

Reformulate the following question by adding relevant synonyms and technical terms.
Keep the reformulation concise (max 40 words) on a single line.
Do not add question marks or formatting.

Question: {query}

Enriched reformulation:"""

    def __init__(
        self,
        prompt_file: Optional[str] = None,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        max_tokens: int = 100,
        temperature: float = 0.3,
    ):
        """Initialize the LLM query expander.

        Args:
            prompt_file: Path to custom prompt file (optional)
            model: LLM model to use for expansion
            api_key: OpenAI API key (uses env var if not provided)
            max_tokens: Max tokens for LLM response
            temperature: LLM temperature (lower = more consistent)
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._prompt_template: Optional[str] = None
        self._prompt_file = prompt_file

    def _load_prompt(self) -> str:
        """Load prompt template from file or use default.

        Search order:
        1. Explicit prompt_file parameter
        2. QUERY_EXPANSION_PROMPT_FILE env var
        3. data/prompts/query_expansion.txt (relative to project root)
        4. Default built-in prompt
        """
        if self._prompt_template:
            return self._prompt_template

        # Try explicit file first
        prompt_paths = []

        if self._prompt_file:
            prompt_paths.append(Path(self._prompt_file))

        # Try env var
        env_path = os.getenv("QUERY_EXPANSION_PROMPT_FILE")
        if env_path:
            prompt_paths.append(Path(env_path))

        # Try default location
        prompt_paths.append(Path("data/prompts/query_expansion.txt"))

        for path in prompt_paths:
            if path.exists():
                try:
                    self._prompt_template = path.read_text(encoding="utf-8")
                    logger.info(f"Loaded query expansion prompt from: {path}")
                    return self._prompt_template
                except Exception as e:
                    logger.warning(f"Failed to load prompt from {path}: {e}")

        # Use default
        logger.info("Using default query expansion prompt (no custom file found)")
        self._prompt_template = self.DEFAULT_PROMPT
        return self._prompt_template

    async def expand(self, query: str) -> str:
        """Expand query using LLM with domain-specific prompt.

        Args:
            query: Original user query

        Returns:
            Combined original + expanded query for better retrieval
        """
        if not self.api_key:
            logger.warning("No OpenAI API key for query expansion, using original query")
            return query

        try:
            client = AsyncOpenAI(api_key=self.api_key)
            prompt = self._load_prompt().format(query=query)

            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            expanded = response.choices[0].message.content.strip()

            # Combine original + expanded for best coverage
            combined = f"{query} {expanded}"
            logger.info(f"Query expansion: '{query[:50]}...' → +{len(expanded)} chars")

            return combined

        except Exception as e:
            logger.warning(f"Query expansion failed, using original: {e}")
            return query


def get_query_expander() -> QueryExpander:
    """Factory function to get the configured query expander.

    Returns:
        QueryExpander instance based on settings
    """
    if not settings.search.query_expansion_enabled:
        return NoOpQueryExpander()

    return LLMQueryExpander(
        model=settings.search.query_expansion_model,
    )


# Module-level convenience function
async def expand_query(query: str) -> str:
    """Expand a query using the configured expander.

    Convenience function for simple usage without managing expander instances.

    Args:
        query: Original user query

    Returns:
        Expanded query
    """
    expander = get_query_expander()
    return await expander.expand(query)
