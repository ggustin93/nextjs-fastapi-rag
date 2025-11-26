# Docling RAG Agent - System Architecture

## Overview

Docling RAG Agent is an intelligent text-based CLI system that provides conversational access to a knowledge base using Retrieval Augmented Generation (RAG). The system combines semantic search with large language models to deliver accurate, source-cited responses.

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        User Interfaces                        │
│  services/web/ (Next.js)    │    packages/core/cli.py         │
│  • React chat interface     │    • Terminal CLI interface     │
└────────────────────┬────────┴────────┬───────────────────────┘
                     │                 │
┌────────────────────▼─────────────────▼───────────────────────┐
│                      FastAPI Backend                          │
│                    services/api/app/main.py                   │
│   • SSE streaming  • Health checks  • CORS configuration      │
└──────┬───────────────────────────────────────────────────────┘
       │
┌──────▼───────────────────────────────────────────────────────┐
│                      RAG Agent Core                           │
│                 packages/core/agent.py (PydanticAI)           │
│   • Query processing  • Context management  • Tool orchestration │
└──────┬────────────────┬────────────────────┬─────────────────┘
       │                │                    │
┌──────▼──────┐  ┌─────▼─────┐  ┌──────────▼──────────┐
│ LLM Provider│  │ Embedding │  │  Supabase/PGVector   │
│  (OpenAI,   │  │  Provider │  │  • documents table   │
│ Chutes.ai,  │  │  (1536-d) │  │  • chunks table      │
│  Ollama)    │  │           │  │  • match_chunks()    │
└─────────────┘  └───────────┘  └─────────────────────┘
                                          ▲
