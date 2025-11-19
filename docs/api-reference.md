# API Reference - Docling RAG Agent

## Table of Contents
- [Agent API](#agent-api)
- [Database Functions](#database-functions)
- [Ingestion Pipeline](#ingestion-pipeline)
- [Utilities](#utilities)
- [Data Models](#data-models)

---

## Agent API

### RAG Agent Core

#### `Agent` (PydanticAI)

Main agent instance for conversational RAG.

**Configuration**:
```python
agent = Agent(
    model=get_llm(),          # OpenAI model instance
    system_prompt=str,        # System behavior instructions
    deps_type=None            # No external dependencies
)
```

**Methods**:

##### `run_stream(user_input: str, message_history: list) -> RunStream`

Stream agent responses with conversation context.

**Parameters**:
- `user_input` (str): User query or message
- `message_history` (list): Previous conversation turns

**Returns**: `RunStream` object for async iteration

**Example**:
```python
async with agent.run_stream(user_input, message_history=history) as result:
    async for text in result.stream_text(delta=False):
        print(text, end="", flush=True)
```

---

### Tools

#### `search_knowledge_base`

Semantic search tool registered with the agent.

**Signature**:
```python
async def search_knowledge_base(
    ctx: RunContext[None],
    query: str,
    limit: int = 5
) -> str
```

**Parameters**:
- `ctx` (RunContext): PydanticAI runtime context
- `query` (str): Search query for semantic matching
- `limit` (int, optional): Maximum results to return (default: 5)

**Returns**: Formatted string with search results and sources

**Response Format**:
```
Found [N] relevant chunks:

1. [Chunk content excerpt...]
   Source: document_title.pdf
   Similarity: 0.85

2. [Chunk content excerpt...]
   Source: document_title.docx
   Similarity: 0.82
```

**Process**:
1. Generate query embedding using OpenAI
2. Execute vector similarity search via `match_chunks()`
3. Format results with source citations
4. Return context for LLM consumption

**Example Usage**:
```python
# Tool is automatically invoked by agent when needed
# Manual invocation for testing:
results = await search_knowledge_base(ctx, "What is RAG?", limit=3)
```

---

## Database Functions

### Vector Search

#### `match_chunks`

PostgreSQL function for vector similarity search using PGVector.

**Signature**:
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

**Parameters**:
- `query_embedding` (VECTOR(1536)): Query vector for similarity comparison
- `match_count` (INT): Maximum number of results
- `similarity_threshold` (FLOAT, optional): Minimum similarity score (default: 0.7)

**Returns**: Table with columns:
- `id`: Chunk UUID
- `content`: Text content of chunk
- `embedding`: Vector representation
- `similarity`: Cosine similarity score (0-1)
- `document_title`: Source document title
- `document_source`: Source document path

**Algorithm**: Cosine similarity using `<=>` operator
```sql
1 - (embedding <=> query_embedding) AS similarity
```

**Example Usage**:
```sql
-- Search for chunks similar to a query embedding
SELECT * FROM match_chunks(
    '[0.123, 0.456, ...]'::VECTOR(1536),
    5,
    0.75
);
```

**Python Usage**:
```python
results = await conn.fetch(
    "SELECT * FROM match_chunks($1::vector(1536), $2, $3)",
    query_embedding,
    limit,
    0.7
)
```

---

### Database Tables

#### `documents` Table

Stores original document metadata and content.

**Schema**:
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

**Columns**:
- `id`: Unique document identifier (UUID)
- `title`: Document title/name
- `source`: File path or source identifier
- `content`: Full document text (markdown)
- `metadata`: Additional document properties (JSON)
- `created_at`: Document creation timestamp
- `updated_at`: Last modification timestamp

**Indexes**:
```sql
CREATE INDEX idx_documents_source ON documents(source);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
```

#### `chunks` Table

Stores document chunks with vector embeddings.

**Schema**:
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

**Columns**:
- `id`: Unique chunk identifier (UUID)
- `document_id`: Reference to parent document
- `content`: Chunk text content
- `embedding`: 1536-dimensional vector
- `chunk_index`: Position in original document
- `metadata`: Additional chunk properties (JSON)
- `token_count`: Approximate token count for chunk

**Indexes**:
```sql
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops);
```

---

## Ingestion Pipeline

### Document Ingestion

#### `ingest_documents`

Main ingestion function for processing and storing documents.

**Location**: `ingestion/ingest.py`

**Signature**:
```python
async def ingest_documents(
    documents_dir: Path,
    chunk_size: int = 1000,
    clear_existing: bool = True
) -> dict
```

**Parameters**:
- `documents_dir` (Path): Directory containing documents to ingest
- `chunk_size` (int, optional): Maximum chunk size in characters (default: 1000)
- `clear_existing` (bool, optional): Clear database before ingestion (default: True)

**Returns**: Dictionary with ingestion statistics
```python
{
    "documents_processed": int,
    "chunks_created": int,
    "errors": list[str]
}
```

**Process**:
1. Clear existing documents and chunks (if `clear_existing=True`)
2. Scan directory for supported file types
3. Process each document with appropriate handler
4. Chunk content using HybridChunker
5. Generate embeddings in batches
6. Store documents and chunks in database

**Example**:
```python
from ingestion.ingest import ingest_documents
from pathlib import Path

stats = await ingest_documents(
    documents_dir=Path("./documents"),
    chunk_size=800,
    clear_existing=True
)
print(f"Processed {stats['documents_processed']} documents")
print(f"Created {stats['chunks_created']} chunks")
```

**Supported File Types**:
- PDF: `.pdf`
- Word: `.docx`, `.doc`
- PowerPoint: `.pptx`, `.ppt`
- Excel: `.xlsx`, `.xls`
- HTML: `.html`, `.htm`
- Markdown: `.md`, `.markdown`
- Text: `.txt`
- Audio: `.mp3`

---

### Document Chunking

#### `HybridChunker`

Docling-based chunking for semantic text splitting.

**Location**: `ingestion/chunker.py`

**Signature**:
```python
def chunk_document(
    markdown_content: str,
    chunk_size: int = 1000,
    doc_meta: dict = None
) -> list[dict]
```

**Parameters**:
- `markdown_content` (str): Document content in markdown format
- `chunk_size` (int, optional): Target chunk size in characters (default: 1000)
- `doc_meta` (dict, optional): Document metadata to include in chunks

**Returns**: List of chunk dictionaries
```python
[
    {
        "content": str,       # Chunk text
        "chunk_index": int,   # Position in document
        "token_count": int,   # Approximate tokens
        "metadata": dict      # Additional properties
    },
    ...
]
```

**Chunking Strategy**:
- Respects document structure (sections, paragraphs)
- Preserves markdown formatting
- Maintains semantic coherence
- Configurable overlap for context preservation

**Example**:
```python
from ingestion.chunker import chunk_document

chunks = chunk_document(
    markdown_content=doc_text,
    chunk_size=800,
    doc_meta={"source": "example.pdf"}
)
```

---

### Embedding Generation

#### `EmbeddingGenerator`

OpenAI-based embedding generation with caching.

**Location**: `ingestion/embedder.py`

**Class**:
```python
class EmbeddingGenerator:
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        cache_ttl: int = 3600
    )
```

**Parameters**:
- `model` (str): OpenAI embedding model name
- `cache_ttl` (int): Cache expiration time in seconds

**Methods**:

##### `generate_embedding(text: str) -> list[float]`

Generate single embedding vector.

**Parameters**:
- `text` (str): Text to embed

**Returns**: 1536-dimensional vector as list of floats

**Example**:
```python
embedder = EmbeddingGenerator()
embedding = await embedder.generate_embedding("Hello, world!")
```

##### `generate_embeddings_batch(texts: list[str]) -> list[list[float]]`

Generate embeddings for multiple texts efficiently.

**Parameters**:
- `texts` (list[str]): List of texts to embed

**Returns**: List of 1536-dimensional vectors

**Example**:
```python
embedder = EmbeddingGenerator()
chunks = ["chunk 1", "chunk 2", "chunk 3"]
embeddings = await embedder.generate_embeddings_batch(chunks)
```

**Features**:
- Batch processing for efficiency
- In-memory caching with TTL
- Automatic retry with exponential backoff
- Progress tracking for large batches

---

## Utilities

### Database Utilities

#### `get_db_pool`

Create async PostgreSQL connection pool.

**Location**: `utils/db_utils.py`

**Signature**:
```python
async def get_db_pool(
    database_url: str,
    min_size: int = 2,
    max_size: int = 10
) -> asyncpg.Pool
```

**Parameters**:
- `database_url` (str): PostgreSQL connection string
- `min_size` (int, optional): Minimum pool connections (default: 2)
- `max_size` (int, optional): Maximum pool connections (default: 10)

**Returns**: AsyncPG connection pool

**Example**:
```python
from utils.db_utils import get_db_pool

pool = await get_db_pool(DATABASE_URL, min_size=2, max_size=10)
async with pool.acquire() as conn:
    result = await conn.fetch("SELECT * FROM documents")
```

#### `check_db_health`

Verify database connectivity and configuration.

**Signature**:
```python
async def check_db_health(pool: asyncpg.Pool) -> dict
```

**Parameters**:
- `pool` (asyncpg.Pool): Database connection pool

**Returns**: Health status dictionary
```python
{
    "status": "healthy" | "unhealthy",
    "document_count": int,
    "chunk_count": int,
    "pgvector_enabled": bool
}
```

**Example**:
```python
from utils.db_utils import check_db_health

health = await check_db_health(pool)
if health["status"] == "healthy":
    print(f"Knowledge base ready: {health['chunk_count']} chunks")
```

---

### Model Providers

#### `get_llm`

Get configured OpenAI LLM instance.

**Location**: `utils/providers.py`

**Signature**:
```python
def get_llm(model: str = None) -> OpenAIModel
```

**Parameters**:
- `model` (str, optional): Model name override (default: from env `LLM_CHOICE`)

**Returns**: Configured OpenAI model instance

**Example**:
```python
from utils.providers import get_llm

llm = get_llm()  # Uses LLM_CHOICE from .env
# or
llm = get_llm("gpt-4-turbo")  # Override model
```

#### `get_embedding_model`

Get configured OpenAI embedding model.

**Signature**:
```python
def get_embedding_model(model: str = None) -> str
```

**Parameters**:
- `model` (str, optional): Model name override (default: from env `EMBEDDING_MODEL`)

**Returns**: Embedding model name string

**Example**:
```python
from utils.providers import get_embedding_model

model = get_embedding_model()  # "text-embedding-3-small"
```

---

## Data Models

### Pydantic Models

#### `DocumentConfig`

Configuration for document processing.

**Location**: `utils/models.py`

**Schema**:
```python
class DocumentConfig(BaseModel):
    chunk_size: int = 1000
    overlap: int = 100
    embedding_model: str = "text-embedding-3-small"
    batch_size: int = 50
```

#### `ChunkMetadata`

Metadata for document chunks.

**Schema**:
```python
class ChunkMetadata(BaseModel):
    document_id: str
    chunk_index: int
    token_count: int
    source: str
    created_at: datetime
```

#### `SearchResult`

Structure for search results.

**Schema**:
```python
class SearchResult(BaseModel):
    content: str
    similarity: float
    document_title: str
    document_source: str
    chunk_id: str
```

---

## CLI Commands

### Interactive Commands

Available during CLI session:

#### `help`
Display help information and available commands.

**Usage**: `help`

#### `clear`
Clear conversation history and start fresh session.

**Usage**: `clear`

#### `stats`
Display session statistics (queries, tokens, documents).

**Usage**: `stats`

**Output**:
```
Session Statistics:
- Queries processed: 15
- Tokens generated: 2,450
- Documents searched: 20
- Chunks retrieved: 75
```

#### `exit` / `quit`
Exit the CLI application.

**Usage**: `exit` or `quit` or `Ctrl+C`

---

## Environment Variables

### Required Variables

#### `DATABASE_URL`
PostgreSQL connection string with PGVector extension.

**Format**: `postgresql://user:password@host:port/database`

**Examples**:
- Local: `postgresql://postgres:password@localhost:5432/rag_db`
- Supabase: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`
- Neon: `postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]`

#### `OPENAI_API_KEY`
OpenAI API key for embeddings and LLM.

**Format**: `sk-...`

**Get from**: https://platform.openai.com/api-keys

### Optional Variables

#### `LLM_CHOICE`
OpenAI model for text generation.

**Default**: `gpt-4o-mini`

**Options**: `gpt-4o-mini`, `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`

#### `EMBEDDING_MODEL`
OpenAI model for embeddings.

**Default**: `text-embedding-3-small`

**Options**: `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`

---

## Error Handling

### Common Errors

#### `ConnectionError`
Database connection failed.

**Solution**: Verify `DATABASE_URL` and network connectivity

#### `EmbeddingError`
OpenAI API request failed.

**Solution**: Check `OPENAI_API_KEY` and API quota

#### `ChunkingError`
Document processing failed.

**Solution**: Verify document format and file integrity

#### `VectorSearchError`
Similarity search failed.

**Solution**: Ensure PGVector extension is enabled and indexes exist

---

## Rate Limits

### OpenAI API

**Embeddings**:
- Tier 1: 3,000 requests/minute
- Tier 2: 3,500 requests/minute

**LLM**:
- GPT-4: 500 requests/minute (Tier 1)
- GPT-3.5: 3,500 requests/minute (Tier 1)

**Mitigation**:
- Batch processing for embeddings
- Connection pooling for API requests
- Retry logic with exponential backoff

---

## Best Practices

### 1. Chunk Size Selection
- **Small documents** (< 5 pages): 500-800 characters
- **Medium documents** (5-50 pages): 800-1200 characters
- **Large documents** (> 50 pages): 1000-1500 characters

### 2. Embedding Batch Size
- **Fast network**: 100-200 texts per batch
- **Standard network**: 50-100 texts per batch
- **Rate limited**: 20-50 texts per batch

### 3. Database Connections
- **Development**: 2-5 connections
- **Production**: 10-20 connections
- **High load**: 20-50 connections

### 4. Vector Search Tuning
- **Similarity threshold**: 0.7 (default), 0.6 (relaxed), 0.8 (strict)
- **Result limit**: 3-5 (focused), 5-10 (comprehensive), 10+ (exhaustive)

---

## Version Compatibility

### Python
- **Minimum**: 3.9
- **Recommended**: 3.10+
- **Tested**: 3.9, 3.10, 3.11

### PostgreSQL
- **Minimum**: 14.0
- **PGVector**: 0.5.0+
- **Recommended**: 15.0+ with PGVector 0.6.0+

### OpenAI API
- **SDK**: 1.0.0+
- **API Version**: Latest (auto-updated)
