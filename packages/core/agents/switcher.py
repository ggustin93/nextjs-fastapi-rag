"""Agent switcher for managing multiple agents at runtime."""

import re
from typing import TYPE_CHECKING

from pydantic_ai import Agent

from packages.core.agents import AGENTS, ensure_agents_registered, get_agent_config
from packages.core.factory import create_rag_agent

if TYPE_CHECKING:
    from packages.core.agents import AgentConfig


class AgentSwitcher:
    """Manages switching between different agents at runtime.

    Agents are created lazily on first use and cached for reuse.

    Usage:
        switcher = AgentSwitcher()
        switcher.switch_to("weather")
        agent = switcher.get_current()
        response = await agent.run("Météo à Bruxelles?", deps=context)

    Chat input with @mention:
        agent_id, message = switcher.parse_agent_mention("@weather Météo?")
        if agent_id:
            switcher.switch_to(agent_id)
    """

    def __init__(self, default_agent_id: str = "rag"):
        """Initialize the switcher.

        Args:
            default_agent_id: The default agent to use if none specified.
        """
        ensure_agents_registered()
        self.current_agent_id: str = default_agent_id
        self._cached_agents: dict[str, Agent] = {}

    def switch_to(self, agent_id: str) -> Agent:
        """Switch to a different agent.

        Creates the agent if not already cached.

        Args:
            agent_id: The ID of the agent to switch to.

        Returns:
            The PydanticAI Agent instance.

        Raises:
            ValueError: If the agent ID is not registered.
        """
        config = get_agent_config(agent_id)
        if config is None:
            available = list(AGENTS.keys())
            raise ValueError(f"Unknown agent: {agent_id}. Available: {available}")

        # Use the canonical ID (in case an alias was used)
        canonical_id = config.id

        # Create agent if not cached
        if canonical_id not in self._cached_agents:
            self._cached_agents[canonical_id] = create_rag_agent(
                system_prompt=config.system_prompt,
                enabled_tools=config.enabled_tools,
            )

        self.current_agent_id = canonical_id
        return self._cached_agents[canonical_id]

    def get_current(self) -> Agent:
        """Get the currently active agent.

        Creates the agent if not already cached.

        Returns:
            The current PydanticAI Agent instance.
        """
        if self.current_agent_id not in self._cached_agents:
            self.switch_to(self.current_agent_id)
        return self._cached_agents[self.current_agent_id]

    def get_current_config(self) -> "AgentConfig | None":
        """Get the configuration of the current agent."""
        return get_agent_config(self.current_agent_id)

    def parse_agent_mention(self, message: str) -> tuple[str | None, str]:
        """Parse @agent mention from the beginning of a message.

        Uses strict validation to prevent injection attacks:
        - ASCII alphanumeric and underscore only (no path chars)
        - Max 50 characters for agent ID
        - Must match a registered agent

        Args:
            message: The user message to parse.

        Returns:
            Tuple of (agent_id or None, cleaned message).

        Examples:
            >>> switcher.parse_agent_mention("@weather Météo Paris?")
            ("weather", "Météo Paris?")

            >>> switcher.parse_agent_mention("Hello world")
            (None, "Hello world")
        """
        # Strict pattern: ASCII alphanumeric + underscore only, max 50 chars
        match = re.match(r"^@([a-zA-Z0-9_]{1,50})\s+(.*)", message, re.DOTALL)
        if match:
            agent_id = match.group(1).lower()
            clean_message = match.group(2).strip()
            # Verify agent exists (also handles aliases)
            config = get_agent_config(agent_id)
            if config is not None:
                return config.id, clean_message  # Return canonical ID
        return None, message

    def process_message(self, message: str) -> tuple[Agent, str]:
        """Process a message, switching agents if @mention detected.

        This is a convenience method that combines parse_agent_mention
        and switch_to.

        Args:
            message: The user message to process.

        Returns:
            Tuple of (agent to use, cleaned message).
        """
        agent_id, clean_message = self.parse_agent_mention(message)
        if agent_id:
            self.switch_to(agent_id)
        return self.get_current(), clean_message