┌─────────────────────────────────────────┘
│              Ingestion Pipeline
│      packages/ingestion/ (Docling-based)
│    • Document parsing  • Chunking  • Embedding
└─────────────────────────────────────────────────────
```

## Core Components

### 1. Web Interface (`services/web/`)

**Purpose**: Modern React chat interface

**Key Features**:
- 🎨 Next.js with App Router
- 💬 Real-time streaming chat
- 📱 Responsive design
- 🔗 SSE-based backend communication

**Technologies**:
- Next.js 14+ with TypeScript
- React hooks (useChat)
- TailwindCSS for styling

### 2. CLI Interface (`packages/core/cli.py`)

**Purpose**: Terminal-based user interface with rich features

**Key Features**:
- 🎨 Colored output for improved readability
- 📊 Session statistics tracking
- 🔄 Conversation history management
- ✅ Database health checks
- 💡 Built-in help system

**Technologies**:
- Async I/O for responsive interaction
- Token streaming for real-time responses
- Connection pooling for performance

### 3. FastAPI Backend (`services/api/`)

**Purpose**: REST API with SSE streaming for RAG queries

**Key Responsibilities**:
- HTTP endpoint management
- Server-Sent Events streaming
- CORS configuration for frontend
- Health monitoring

**Endpoints**:
- `POST /api/v1/chat/stream` - Streaming RAG responses
- `GET /api/v1/chat/health` - Service health check

### 4. RAG Agent Core (`packages/core/agent.py`)

**Purpose**: Orchestrates RAG pipeline and manages agent behavior

**Key Responsibilities**:
- Query understanding and context management
- Tool invocation (search_knowledge_base)
- Response generation with streaming
- Conversation history tracking

**Technologies**:
- **PydanticAI**: Agent framework with tool support
- **AsyncPG**: Async PostgreSQL driver with connection pooling
- **OpenAI API**: LLM and embeddings

**Agent Configuration**:
```python
agent = Agent(
    model=get_llm(),  # GPT-4 or configured model
    system_prompt="""Expert assistant with knowledge base access...""",
    deps_type=None
)
```

### 5. Knowledge Base Search Tool

**Function**: `search_knowledge_base(query: str, limit: int = 5) -> str`

**Process Flow**:
1. Generate query embedding using OpenAI (1536 dimensions)
2. Execute vector similarity search via `match_chunks()` function
3. Retrieve top-k most relevant chunks with similarity scores
4. Format results with source citations
5. Return structured context for LLM

**Vector Search**:
- **Algorithm**: Cosine similarity using PGVector
- **Threshold**: 0.7 (configurable)
- **Dimensions**: 1536 (text-embedding-3-small)
- **Index**: IVFFlat for efficient similarity search

### 6. Ingestion Pipeline (`packages/ingestion/`)

#### 4.1 Document Ingestion (`ingest.py`)

**Purpose**: Process and store documents in vector database

**Supported Formats** (via Docling):
- 📄 PDF (`.pdf`)
- 📝 Word (`.docx`, `.doc`)
- 📊 PowerPoint (`.pptx`, `.ppt`)
- 📈 Excel (`.xlsx`, `.xls`)
- 🌐 HTML (`.html`, `.htm`)
- 📋 Markdown (`.md`)
- 📃 Text (`.txt`)
- 🎵 Audio (`.mp3`) - Whisper transcription

**Process**:
1. **Clear existing data** (default behavior)
2. **Auto-detect file type** and route to appropriate processor
3. **Convert to Markdown** for consistent processing
4. **Chunk content** using hybrid strategy
5. **Generate embeddings** batch processing
6. **Store in database** with metadata

#### 4.2 Document Chunking (`chunker.py`)

**Purpose**: Intelligent text splitting for RAG

**Strategies**:
- **Hybrid Chunking**: Uses Docling's HybridChunker
- **Semantic Awareness**: Preserves document structure
- **Configurable Size**: Default 1000 characters
- **Overlap**: Maintains context between chunks

**Key Features**:
- Respects document boundaries (sections, paragraphs)
- Preserves tables and structured content
- Maintains markdown formatting
- Tracks chunk metadata (index, token count)

#### 4.3 Embedding Generation (`embedder.py`)

**Purpose**: Convert text to vector representations

**Features**:
- **Model**: text-embedding-3-small (OpenAI)
- **Dimensions**: 1536
- **Batch Processing**: Efficient bulk embedding
- **Caching**: Reduces redundant API calls
- **Error Handling**: Retry logic with exponential backoff

**Performance**:
- Connection pooling for API efficiency
- Batch size optimization
- Progress tracking for large datasets

### 5. Utilities (`utils/`)

#### 5.1 Database Utilities (`db_utils.py`)

**Purpose**: PostgreSQL connection management

**Features**:
- **Connection Pooling**: 2-10 connections (configurable)
- **Health Checks**: Database availability validation
- **Query Helpers**: Common database operations
- **Error Handling**: Graceful degradation

**Configuration**:
```python
db_pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=2,
    max_size=10,
    command_timeout=60
)
```

#### 5.2 Model Providers (`providers.py`)

**Purpose**: OpenAI client and model configuration

**Features**:
- Environment-based configuration
- Model selection (LLM and embeddings)
- API key management
- Client initialization

#### 5.3 Data Models (`models.py`)

**Purpose**: Pydantic models for type safety

**Models**:
- Document metadata structures
- Chunk representations
- Configuration schemas
- API request/response types

### 6. Centralized Configuration (`packages/config/`)

**Purpose**: Type-safe configuration management with environment variable support

**Features**:
- **Frozen Dataclasses**: Immutable configuration objects
- **Multi-Provider Support**: OpenAI, Chutes.ai, Ollama, and any OpenAI-compatible API
- **Singleton Pattern**: `@lru_cache` ensures consistent settings
- **Domain-Specific Configs**: `LLMConfig`, `EmbeddingConfig`, `DatabaseConfig`, `ChunkingConfig`, `SearchConfig`, `APIConfig`

**Usage**:
```python
from packages.config import settings

# Create model with provider support
agent = Agent(settings.llm.create_model())

