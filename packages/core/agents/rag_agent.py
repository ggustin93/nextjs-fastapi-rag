"""RAG Agent - Knowledge base + Osiris API access."""

from packages.config import settings
from packages.core.agents import AgentConfig, register_agent

RAG_AGENT = AgentConfig(
    id="rag",
    name="Assistant RAG",
    icon="📚",
    system_prompt=settings.llm.system_prompt,
    enabled_tools=["search_knowledge_base", "osiris_worksite"],
    temperature=0.7,
    description="Assistant avec accès à la base de connaissances et l'API Osiris",
    aliases=["assistant", "default", "kb"],
)

register_agent(RAG_AGENT)
