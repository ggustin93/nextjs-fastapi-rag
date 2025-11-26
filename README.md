# nextjs-fastapi-rag

An open-source RAG (Retrieval-Augmented Generation) pipeline for building document-based Q&A applications. Combines vector similarity search with LLM responses to answer questions from your own documents.

## Features

- **Streaming Chat** - Real-time responses via Server-Sent Events
- **Semantic Search** - pgvector cosine similarity (1536-dim embeddings)
- **Multi-Format Ingestion** - PDF, Word, HTML, Markdown via Docling
- **Web Scraping** - Crawl4AI for automated content extraction
- **Source Citations** - Every response includes document sources
- **Multi-Provider LLM** - OpenAI, Ollama, or any OpenAI-compatible API

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
│   ├── ingestion/          # Docling chunker, embedder
│   ├── scraper/            # Crawl4AI web scraper
│   ├── config/             # Centralized settings
│   └── utils/              # DB, cache, providers
├── services/
│   ├── api/                # FastAPI backend
│   └── web/                # Next.js frontend
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # API integration tests
├── deploy/                 # Docker configuration
├── sql/                    # Database schema
├── data/                   # Documents for ingestion
├── .github/workflows/      # CI/CD pipelines
├── pyproject.toml          # Python dependencies
├── docker-compose.yml      # Local orchestration
└── Makefile                # Development commands
```

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 20+
- PostgreSQL with pgvector extension
- OpenAI API key

### Installation

```bash
# Clone repository
git clone <repo-url>
cd nextjs-fastapi-rag

# Install dependencies
make install

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

## Testing

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

### Makefile

```bash
make help              # Show all commands
make lint              # Run linters
make format            # Format code
make clean             # Remove artifacts
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

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| PydanticAI | Type safety, simpler than LangChain |
| pgvector | Self-hosted, ACID compliance |
| Docling | Better PDF parsing than alternatives |
| SSE | Simpler than WebSocket for chat |
| UV | Faster than pip |

## Disclaimer

This project was developed with assistance from [Claude Code](https://claude.ai/claude-code), Anthropic's AI coding assistant.

## License

Apache 2.0