# Access domain configs
batch_size = settings.embedding.batch_size
pool_size = settings.database.pool_max_size
```

**Environment Variables** (see `.env.example`):
- `LLM_BASE_URL`: Custom API endpoint for alternative providers
- `LLM_MODEL`: Model name (default: `gpt-4o-mini`)
- `EMBEDDING_BATCH_SIZE`: Batch size for embeddings (default: `100`)
- `DB_POOL_MAX_SIZE`: Database connection pool size (default: `5`)
- `CHUNK_SIZE`: Target chunk size in characters (default: `1000`)

### 7. Database Schema (`sql/schema.sql`)

#### Tables

**`documents`**
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**`chunks`**
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    chunk_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    token_count INTEGER
);
```

#### Functions

**`match_chunks()`**: Vector similarity search
```sql
CREATE FUNCTION match_chunks(
    query_embedding VECTOR(1536),
    match_count INT,
    similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    embedding VECTOR(1536),
    similarity FLOAT,
    document_title TEXT,
    document_source TEXT
)
```

**Algorithm**: `1 - (embedding <=> query_embedding)` (cosine similarity)

## Audio Transcription Feature

### Whisper ASR Integration

**Model**: `openai/whisper-large-v3-turbo`

**Process Flow**:
1. Audio file detected during ingestion (`.mp3`)
2. Docling routes to Whisper ASR processor
3. Transcription with timestamps generated
4. Formatted as markdown with time markers
5. Stored and indexed like text documents

**Output Format**:
```markdown
[time: 0.0-4.0] Welcome to our podcast on AI and machine learning.
[time: 5.28-9.96] Today we'll discuss retrieval augmented generation systems.
```

**Capabilities**:
- 90+ language support
- Speaker diarization (optional)
- Timestamp precision to 0.01s
- Background noise handling

## Data Flow

### Query Processing Flow

```
User Input
    ↓
Web UI (services/web/) or CLI (packages/core/cli.py)
    ↓
FastAPI Backend (services/api/)
    ↓
RAG Agent (packages/core/agent.py)
    ↓
[Decision: Use search_knowledge_base tool?]
    ↓ Yes
Generate Query Embedding (OpenAI)
    ↓
Vector Search (PostgreSQL match_chunks)
    ↓
Retrieve Top-K Chunks
    ↓
Format Context with Sources
    ↓
LLM Generation (OpenAI GPT-4)
    ↓
Stream Response to User
    ↓
Update Conversation History
```

### Ingestion Flow

```
Documents Directory
    ↓
ingest.py (Entry Point)
    ↓
[For each file]
    ↓
File Type Detection
    ↓
Docling Processing
    ↓
Markdown Conversion
    ↓
Hybrid Chunking (chunker.py)
    ↓
Batch Embedding (embedder.py)
    ↓
Database Storage (PostgreSQL)
    ↓
Index Creation (PGVector)
```

## Performance Optimizations

### 1. Connection Pooling
- **Database**: 2-10 async connections
- **OpenAI**: Shared client with connection reuse
- **Benefits**: Reduced latency, better throughput

### 2. Embedding Cache
- **Strategy**: In-memory cache for frequent queries
- **TTL**: Configurable expiration
- **Benefits**: Reduced API costs, faster responses

### 3. Batch Processing
- **Embeddings**: Process multiple chunks simultaneously
- **Database**: Bulk insert operations
- **Benefits**: Higher throughput during ingestion

### 4. Streaming Responses
- **Protocol**: Token-by-token streaming from OpenAI
- **UX**: Immediate feedback to users
- **Benefits**: Perceived performance improvement

### 5. Vector Index
- **Type**: IVFFlat (Inverted File with Flat Quantization)
- **Purpose**: Accelerate similarity search
- **Trade-off**: Slight accuracy loss for speed gain

## Technology Stack

