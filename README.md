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

## Detailed System Architecture

### System Components

```mermaid
flowchart LR
    subgraph Client["🎨 Presentation Layer"]
        UI[Next.js App<br/>App Router + useChat Hook]
    end

    subgraph API["🔌 API Gateway Layer"]
        GW[FastAPI Gateway<br/>CORS + Middleware]
        HEALTH[Health Checks<br/>Liveness/Readiness]
    end

    subgraph Logic["🧠 Business Logic Layer"]
        AGENT[PydanticAI Agent<br/>RAG Orchestration]
        CTX[RAGContext<br/>Dependency Injection]
        TOOLS[Tool System<br/>search_knowledge_base]
    end

    subgraph Data["💾 Data & Cache Layer"]
        CACHE[AsyncLRUCache<br/>Query + Metadata]
        PG[(PostgreSQL<br/>+ pgvector)]
        HISTORY[Message History<br/>Per Session]
    end

    subgraph Config["⚙️ Configuration Layer"]
        CONF[Centralized Config<br/>Multi-Provider LLM]
        DOMAIN[Domain Config<br/>Optional Synonyms]
    end

    subgraph External["☁️ External Services"]
        LLM[OpenAI/Ollama<br/>Chutes.ai]
        EMB[Embeddings API<br/>text-embedding-3]
        DOC[Docling + Crawl4AI<br/>Document Processing]
    end

    %% Critical SSE Streaming Path
    UI -.->|SSE Stream<br/>token/sources/done| GW
    GW -.->|Progressive Updates| UI

    %% API Layer Connections
    UI -->|POST /api/v1/chat/stream| GW
    GW --> HEALTH
    GW --> AGENT

    %% Business Logic Flow
    AGENT --> CTX
    CTX -.->|Injects deps| AGENT
    AGENT --> TOOLS
    TOOLS -->|See RAG Pipeline ⭐| CACHE

    %% Data Layer with Cache-First
    CACHE -->|Cache Miss| PG
    PG -->|Vector + FTS| CACHE
    AGENT --> HISTORY

    %% Configuration
    CONF -.->|LLM Provider| AGENT
    DOMAIN -.->|Query Expansion| TOOLS

    %% External Services
    AGENT --> LLM
    AGENT --> EMB
    DOC --> PG

    %% Styling
    style Client fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style API fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style Logic fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style Data fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style Config fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    style External fill:#f5f5f5,stroke:#616161,stroke-width:2px

    %% Annotations
    classDef criticalPath stroke:#c62828,stroke-width:3px,stroke-dasharray: 5 5
    class UI,GW criticalPath
```

Our RAG system uses a layered architecture with sophisticated patterns:

**Key Architectural Patterns:**
- **Streaming SSE**: Real-time progressive updates via Server-Sent Events (not WebSocket)
- **Dependency Injection**: Type-safe context via PydanticAI RunContext
- **Cache-First Strategy**: AsyncLRUCache before database queries
- **4-Stage RAG Pipeline**: See [RAG Search Pipeline](#rag-search-pipeline) section below for details
- **Multi-Provider LLM**: Configuration-driven (OpenAI, Ollama, Chutes.ai)
- **Tool System**: Extensible external API integration pattern

### Request Flow

```mermaid
sequenceDiagram
    participant FE as Frontend<br/>(useChat Hook)
    participant API as FastAPI<br/>(chat.py)
    participant Agent as RAG Agent<br/>(PydanticAI)
    participant Tools as search_knowledge_base
    participant DB as PostgreSQL<br/>+ pgvector
    participant LLM as OpenAI API

    FE->>API: POST /api/v1/chat/stream<br/>{message, session_id}
    activate API

    API->>Agent: Create RAGContext + Agent instance
    API->>Agent: Run agent with message
    activate Agent

    Agent->>Tools: search_knowledge_base(query)
    activate Tools
    Tools->>DB: Hybrid Search (Vector + FTS)
    DB-->>Tools: 20 chunks
    Tools->>Tools: Filter TOC + FlashRank
    Tools-->>Agent: Top 10 sources
    deactivate Tools

    Agent->>LLM: Generate response with context
    activate LLM

    loop Streaming Tokens
        LLM-->>Agent: Token chunk
        Agent-->>API: event: "token"
        API-.->FE: SSE: data: {"token": "..."}
        Note over FE: Append to message in real-time
    end

    LLM-->>Agent: Complete response
    deactivate LLM

    Agent-->>API: event: "sources"
    API-.->FE: SSE: data: {"sources": [...]}
    Note over FE: Update sources + cited indices

    Agent-->>API: event: "done"
    API-.->FE: SSE: data: "done"
    deactivate Agent

    Note over FE: Stream complete, show sources
    deactivate API
```

This sequence diagram shows how a chat request flows through the system with progressive streaming updates.

## RAG Search Pipeline

Our RAG system uses a sophisticated 4-stage pipeline to ensure high-quality, relevant responses:

### Pipeline Overview

```mermaid
flowchart TD
    subgraph Input["🔍 Stage 1: Query Processing"]
        Query[User Query]
        Query --> Reform[Reformulate Query<br/>semantic matching]
        Query --> Expand[Expand Query<br/>domain synonyms]
        Reform --> Embed[Generate Embeddings]
    end

    subgraph Search["🔎 Stage 2: Hybrid Search - 20 Chunks"]
        Embed --> Vector[Vector Similarity<br/>Semantic Search]
        Expand --> FTS[Full-Text Search<br/>French + Keyword]
        Vector --> RRF[Reciprocal Rank Fusion]
        FTS --> RRF
        RRF --> Results20[20 Ranked Chunks]
    end

    subgraph Filter["🧹 Stage 3: Quality Filtering"]
        Results20 --> TOC{Filter TOC<br/>Chunks?}
        TOC -->|Remove| Discard[❌ Discard TOC]
        TOC -->|Keep| Clean[Clean Results]
    end

    subgraph Rerank["⭐ Stage 4: Re-ranking - Top 10"]
        Clean --> Flash[FlashRank Re-ranking<br/>Precision Optimization]
        Flash --> Top10[Top 10 Most Relevant]
        Top10 --> LLM[🤖 Feed ALL 10 to LLM]
    end

    LLM --> Response[📝 Response with Citations]

    style Input fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style Search fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style Filter fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style Rerank fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style Response fill:#ffebee,stroke:#c62828,stroke-width:2px
```

### Stage Details

**🔍 Stage 1: Query Processing**
- **Query Reformulation**: Transforms user questions for better semantic matching
  - Example: "Quelle est la superficie..." → "la valeur de la superficie..."
- **Query Expansion**: Adds domain-specific synonyms for full-text search
  - Example: "type D" → "type D OR dispense OR 50 m² OR 24 heures"
- **Embedding Generation**: Creates vector representation for semantic search

**🔎 Stage 2: Hybrid Search (20 Chunks)**
- **Vector Similarity**: Semantic search using embeddings (finds conceptually similar content)
- **Full-Text Search**: Keyword matching with French language support
- **RRF Fusion**: Combines both approaches using Reciprocal Rank Fusion algorithm
- **Result**: 20 candidate chunks ranked by relevance

**🧹 Stage 3: Quality Filtering**
- **TOC Detection**: Removes table of contents chunks that pollute results
- **Content Validation**: Ensures only meaningful content passes through
- **Result**: Clean, relevant chunks ready for re-ranking

**⭐ Stage 4: Re-ranking (Top 10)**
- **FlashRank**: Advanced re-ranking model for precision optimization
- **Top Selection**: Keeps the 10 most relevant chunks
- **LLM Context**: ALL 10 chunks fed to LLM with full context
- **Result**: Response with numbered source citations [1], [2], etc.

### Configuration

Customize retrieval behavior via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARCH_DEFAULT_LIMIT` | 20 | Chunks retrieved in Stage 2 |
| `SEARCH_SIMILARITY_THRESHOLD` | 0.4 | Minimum similarity (40%) |
| `MAX_CHUNKS_PER_DOCUMENT` | 3 | Max chunks per document |
| `RERANK_ENABLED` | true | Enable FlashRank reranking |
| `REFORMULATE_QUERY_ENABLED` | true | Enable LLM query reformulation |

> **💡 Tip:** For definition-seeking queries or domain-specific content, try disabling reranking and reformulation. See [Troubleshooting Guide](docs/TROUBLESHOOT.md) for details.

See [Configuration](#configuration) section for more details.

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
├── data/                   # Data directory (gitignored except examples/)
│   ├── raw/pdfs/           # Manual PDF documents for ingestion
│   ├── processed/scraped/  # Web scraper output (auto-generated)
│   └── examples/           # Tutorial examples (tracked in git)
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

# LLM Settings (Optional)
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small

# Search Settings (Optional)
SEARCH_SIMILARITY_THRESHOLD=0.4     # Minimum similarity (0.0-1.0)
SEARCH_DEFAULT_LIMIT=20             # Chunks from hybrid search
MAX_CHUNKS_PER_DOCUMENT=3           # Limit per source document

# Feature Toggles (Optional)
RERANK_ENABLED=true                 # Enable FlashRank reranking
REFORMULATE_QUERY_ENABLED=true      # Enable LLM query reformulation
```

> **📖 Troubleshooting:** If retrieval quality is poor for definition-seeking queries, see [docs/TROUBLESHOOT.md](docs/TROUBLESHOOT.md).

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
