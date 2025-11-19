# Project Structure - Docling RAG Agent

## Directory Tree

```
osiris-multirag-agent/  (aka docling-rag-agent)
├── .claude/                     # Claude Code configuration
├── .venv/                       # Python virtual environment
├── archives/                    # Archived/experimental code
│   └── ottomator-agents/        # Previous agent implementations
├── claudedocs/                  # 📚 Project documentation (this folder)
│   ├── architecture.md          # System architecture and design
│   ├── api-reference.md         # Complete API documentation
│   ├── project-structure.md     # This file
│   └── development-guide.md     # Development and contribution guide
├── docling_basics/              # 🎓 Docling learning tutorials
│   ├── README.md                # Tutorial overview and index
│   ├── 01_simple_pdf.py         # Basic PDF conversion
│   ├── 02_multiple_formats.py   # Multi-format document handling
│   ├── 03_audio_transcription.py # Whisper ASR integration
│   ├── 04_hybrid_chunking.py    # Advanced chunking strategies
│   └── output/                  # Tutorial output samples
├── documents/                   # 📄 Documents for ingestion
│   └── [various formats]        # PDF, DOCX, MP3, etc.
├── ingestion/                   # 🔄 Document processing pipeline
│   ├── __init__.py              # Module initialization
│   ├── ingest.py                # Main ingestion orchestrator
│   ├── chunker.py               # Hybrid document chunking
│   ├── chunker_no_docling.py    # Legacy chunking (fallback)
│   └── embedder.py              # OpenAI embedding generation
├── sql/                         # 🗄️ Database schema and migrations
│   └── schema.sql               # PostgreSQL + PGVector schema
├── utils/                       # 🛠️ Shared utilities
│   ├── db_utils.py              # Database connection pooling
│   ├── models.py                # Pydantic data models
│   └── providers.py             # OpenAI client configuration
├── cli.py                       # 💬 Enhanced CLI interface (main entry)
├── rag_agent.py                 # 🤖 RAG agent core (PydanticAI)
├── pyproject.toml               # Project dependencies and config
├── uv.lock                      # Dependency lock file (uv)
├── .env                         # Environment variables (not in git)
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore patterns
├── .mcp.json                    # MCP server configuration
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Container definition
└── README.md                    # Main project documentation
```

---

## Core Files

### Entry Points

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
uv run python cli.py
```

**Lines of Code**: ~400
**Dependencies**: asyncpg, pydantic-ai, openai, python-dotenv

---

#### `rag_agent.py`
**Purpose**: Core RAG agent with PydanticAI

**Key Components**:
- Agent initialization with system prompt
- `search_knowledge_base` tool implementation
- Conversation history management
- Vector similarity search integration

**Usage**:
```bash
uv run python rag_agent.py  # Basic CLI without colors
```

**Lines of Code**: ~200
**Dependencies**: pydantic-ai, asyncpg, openai, numpy

---

### Configuration Files

#### `pyproject.toml`
**Purpose**: Python project configuration and dependencies

**Sections**:
- `[project]`: Metadata (name, version, description)
- `dependencies`: Required packages
- `[tool.black]`: Code formatting configuration
- `[tool.ruff]`: Linting rules
- `[tool.pytest]`: Test configuration
- `[tool.mypy]`: Type checking settings

**Key Dependencies**:
```toml
dependencies = [
    "python-dotenv>=1.0.0",
    "aiohttp>=3.9.0",
    "pydantic-ai>=0.7.4",
    "asyncpg>=0.30.0",
    "numpy>=2.0.2",
    "openai>=1.0.0",
    "docling>=2.55.0",
    "openai-whisper>=20250625",
    "supabase>=2.0.0"
]
```

---

#### `.env` & `.env.example`
**Purpose**: Environment variable configuration

**Required Variables**:
```bash
DATABASE_URL=postgresql://user:password@host:port/dbname
OPENAI_API_KEY=sk-...
```

**Optional Variables**:
```bash
LLM_CHOICE=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

**Security**: `.env` is gitignored, `.env.example` is committed as template

---

#### `.mcp.json`
**Purpose**: MCP (Model Context Protocol) server configuration

**Usage**: Configures external AI services and tools

---

### Docker Configuration

#### `Dockerfile`
**Purpose**: Container image definition

