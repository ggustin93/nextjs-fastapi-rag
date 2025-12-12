# nextjs-fastapi-rag

RAG starter for document-based Q&A with multi-agent support. Clean architecture, hybrid search, streaming responses.

## Features

- **Streaming Chat** — SSE real-time responses with source citations
- **Hybrid Search** — Vector + full-text + RRF fusion
- **Multi-Agent** — Switchable agents with `@mention` syntax
- **Multi-Format** — PDF (Docling), Web (Crawl4AI), Markdown
- **Multi-Provider** — OpenAI, Ollama, or any OpenAI-compatible API

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 15, TypeScript, Tailwind, shadcn/ui |
| Backend | FastAPI, PydanticAI |
| Database | PostgreSQL + pgvector |
| AI | OpenAI, Docling, Crawl4AI |

## Quick Start

```bash
# Install
make install

# Configure
cp .env.example .env  # Edit DATABASE_URL, OPENAI_API_KEY

# Setup database
psql $DATABASE_URL < sql/schema.sql

# Ingest documents
make ingest

# Run
make run  # Frontend :3000, Backend :8000
```

## Project Structure

```
├── packages/               # Shared Python packages
│   ├── core/
│   │   ├── agents/         # Multi-agent system (RAG, Weather, custom)
│   │   ├── tools/          # PydanticAI tools (search, external APIs)
│   │   └── factory.py      # Agent factory
│   ├── ingestion/          # Docling chunker, embedder
│   ├── scraper/            # Crawl4AI web scraper
│   └── config/             # Centralized settings
├── services/
│   ├── api/                # FastAPI backend
│   └── web/                # Next.js frontend
├── config/                 # Runtime config
│   ├── prompts/            # System prompts (*.txt)
│   └── stopwords.json      # Search stopwords
├── data/
│   ├── raw/                # Source documents (PDFs, notes)
│   └── processed/          # Generated content (scraped)
└── tests/
```

## Architecture

```
User → Next.js → FastAPI → PydanticAI Agent
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
              search_kb            external_apis
                    │                   │
                pgvector            Weather, OSIRIS...
```

**Retrieval Pipeline**: Query → Expansion → Hybrid Search → RRF Fusion → Title Rerank → LLM → Stream

## Multi-Agent System

Agents are switchable at runtime via `@mention` or API:

```python
# packages/core/agents/
├── __init__.py       # Registry, AgentConfig
├── switcher.py       # Runtime switching, @mention parsing
├── rag_agent.py      # Knowledge base + external tools
└── weather_agent.py  # Specialized weather assistant
```

**Usage**:
- Chat: `@weather Météo à Bruxelles?`
- API: `POST /agents/switch/weather`

**Create custom agent**:
```python
from packages.core.agents import AgentConfig, register_agent

MY_AGENT = AgentConfig(
    id="my_agent",
    name="My Agent",
    icon="🤖",
    system_prompt="You are...",
    enabled_tools=["search_knowledge_base"],  # or None for all
)
register_agent(MY_AGENT)
```

## Adding Tools

```python
# packages/core/tools/my_tool.py
from pydantic_ai import RunContext
from packages.core.types import RAGContext

async def my_tool(ctx: RunContext[RAGContext], query: str) -> str:
    """Tool description (LLM reads this docstring)."""
    return f"Result: {query}"

# Register in packages/core/tools/__init__.py
_AVAILABLE_TOOLS = {
    "my_tool": my_tool,
    ...
}
```

## Configuration

```bash
# Required
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...

# Optional
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
SEARCH_SIMILARITY_THRESHOLD=0.25
QUERY_EXPANSION_ENABLED=true
```

## Make Commands

```bash
make install    # Install dependencies
make run        # Start dev servers
make test       # Run all tests
make ingest     # Ingest documents
make scrape     # Run web scraper
make lint       # Run linters
make format     # Format code
make help       # Show all commands
```

## License

Apache 2.0
