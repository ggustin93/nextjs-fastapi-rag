"""Agent configuration and registry.

Provides a simple way to define and manage multiple agents with different
prompts and tool access.
"""

from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    id: str
    name: str
    icon: str
    system_prompt: str
    enabled_tools: list[str] | None = None  # None = all tools
    temperature: float = 0.7
    description: str = ""
    aliases: list[str] = field(default_factory=list)


# Global agent registry
AGENTS: dict[str, AgentConfig] = {}


def register_agent(config: AgentConfig) -> None:
    """Register an agent configuration."""
    AGENTS[config.id] = config
    # Also register aliases
    for alias in config.aliases:
        AGENTS[alias] = config


def get_agent_config(agent_id: str) -> AgentConfig | None:
    """Get an agent configuration by ID or alias."""
    return AGENTS.get(agent_id)


def list_agents() -> list[dict]:
    """List all registered agents (excluding aliases)."""
    seen_ids = set()
    agents = []
    for config in AGENTS.values():
        if config.id not in seen_ids:
            seen_ids.add(config.id)
            agents.append(
                {
                    "id": config.id,
                    "name": config.name,
                    "icon": config.icon,
                    "description": config.description,
                }
            )
    return agents


def _register_builtin_agents() -> None:
    """Register built-in agents. Called lazily to avoid circular imports."""
    if AGENTS:  # Already registered
        return
    # Import triggers registration via register_agent() calls
    from packages.core.agents import (
        rag_agent,  # noqa: F401
        weather_agent,  # noqa: F401
    )


def ensure_agents_registered() -> None:
    """Ensure all built-in agents are registered."""
    _register_builtin_agents()