**Base Image**: Python 3.9+
**Exposed Port**: None (CLI application)
**Volumes**: `/app/documents` for document mounting

---

#### `docker-compose.yml`
**Purpose**: Multi-container orchestration

**Services**:
- `rag-agent`: Main application container
- `ingestion`: One-time ingestion job (profile)

**Features**:
- Environment variable injection
- Volume mounting for documents
- Network isolation

---

## Module Breakdown

### `ingestion/` Package

Purpose: Document processing and vector storage pipeline

#### `ingest.py`
**Primary Functions**:
- `ingest_documents()`: Main orchestration function
- `process_file()`: File type detection and routing
- `store_document()`: Database persistence
- `clear_database()`: Pre-ingestion cleanup

**Process Flow**:
```
Documents → Detect Type → Docling Processing →
Markdown Conversion → Chunking → Embedding → Storage
```

**Lines of Code**: ~600
**Key Dependencies**: docling, asyncpg, openai

---

#### `chunker.py`
**Primary Functions**:
- `chunk_document()`: Hybrid chunking with Docling
- `estimate_token_count()`: Token estimation for chunks
- `preserve_markdown_structure()`: Format preservation

**Chunking Strategy**:
- Docling HybridChunker for semantic splitting
- Configurable chunk size (default: 1000 chars)
- Overlap for context preservation
- Metadata tracking (chunk_index, token_count)

**Lines of Code**: ~350
**Key Dependencies**: docling

---

#### `chunker_no_docling.py`
**Purpose**: Legacy chunking without Docling dependency

**Use Case**: Fallback for simple text files or debugging

**Lines of Code**: ~450

---

#### `embedder.py`
**Primary Functions**:
- `generate_embedding()`: Single text embedding
- `generate_embeddings_batch()`: Batch processing
- `cache_embedding()`: In-memory caching with TTL

**Features**:
- OpenAI API integration
- Batch processing optimization
- Connection pooling
- Retry logic with exponential backoff
- Cache management

**Lines of Code**: ~400
**Key Dependencies**: openai, numpy

---

### `utils/` Package

Purpose: Shared utilities and helpers

#### `db_utils.py`
**Primary Functions**:
- `get_db_pool()`: Create async connection pool
- `check_db_health()`: Verify database status
- `execute_query()`: Safe query execution
- `close_pool()`: Graceful shutdown

**Configuration**:
```python
Pool Settings:
  - min_size: 2 connections
  - max_size: 10 connections
  - command_timeout: 60 seconds
```

**Lines of Code**: ~200
**Key Dependencies**: asyncpg

---

#### `models.py`
**Primary Classes**:
- `DocumentConfig`: Document processing configuration
- `ChunkMetadata`: Chunk metadata structure
- `SearchResult`: Search result representation
- `SessionStats`: CLI session statistics

**Purpose**: Type-safe data structures with Pydantic validation

**Lines of Code**: ~180
**Key Dependencies**: pydantic

---

#### `providers.py`
**Primary Functions**:
- `get_llm()`: OpenAI LLM instance
- `get_embedding_model()`: Embedding model configuration
- `get_openai_client()`: Shared OpenAI client

**Configuration**:
- Reads from environment variables
- Provides defaults for all models
- Singleton client pattern

**Lines of Code**: ~80
**Key Dependencies**: openai, python-dotenv

---

### `sql/` Directory

#### `schema.sql`
**Purpose**: Complete database schema definition

**Components**:
1. **Extensions**: Enable PGVector
2. **Tables**: documents, chunks
3. **Indexes**: Performance optimization
4. **Functions**: match_chunks() for vector search
5. **Triggers**: Updated timestamps

**Key Features**:
- UUID primary keys
- JSONB metadata fields
- Vector(1536) embeddings
- Cascade deletes for referential integrity

**Lines**: ~100

---

### `docling_basics/` Package

Purpose: Educational tutorials for Docling fundamentals

#### `README.md`
Progressive learning path for Docling library

---

#### `01_simple_pdf.py`
**Topic**: Basic PDF conversion to Markdown

**Concepts**:
- DocumentConverter initialization
- PDF file processing
- Markdown export

**Lines of Code**: ~50

---

#### `02_multiple_formats.py`
**Topic**: Multi-format document support

