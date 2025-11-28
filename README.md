# nextjs-fastapi-rag

A production-ready, domain-agnostic RAG (Retrieval-Augmented Generation) system for building document-based Q&A applications. Clean architecture with optional domain customization and external API integration.

## Features

- **Streaming Chat** - Real-time responses via Server-Sent Events (SSE)
- **Hybrid Search** - Vector similarity + French full-text search with re-ranking
- **Multi-Format Ingestion** - PDF, Word, HTML, Markdown via Docling
- **Web Scraping** - Crawl4AI for automated content extraction
- **Source Citations** - Every response includes ranked document sources
- **Multi-Provider LLM** - OpenAI, Ollama, or any OpenAI-compatible API
- **Domain-Agnostic** - Works generically or with optional domain configuration
- **Extensible** - Add external API tools following clean patterns

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, PydanticAI, Uvicorn, AsyncPG |
| Database | PostgreSQL + pgvector |
| AI/ML | OpenAI, Docling, Crawl4AI |
| Testing | Pytest, Jest |
| DevOps | Docker, GitHub Actions, UV |

## Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        UI[Next.js App]
    end

    subgraph API["API Layer"]
        GW[FastAPI]
        AGENT[PydanticAI Agent]
    end

    subgraph Data["Data Layer"]
        PG[(PostgreSQL)]
        VEC[pgvector]
        CACHE[AsyncLRUCache]
    end

    subgraph External["External Services"]
        LLM[OpenAI API]
        EMB[Embeddings API]
    end

    subgraph Pipeline["Ingestion Pipeline"]
        CRAWL[Crawl4AI]
        DOC[Docling]
        CHUNK[HybridChunker]
        EMBED[EmbeddingGenerator]
    end

    UI -->|SSE| GW
    GW --> AGENT
    AGENT --> PG
    PG --> VEC
    AGENT --> CACHE
    AGENT --> LLM
    AGENT --> EMB

    CRAWL --> DOC
    DOC --> CHUNK
    CHUNK --> EMBED
    EMBED --> PG
```

## Project Structure

```
nextjs-fastapi-rag/
├── packages/
│   ├── core/               # RAG agent, CLI
│   │   ├── config/         # Optional domain configuration
│   │   └── tools/          # External API tool patterns
│   ├── ingestion/          # Docling chunker, embedder
│   ├── scraper/            # Crawl4AI web scraper
│   ├── config/             # Centralized settings
│   └── utils/              # DB, cache, providers
├── services/
│   ├── api/                # FastAPI backend
│   └── web/                # Next.js frontend
├── tests/
│   ├── unit/               # Unit tests
│   ├── integration/        # API integration tests
│   └── results/            # Evaluation metrics
├── scripts/                # Utility scripts
├── data/                   # Documents for ingestion
├── pyproject.toml          # Python dependencies
└── Makefile                # Development commands
```

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 20+
- PostgreSQL with pgvector extension
- OpenAI API key

### Quick Start

```bash
# Install dependencies
make install

# Setup pre-commit hooks (recommended)
make pre-commit-install

# Configure environment
cp .env.example .env
# Edit .env with DATABASE_URL and OPENAI_API_KEY

# Initialize database
psql $DATABASE_URL < sql/schema.sql

# Ingest documents
make ingest

# Start servers
make run
```

### Endpoints

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Health | http://localhost:8000/health |
| API Docs | http://localhost:8000/docs |

## Development

### Code Quality

Pre-commit hooks automatically check code quality before each commit:

```bash
# Install hooks (one-time setup)
make pre-commit-install

# Run checks manually
make pre-commit

# Update hook versions
make pre-commit-update
```

**What's checked:**
- **Python**: Ruff linting and formatting
- **JavaScript/TypeScript**: ESLint and type checking
- **General**: Trailing whitespace, EOF newlines, YAML syntax, secret detection

### Testing

```bash
make test              # All tests
make test-backend      # Backend only
make test-frontend     # Frontend only
make test-unit         # Unit tests only
```

## DevOps

### Docker

```bash
make docker-build      # Build images
make docker-up         # Start containers
make docker-down       # Stop containers
```

### CI/CD

GitHub Actions runs on push/PR:
- Linting (ruff, eslint)
- Type checking (mypy, tsc)
- Unit tests
- Integration tests

### Make Commands

```bash
make help                  # Show all available commands
make install               # Install dependencies
make pre-commit-install    # Setup pre-commit hooks
make pre-commit            # Run quality checks
make run                   # Start dev servers
make test                  # Run all tests
make ingest                # Ingest documents
make lint                  # Run linters
make format                # Format code
make clean                 # Remove artifacts
```

## Configuration

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db
OPENAI_API_KEY=sk-...

# Optional
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
```

## Customization

### System Prompt

Customize the RAG agent's behavior via `RAG_SYSTEM_PROMPT` environment variable:

```bash
# Example: Legal domain
export RAG_SYSTEM_PROMPT="Tu es un expert juridique belge..."
```

Default: Generic French knowledge assistant with numbered source citations.

### Optional Domain Configuration

The system works generically by default. Add domain-specific query expansion:

```python
from packages.core.config import DomainConfig, QueryExpansionConfig

# Generic RAG (default)
domain_config = DomainConfig()

# With domain-specific query expansion
domain_config = DomainConfig(
    query_expansion=QueryExpansionConfig(
        type_d={"synonyms": [...], "criteria": [...]}
    )
)
```

### External API Integration

Add external API tools following the pattern in `packages/core/tools/external_api_example.py`:

1. Create type-safe Pydantic models for API responses
2. Define configuration with feature flags
3. Implement async tool function with dependency injection
4. Register conditionally based on configuration

See weather API example for complete implementation pattern.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Domain-Agnostic Core** | Generic by default, optional domain customization |
| **Dependency Injection** | Type-safe context via PydanticAI RunContext |
| **Optional Configuration** | All domain features opt-in, not required |
| **PydanticAI** | Type safety, simpler than LangChain |
| **Hybrid Search** | Vector + FTS + re-ranking for better retrieval |
| **pgvector** | Self-hosted, ACID compliance |
| **Docling** | Better PDF parsing than alternatives |
| **SSE** | Simpler than WebSocket for streaming chat |
| **UV** | Faster dependency resolution than pip |

## Architecture Principles

- **SOLID**: Single responsibility, dependency inversion
- **KISS**: Simple solutions over complex abstractions
- **DRY**: Reusable configuration and tool patterns
- **YAGNI**: No speculative features, build what's needed

## Disclaimer

This project was developed with assistance from [Claude Code](https://claude.ai/claude-code), Anthropic's AI coding assistant.

## License

Apache 2.0