### Core Technologies
- **Python**: 3.9+ (async/await, type hints)
- **PydanticAI**: Agent framework with tool support
- **Docling**: Multi-format document processing
- **OpenAI**: LLMs (GPT-4) and embeddings
- **PostgreSQL**: Relational database
- **PGVector**: Vector similarity extension
- **AsyncPG**: Async PostgreSQL driver

### Key Libraries
- `python-dotenv`: Environment configuration
- `aiohttp`: Async HTTP client
- `numpy`: Vector operations
- `openai-whisper`: Audio transcription
- `supabase`: Optional cloud database

## Deployment Options

### 1. Local Development
- Local PostgreSQL with PGVector
- Python virtual environment (uv/venv)
- `.env` configuration

### 2. Docker Deployment
- `docker-compose.yml` provided
- Multi-container setup (app + db)
- Volume mounting for persistence

### 3. Cloud Deployment
- **Database**: Supabase, Neon, or managed PostgreSQL
- **Application**: Cloud Run, ECS, or VPS
- **Configuration**: Environment variables

## Security Considerations

### 1. API Key Management
- Environment variables only (`.env`)
- Never commit credentials
- Rotate keys regularly

### 2. Database Security
- Connection string encryption
- Role-based access control
- SSL/TLS connections

### 3. Input Validation
- Pydantic schema validation
- SQL injection prevention (parameterized queries)
- File type validation during ingestion

## Monitoring and Observability

### Current Capabilities
- Session statistics (`stats` command)
- Database health checks
- Error logging to console

### Future Enhancements
- Structured logging
- Metrics collection (Prometheus)
- Distributed tracing
- Performance dashboards

## Scalability Considerations

### Current Limits
- Connection pool: 10 concurrent connections
- Single-node database
- Synchronous ingestion pipeline

### Scaling Strategies
- **Horizontal**: Load balancer + multiple app instances
- **Database**: Read replicas, connection pooling
- **Vector Search**: Specialized vector databases (Pinecone, Weaviate)
- **Ingestion**: Distributed task queue (Celery, Redis)

## Extension Points

### 1. Custom Document Processors
- Add new file type handlers in `packages/ingestion/`
- Integrate additional Docling features
- Support proprietary formats

### 2. Alternative LLMs
The application supports multiple LLM providers via `packages/config/`:
- **OpenAI**: Default configuration
- **Chutes.ai**: Bittensor decentralized AI via `LLM_BASE_URL`
- **Ollama**: Local models via `LLM_BASE_URL=http://localhost:11434/v1`
- **Any OpenAI-compatible API**: Configure via `LLM_BASE_URL` and `LLM_API_KEY`

Configure via environment variables (see `.env.example`)

### 3. Enhanced Search
- Hybrid search (keyword + vector)
- Reranking strategies
- Multi-query expansion

### 4. Multi-Modal Support
- Image embeddings (CLIP)
- Video transcription
- Table understanding

## Architectural Decisions

### ADR-001: PydanticAI for Agent Framework
**Context**: Need structured agent with tool support
**Decision**: Use PydanticAI over LangChain
**Rationale**: Type safety, simpler API, better async support

### ADR-002: PostgreSQL + PGVector for Storage
**Context**: Need vector database with ACID guarantees
**Decision**: PostgreSQL + PGVector over specialized vector DBs
**Rationale**: Simpler deployment, familiar tooling, strong consistency

### ADR-003: Docling for Document Processing
**Context**: Need multi-format document support
**Decision**: Use Docling over custom parsers
**Rationale**: Comprehensive format support, maintained by IBM, includes audio

### ADR-004: Hybrid Chunking Strategy
**Context**: Need optimal chunk sizes for RAG
**Decision**: Docling HybridChunker with configurable size
**Rationale**: Preserves structure, semantic awareness, flexibility

### ADR-005: Streaming Responses
**Context**: Improve user experience during LLM generation
**Decision**: Token-by-token streaming from OpenAI
**Rationale**: Immediate feedback, perceived performance improvement