**Concepts**:
- Format detection
- Unified conversion pipeline
- PDF, Word, PowerPoint handling

**Lines of Code**: ~100

---

#### `03_audio_transcription.py`
**Topic**: Audio transcription with Whisper

**Concepts**:
- Whisper ASR integration
- Timestamp generation
- Markdown formatting for transcripts

**Lines of Code**: ~130

---

#### `04_hybrid_chunking.py`
**Topic**: Advanced chunking for RAG systems

**Concepts**:
- HybridChunker usage
- Semantic splitting
- Chunk size optimization
- Metadata tracking

**Lines of Code**: ~180

---

## Archive Structure

### `archives/` Directory

**Purpose**: Historical code and experimental implementations

#### `ottomator-agents/`
Previous agent implementations with different architectures

**Subdirectories**:
- `graphiti-agent/`: Graph-based agent experiments
- `streambuzz-agent/`: Streaming-focused agent prototype

**Status**: Not maintained, kept for reference

---

## Documentation Structure

### `claudedocs/` Directory

**Purpose**: Comprehensive project documentation

#### `architecture.md` (this was created)
- System architecture overview
- Component descriptions
- Data flow diagrams
- Technology stack
- Performance optimizations
- Architectural decisions (ADRs)

---

#### `api-reference.md` (this was created)
- Complete API documentation
- Function signatures
- Database schema reference
- Environment variables
- Error handling guide
- Best practices

---

#### `project-structure.md` (this file)
- Directory tree
- File descriptions
- Module breakdown
- Line counts
- Dependencies

---

#### `development-guide.md` (to be created)
- Setup instructions
- Development workflow
- Testing guidelines
- Contribution process
- Code style guide

---

## File Statistics

### Code Metrics

| Module | Files | Lines of Code | Purpose |
|--------|-------|---------------|---------|
| `ingestion/` | 5 | ~1,800 | Document processing |
| `utils/` | 3 | ~460 | Shared utilities |
| `cli.py` | 1 | ~400 | CLI interface |
| `rag_agent.py` | 1 | ~200 | RAG core |
| `docling_basics/` | 4 | ~460 | Tutorials |
| `sql/` | 1 | ~100 | Database schema |
| **Total** | 15 | ~3,420 | Core codebase |

---

### Documentation Metrics

| File | Lines | Purpose |
|------|-------|---------|
| `README.md` | ~350 | Main documentation |
| `architecture.md` | ~500 | System design |
| `api-reference.md` | ~650 | API documentation |
| `project-structure.md` | ~400 | This file |
| `docling_basics/README.md` | ~200 | Tutorial index |
| **Total** | ~2,100 | Documentation |

---

## Dependencies Tree

### Direct Dependencies

```
docling-rag-agent
├── Core Framework
│   ├── pydantic-ai (>=0.7.4)       # Agent framework
│   └── python-dotenv (>=1.0.0)     # Environment config
├── Database
│   └── asyncpg (>=0.30.0)          # Async PostgreSQL
├── AI/ML
│   ├── openai (>=1.0.0)            # LLM and embeddings
│   ├── numpy (>=2.0.2)             # Vector operations
│   └── openai-whisper (>=20250625) # Audio transcription
├── Document Processing
│   ├── docling (>=2.55.0)          # Multi-format processing
│   └── hf-xet (>=1.1.8)            # Hugging Face integration
├── HTTP/API
│   ├── aiohttp (>=3.9.0)           # Async HTTP
│   ├── httpx (>=0.25.0)            # Modern HTTP client
│   └── supabase (>=2.0.0)          # Supabase client
└── Development Tools
    ├── black (code formatting)
    ├── ruff (linting)
    ├── pytest (testing)
    └── mypy (type checking)
```

---

### Transitive Dependencies

Key indirect dependencies (automatically installed):

- `pydantic`: Data validation
- `tiktoken`: Token counting
- `torch`: ML backend for Whisper
- `transformers`: HuggingFace models
- `pillow`: Image processing
- `pandas`: Data manipulation

---

## Module Dependencies

### Import Graph

