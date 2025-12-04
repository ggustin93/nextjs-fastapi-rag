# nextjs-fastapi-rag

A domain-agnostic RAG (Retrieval-Augmented Generation) starter for building document-based Q&A applications. Clean architecture with optional domain customization.

<!-- ![Screenshot](docs/images/screenshot.png) -->

## Table of Contents

1. [Features](#1-features)
2. [Tech Stack](#2-tech-stack)
3. [Architecture](#3-architecture)
   - [3.1 Ingestion Pipeline](#31-ingestion-pipeline)
   - [3.2 Retrieval Pipeline](#32-retrieval-pipeline)
   - [3.3 Configuration](#33-configuration)
4. [Project Structure](#4-project-structure)
5. [Getting Started](#5-getting-started)
   - [5.1 Prerequisites](#51-prerequisites)
   - [5.2 Python Environment](#52-python-environment)
   - [5.3 Quick Start](#53-quick-start)
   - [5.4 Endpoints](#54-endpoints)
6. [Development](#6-development)
   - [6.1 Code Quality](#61-code-quality)
   - [6.2 Testing](#62-testing)
7. [DevOps](#7-devops)
   - [7.1 Docker](#71-docker)
   - [7.2 CI/CD](#72-cicd)
   - [7.3 Make Commands](#73-make-commands)
8. [Configuration](#8-configuration)
9. [Customization](#9-customization)
   - [9.1 System Prompt](#91-system-prompt)
   - [9.2 Adding Custom Tools](#92-adding-custom-tools)
   - [9.3 Agent Configuration](#93-agent-configuration)
10. [Design Decisions](#10-design-decisions)
11. [License](#11-license)

## 1. Features

- **Streaming Chat** - Real-time responses via Server-Sent Events (SSE)
- **Hybrid Search** - Vector similarity + full-text search with RRF fusion
- **Multi-Format Ingestion** - PDF, Word, HTML, Markdown via Docling
- **Web Scraping** - Crawl4AI for automated content extraction
- **Source Citations** - Every response includes ranked document sources
- **Multi-Provider LLM** - OpenAI, Ollama, or any OpenAI-compatible API
- **Domain-Agnostic** - Works generically or with optional domain configuration
- **Extensible** - Add external API tools following clean patterns

## 2. Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, PydanticAI |
| Database | PostgreSQL + pgvector |
| AI/ML | OpenAI, Docling, Crawl4AI |
| Testing | Pytest, Jest |
| DevOps | Docker, GitHub Actions, UV |

## 3. Architecture

### System Overview

```mermaid
graph TB
    subgraph "Client Layer"
        USER[👤 User]
    end

    subgraph "Frontend Service"
        NEXT["`**Next.js**<br/>:3000`"]
    end

    subgraph "Backend Service"
        API["`**FastAPI**<br/>:8000`"]
    end

    subgraph "Data Layer"
        DB[("`**PostgreSQL**<br/>pgvector`")]
    end

    subgraph "External Services"
        OPENAI["`**OpenAI**`"]
    end

    subgraph "Document Sources"
        PDF[📄 PDF]
        WEB[🌐 Web]
    end

    USER -->|`*requests*`| NEXT
    NEXT -->|`*API calls*`| API
    API <-->|`*vector search*`| DB
    API <-->|`*LLM*`| OPENAI
    PDF -->|`*ingest*`| API
    WEB -->|`*scrape*`| API

    style USER fill:#e1f5ff,stroke:#0288d1
    style NEXT fill:#dcedc8,stroke:#689f38
    style API fill:#fff9c4,stroke:#fbc02d
    style DB fill:#f3e5f5,stroke:#7b1fa2
    style OPENAI fill:#ffe0b2,stroke:#f57c00
    style PDF fill:#ffebee,stroke:#c62828
    style WEB fill:#e0f2f1,stroke:#00695c
```

**Key Components**:
- **Frontend**: SSE streaming
- **Backend**: RAG pipeline
- **Database**: Semantic search
- **AI Services**: Embeddings (1536D) + LLM
- **Ingestion**: Docling (PDF) + Crawl4AI (Web)

### 3.1 Ingestion Pipeline

```mermaid
graph LR
    subgraph Sources
        PDF[PDF Files]
        WEB[Web Pages]
    end

    PDF --> DOC[Docling]
    WEB --> C4A[Crawl4AI]
    DOC --> MD[Markdown]
    C4A --> MD
    MD --> CHK[Chunking]
    CHK --> EMB[Embeddings]
    EMB --> DB[(pgvector)]

    style PDF fill:#ffe4e6,stroke:#f43f5e
    style WEB fill:#e0f2fe,stroke:#0ea5e9
    style DOC fill:#ffe4e6,stroke:#f43f5e
    style C4A fill:#e0f2fe,stroke:#0ea5e9
    style CHK fill:#fef3c7,stroke:#f59e0b
    style EMB fill:#d1fae5,stroke:#10b981
    style DB fill:#d1fae5,stroke:#10b981
```

| Step | Tool | Description |
|------|------|-------------|
| **Parse** | Docling | Parses PDFs preserving structure (tables, headers, lists) |
| **Scrape** | Crawl4AI | Scrapes websites with JS rendering, extracts clean markdown |
| **Chunk** | HybridChunker | Splits into ~512 token chunks with 50 overlap |
| **Embed** | OpenAI | text-embedding-3-small → 1536D vectors in pgvector |

### 3.2 Retrieval Pipeline

```mermaid
graph LR
    Q[Query] --> QE[Query Expansion]
    QE --> E[Embed]
    E --> V[(pgvector)]
    E --> F[Full-Text Search]
    V --> |Top-K| R[RRF Fusion]
    F --> |Top-K| R
    R --> TR[Title Rerank]
    TR --> C[Context]
    C --> L[LLM]
    L --> S[Stream SSE]

    style Q fill:#f1f5f9,stroke:#64748b
    style QE fill:#fef3c7,stroke:#f59e0b
    style V fill:#ede9fe,stroke:#8b5cf6
    style F fill:#e0e7ff,stroke:#6366f1
    style R fill:#ccfbf1,stroke:#14b8a6
    style TR fill:#fce7f3,stroke:#ec4899
    style L fill:#fef3c7,stroke:#d97706
    style S fill:#dcfce7,stroke:#16a34a
```

| Step | Component | Description |
|------|-----------|-------------|
| **1. Query Expansion** | LLM (gpt-4o-mini) | Adds domain synonyms to improve recall |
| **2. Vector Search** | pgvector | Cosine similarity on 1536D embeddings |
| **3. Full-Text Search** | PostgreSQL | Keyword search with language stemming |
| **4. RRF Fusion** | Custom | Merges rankings with k=50 |
| **5. Title Rerank** | Custom | Boosts documents with matching titles +15% |

> **RAG Best Practices**: Query Expansion fixes vocabulary mismatch between user queries and document terminology. Title Reranking improves precision by surfacing documents with relevant titles.

### 3.3 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `QUERY_EXPANSION_ENABLED` | true | Enable LLM query expansion |
| `QUERY_EXPANSION_MODEL` | gpt-4o-mini | Model for query expansion |
| `TITLE_RERANK_ENABLED` | true | Enable title-based reranking |
| `TITLE_RERANK_BOOST` | 0.15 | Max boost for title matches (+15%) |
| `SEARCH_DEFAULT_LIMIT` | 30 | Max chunks from hybrid search |
| `SEARCH_SIMILARITY_THRESHOLD` | 0.25 | Minimum similarity (25%) |
| `RRF_K` | 50 | RRF ranking parameter |
| `EXCLUDE_TOC` | true | Filter out TOC chunks |

## 4. Project Structure

```
nextjs-fastapi-rag/
├── packages/                   # Shared Python packages (pip install -e .)
│   ├── core/                   # RAG agent, CLI
│   │   ├── config/             # Optional domain configuration
│   │   └── tools/              # External API tool patterns
│   ├── ingestion/              # Docling chunker, embedder
│   ├── scraper/                # Crawl4AI web scraper
│   ├── config/                 # Centralized settings
│   └── utils/                  # DB client, cache, providers
├── services/
│   ├── api/                    # FastAPI backend (see below)
│   └── web/                    # Next.js frontend (see below)
├── tests/
│   ├── unit/                   # Unit tests (pytest)
│   ├── integration/            # API integration tests
│   └── results/                # Evaluation metrics
├── scripts/                    # Utility scripts
├── data/                       # Data directory (gitignored except examples/)
│   ├── raw/pdfs/               # Manual PDF documents for ingestion
│   ├── processed/scraped/      # Web scraper output (auto-generated)
│   └── examples/               # Tutorial examples (tracked in git)
├── sql/                        # Database schema and migrations
├── pyproject.toml              # Python dependencies
└── Makefile                    # Development commands
```

### 4.1 Backend Structure (`services/api/`)

FastAPI application exposing REST + SSE endpoints for RAG operations.

```
services/api/
├── app/
│   ├── main.py             # FastAPI app, lifespan, CORS
│   ├── api/                # Route handlers
│   │   ├── chat.py         # POST /chat/stream - SSE streaming chat
│   │   ├── documents.py    # GET /documents - File serving
│   │   ├── health.py       # GET /health - Health check
│   │   └── system.py       # GET /system/models - LLM config
│   ├── core/
│   │   └── rag_wrapper.py  # RAG agent wrapper, history management
│   └── middleware/         # Request logging, error handling
└── README.md
```

**Key Files:**
| File | Purpose |
|------|---------|
| `main.py` | App initialization, singleton resources (embedder, DB client) |
| `chat.py` | Streaming endpoint using `StreamingResponse` + SSE |
| `rag_wrapper.py` | Wraps `packages.core.agent`, manages conversation history |

### 4.2 Frontend Structure (`services/web/`)

Next.js 15 application with App Router, TypeScript, and shadcn/ui.

```
services/web/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx          # Root layout with providers
│   │   ├── page.tsx            # Home page (chat interface)
│   │   └── api/                # API routes (if needed)
│   ├── components/
│   │   ├── chat/               # Chat-specific components
│   │   │   ├── ChatContainer.tsx   # Main chat wrapper
│   │   │   ├── ChatInput.tsx       # Message input with submit
│   │   │   ├── ChatLayout.tsx      # Responsive layout
│   │   │   ├── ChatMessage.tsx     # Message bubble with sources
│   │   │   ├── DocumentPanel.tsx   # Side panel for doc preview
│   │   │   ├── DocumentViewer.tsx  # PDF/Markdown viewer
│   │   │   ├── PdfViewer.tsx       # react-pdf integration
│   │   │   ├── LLMSelector.tsx     # Model dropdown
│   │   │   └── ToolCallBadge.tsx   # Tool activity indicator
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── Providers.tsx       # Theme, query providers
│   │   └── ErrorBoundary.tsx   # Error handling
│   ├── hooks/
│   │   ├── useChat.ts          # SSE streaming, message state
│   │   └── useMediaQuery.ts    # Responsive breakpoints
│   ├── lib/
│   │   ├── api-client.ts       # Typed API calls to backend
│   │   └── utils.ts            # cn(), formatters
│   └── types/                  # TypeScript interfaces
├── public/                     # Static assets
├── next.config.ts              # Next.js configuration
├── tailwind.config.ts          # Tailwind + shadcn theming
└── package.json
```

**Key Components:**
| Component | Purpose |
|-----------|---------|
| `ChatContainer` | Orchestrates chat state, connects to `useChat` hook |
| `ChatMessage` | Renders messages with markdown, source citations |
| `DocumentViewer` | Displays PDF/MD with page navigation |
| `useChat` | SSE streaming hook, handles `EventSource` parsing |
| `api-client` | Typed fetch wrapper for `/api/v1/*` endpoints |

## 5. Getting Started

### 5.1 Prerequisites

- Python 3.10+ (required for PydanticAI 1.x)
- Node.js 20+
- PostgreSQL with pgvector extension
- OpenAI API key

### 5.2 Python Environment

This project uses a **single virtual environment** at the project root:

```bash
# Create venv (if not exists)
uv venv .venv --python 3.11

# Install dependencies
uv pip install -e .

# Or with pip
pip install -e .
```

### 5.3 Quick Start

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

### 5.4 Endpoints

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Health | http://localhost:8000/health |
| API Docs | http://localhost:8000/docs |

## 6. Development

### 6.1 Code Quality

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

### 6.2 Testing

```bash
make test              # All tests
make test-backend      # Backend only
make test-frontend     # Frontend only
make test-unit         # Unit tests only
```

## 7. DevOps

### 7.1 Docker

```bash
make docker-build      # Build images
make docker-up         # Start containers
make docker-down       # Stop containers
```

### 7.2 CI/CD

GitHub Actions runs on push/PR:
- Linting (ruff, eslint)
- Type checking (mypy, tsc)
- Unit tests
- Integration tests

### 7.3 Make Commands

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

## 8. Configuration

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db
OPENAI_API_KEY=sk-...

# LLM Settings (Optional)
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small

# Search Settings (Optional)
SEARCH_SIMILARITY_THRESHOLD=0.25    # Minimum similarity (0.0-1.0)
OUT_OF_SCOPE_THRESHOLD=0.40         # Below this = out of scope question
SEARCH_DEFAULT_LIMIT=30             # Max chunks from hybrid search
MAX_CHUNKS_PER_DOCUMENT=5           # Limit per source document
RRF_K=50                            # RRF ranking parameter
EXCLUDE_TOC=true                    # Filter out TOC chunks
```

## 9. Customization

### 9.1 System Prompt

Customize the RAG agent's behavior via `RAG_SYSTEM_PROMPT` environment variable:

```bash
# Example: Custom domain
export RAG_SYSTEM_PROMPT="You are an expert assistant for..."
```

Default: Generic knowledge assistant with numbered source citations.

### 9.2 Adding Custom Tools

Tools use PydanticAI's `RunContext` pattern for dependency injection:

```python
from pydantic_ai import RunContext
from packages.core.types import RAGContext

async def my_custom_tool(
    ctx: RunContext[RAGContext],
    query: str,
    option: bool = False
) -> str:
    """Tool description - the LLM reads this docstring.

    Args:
        ctx: RAG context with dependencies (db_client, etc.)
        query: User's search query
        option: Optional parameter

    Returns:
        Formatted result string
    """
    # Access shared resources via context
    db = ctx.deps.db_client

    # Your tool logic
    return f"Result for: {query}"
```

Then register in `packages/core/tools/__init__.py`:

```python
from packages.core.tools.my_tool import my_custom_tool

_AVAILABLE_TOOLS = {
    "search_knowledge_base": search_knowledge_base,
    "weather": get_weather,
    "my_tool": my_custom_tool,  # Add here
}
```

See `packages/core/tools/weather_tool.py` for a complete implementation example.

### 9.3 Agent Configuration

Create custom agent instances using the factory pattern:

```python
from packages.core.factory import create_rag_agent

# Default configuration
agent = create_rag_agent()

# Custom configuration
agent = create_rag_agent(
    system_prompt="Custom instructions",
    enabled_tools=["weather"]  # or [] for search only
)
```

The factory ensures consistent configuration across CLI, API, and tests.

## 10. Design Decisions

| Choice | Why |
|--------|-----|
| **PydanticAI** | Type-safe agents, simpler than LangChain |
| **Hybrid Search** | Vector + FTS + RRF fusion beats pure vector search |
| **pgvector** | Self-hosted, ACID-compliant, no vendor lock-in |
| **Docling** | Best PDF structure preservation (tables, headers) |
| **SSE Streaming** | Simpler than WebSocket for chat responses |

## 11. License

Apache 2.0
