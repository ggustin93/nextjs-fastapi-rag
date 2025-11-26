# Project Structure - nextjs-fastapi-rag

## Directory Tree

```
nextjs-fastapi-rag/
├── packages/                    # 📦 Core Python packages
│   ├── core/                    # RAG agent and CLI
│   │   ├── __init__.py
│   │   ├── agent.py             # 🤖 RAG agent core (PydanticAI)
│   │   └── cli.py               # 💬 Enhanced CLI interface
│   ├── ingestion/               # 🔄 Document processing pipeline
│   │   ├── __init__.py
│   │   ├── ingest.py            # Main ingestion orchestrator
│   │   ├── chunker.py           # Hybrid document chunking
│   │   └── embedder.py          # OpenAI embedding generation
│   └── utils/                   # 🛠️ Shared utilities
│       ├── __init__.py
│       ├── db_utils.py          # Database connection pooling
│       ├── models.py            # Pydantic data models
│       ├── providers.py         # OpenAI client configuration
│       └── supabase_client.py   # Supabase client wrapper
├── services/                    # 🌐 Deployable services
│   ├── api/                     # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py          # FastAPI application
│   │   │   ├── core/            # RAG wrapper, config
│   │   │   └── routers/         # API endpoints (chat, health)
│   │   └── requirements.txt
│   └── web/                     # Next.js frontend
│       ├── src/
│       │   ├── app/             # App router pages
│       │   ├── components/      # React components
│       │   ├── hooks/           # Custom hooks (useChat)
│       │   └── lib/             # Utilities (api-client)
│       └── package.json
├── deploy/                      # 🐳 Docker configuration
│   ├── Dockerfile               # Container definition
│   └── docker-compose.yml       # Service orchestration
├── tests/                       # 🧪 Test suite
│   ├── conftest.py              # Pytest fixtures
│   ├── test_api.py              # FastAPI health tests
│   ├── test_api_integration.py  # Frontend-backend tests
│   ├── test_cache.py            # EmbeddingCache tests
│   └── test_chunker.py          # ChunkingConfig tests
├── docs/                        # 📚 Project documentation
│   ├── architecture.md          # System architecture
│   ├── api-reference.md         # API documentation
│   ├── project-structure.md     # This file
│   └── quickstart.md            # Getting started guide
├── data/                        # 📊 Data and examples
│   └── examples/                # Docling tutorials
├── documents/                   # 📄 Documents for ingestion
│   ├── active/                  # Documents to be processed
│   └── archive/                 # Reference documents
├── sql/                         # 🗄️ Database schema
│   └── schema.sql               # PostgreSQL + PGVector schema
├── scripts/                     # 🔧 Utility scripts
│   └── restart-servers.sh       # Server restart script
├── pyproject.toml               # Project config and dependencies
├── uv.lock                      # Dependency lock file
├── .env                         # Environment variables (not in git)
├── .gitignore                   # Git ignore patterns
└── README.md                    # Main project documentation
```

---

## Core Packages

### `packages/core/`

#### `agent.py`
**Purpose**: Core RAG agent with PydanticAI

**Key Components**:
- Agent initialization with system prompt
- `search_knowledge_base` tool implementation
- Conversation history management
- Vector similarity search integration

**Usage**:
```bash
uv run python -m packages.core.agent
```

**Dependencies**: pydantic-ai, asyncpg, openai, numpy

---

#### `cli.py`
**Purpose**: Enhanced CLI interface with rich features

**Key Features**:
- Colored output using ANSI codes
- Session statistics tracking
- Real-time streaming responses
- Database health checks
- Interactive commands (help, stats, clear)

**Usage**:
```bash
uv run python -m packages.core.cli
```

**Dependencies**: asyncpg, pydantic-ai, openai, python-dotenv

---

### `packages/ingestion/`

#### `ingest.py`
**Purpose**: Main document ingestion orchestrator

**Key Features**:
- Multi-format document support (PDF, DOCX, MP3, etc.)
- Docling-based parsing with fallback options
- Batch processing with progress tracking
- Automatic embedding generation

**Usage**:
```bash
uv run python -m packages.ingestion.ingest --documents ./documents/active
```

---

#### `chunker.py`
**Purpose**: Hybrid document chunking with semantic awareness

**Key Features**:
- Configurable chunk size and overlap
- Token-aware splitting
- Metadata preservation
- Pydantic validation

**Classes**:
- `ChunkingConfig`: Configuration with validation
- `DocumentChunk`: Data structure for chunks

---

#### `embedder.py`
**Purpose**: OpenAI embedding generation with caching

**Key Features**:
- Batch embedding generation
- LRU cache for efficiency
- Configurable model selection

**Classes**:
- `EmbeddingCache`: LRU cache implementation

---

### `packages/utils/`

#### `db_utils.py`
**Purpose**: Database connection pooling and utilities

**Key Features**:
- AsyncPG connection pool management
- Query helpers
- Health check functions

---

#### `supabase_client.py`
**Purpose**: Supabase client wrapper

**Key Features**:
- Singleton client instance
- Environment-based configuration
- Storage and database access

---

## Services

### `services/api/`
**Purpose**: FastAPI backend for RAG queries

**Endpoints**:
- `GET /` - API info
- `GET /health` - Health check
- `GET /api/v1/chat/health` - Chat service health
- `POST /api/v1/chat/stream` - Streaming RAG responses (SSE)

**Run**:
```bash
cd services/api && uvicorn app.main:app --reload
```

---

### `services/web/`
**Purpose**: Next.js frontend for chat interface

**Key Components**:
- `src/hooks/useChat.ts` - Chat state management
- `src/lib/api-client.ts` - Backend API communication
- `src/components/` - React UI components

**Run**:
```bash
cd services/web && npm run dev
```

---

## Test Suite

### Running Tests
```bash
# Install test dependencies
uv pip install -e ".[test]"

# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=packages --cov-report=term-missing
```

### Test Files
- `test_api.py` - FastAPI health endpoint tests
- `test_api_integration.py` - Frontend-backend contract tests
- `test_cache.py` - EmbeddingCache LRU behavior tests
- `test_chunker.py` - ChunkingConfig validation tests

---

## Docker Deployment

### Build and Run
```bash
cd deploy
docker-compose up --build
```

### Services
- `rag-agent`: Core agent service
- `ingestion`: Document processing service
- `api`: FastAPI backend
- `web`: Next.js frontend

---

## Configuration Files

### `pyproject.toml`
**Sections**:
- `[project]`: Metadata, dependencies
- `[project.scripts]`: CLI entry points
- `[project.optional-dependencies]`: Test dependencies
- `[tool.setuptools.packages.find]`: Package discovery

### `.env`
**Required Variables**:
```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
DATABASE_URL=postgresql://...
```

---

## Import Patterns

### From packages
```python
from packages.core.agent import agent, search_knowledge_base
from packages.ingestion.chunker import ChunkingConfig, DocumentChunk
from packages.ingestion.embedder import EmbeddingCache
from packages.utils.supabase_client import get_supabase_client
```

### From services/api
```python
from app.core.rag_wrapper import stream_agent_response
from app.routers.chat import router
```