```
cli.py
├── rag_agent.py
│   ├── utils.providers
│   ├── utils.db_utils
│   └── utils.models
└── utils.db_utils

rag_agent.py
├── utils.providers
├── utils.db_utils
├── utils.models
└── ingestion.embedder

ingestion/ingest.py
├── ingestion.chunker
├── ingestion.embedder
├── utils.db_utils
└── utils.models

ingestion/chunker.py
└── (no internal dependencies)

ingestion/embedder.py
├── utils.providers
└── utils.models

utils/db_utils.py
└── (external only)

utils/providers.py
└── (external only)

utils/models.py
└── (external only)
```

---

## Build Artifacts

### Generated Files (Not in Git)

```
.venv/                    # Virtual environment
__pycache__/              # Python bytecode cache
*.pyc                     # Compiled Python files
.pytest_cache/            # Pytest cache
.mypy_cache/              # Mypy type check cache
.ruff_cache/              # Ruff linter cache
*.egg-info/               # Package build info
uv.lock                   # Dependency lock (committed)
.env                      # Environment variables (not committed)
.DS_Store                 # macOS metadata (not committed)
```

---

## Entry Point Summary

### Command Line Usage

| Command | Entry Point | Purpose |
|---------|-------------|---------|
| `uv run python cli.py` | `cli.py` | Enhanced CLI with colors |
| `uv run python rag_agent.py` | `rag_agent.py` | Basic CLI |
| `uv run python -m ingestion.ingest` | `ingestion/ingest.py` | Document ingestion |
| `uv run python docling_basics/01_simple_pdf.py` | Tutorial script | Learning example |

---

### Docker Usage

```bash
# Run CLI in container
docker-compose up rag-agent

# Run ingestion in container
docker-compose --profile ingestion up ingestion
```

---

## File Naming Conventions

### Python Files
- `snake_case.py` for all modules
- `__init__.py` for package initialization
- Test files: `test_*.py` or `*_test.py`

### Documentation
- `kebab-case.md` for markdown files
- `UPPERCASE.md` for root-level docs (README, LICENSE)

### Configuration
- `.lowercase` for dotfiles (.env, .gitignore)
- `lowercase.extension` for config (pyproject.toml, docker-compose.yml)

---

## Code Organization Principles

### 1. Separation of Concerns
- CLI logic separate from agent logic
- Database operations isolated in utils
- Document processing in dedicated package

### 2. Single Responsibility
- Each module has one primary purpose
- Functions do one thing well
- Classes encapsulate related functionality

### 3. Dependency Direction
- Core logic (agent) depends on utilities
- Utilities have no internal dependencies
- CLI depends on agent, not ingestion

### 4. Configuration Externalization
- All config in environment variables
- No hardcoded credentials or URLs
- Sensible defaults with overrides

---

## Future Structure Plans

### Potential Additions

#### `tests/` Directory
Unit and integration tests
```
tests/
├── unit/
│   ├── test_chunker.py
│   ├── test_embedder.py
│   └── test_db_utils.py
├── integration/
│   ├── test_ingestion.py
│   └── test_rag_agent.py
└── fixtures/
    └── sample_documents/
```

#### `scripts/` Directory
Utility scripts for common tasks
```
scripts/
├── setup_database.sh
├── backup_vectors.py
├── migrate_schema.py
└── benchmark_search.py
```

#### `api/` Directory
REST API for agent (future feature)
```
api/
├── main.py              # FastAPI application
├── routes.py            # API endpoints
└── middleware.py        # Auth, CORS, etc.
```

---

## Maintenance Notes

### What to Update When...

#### Adding New Dependencies
1. Update `pyproject.toml` dependencies section
2. Run `uv sync` to update lock file
3. Document in relevant `*.md` files

#### Adding New Modules
1. Create in appropriate package directory
2. Add `__init__.py` imports if needed
3. Update this file with module description
4. Update `api-reference.md` with new APIs

#### Changing Database Schema
1. Modify `sql/schema.sql`
2. Create migration script (future)
3. Update `api-reference.md` schema section
4. Update `architecture.md` if structure changes

#### Adding New Document Types
1. Extend handlers in `ingestion/ingest.py`
2. Update README.md supported formats section
3. Add tutorial in `docling_basics/` if complex
4. Document in `api-reference.md`

---

## Related Documentation

- [Architecture Overview](./architecture.md)
- [API Reference](./api-reference.md)
- [Development Guide](./development-guide.md) (coming soon)
- [Main README](../README.md)
- [Docling Tutorials](../docling_basics/README.md)
