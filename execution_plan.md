# RAG Agent Implementation Execution Plan

## Executive Summary

**Project**: Production-Ready RAG Agent Refactoring
**Target File**: `packages/core/agent.py`
**Total Effort**: 22-30 hours (3-4 days)
**Priority**: Critical - Addresses thread safety, information loss, and production readiness

**Key Objectives**:
1. Fix critical RAG retrieval quality issues (French query failures)
2. Eliminate thread-unsafe global state for production deployment
3. Add comprehensive error handling and input validation
4. Implement observability for monitoring and debugging

---

## Phase 1: Critical Fixes (4-6 hours) 🚨

**Goal**: Resolve immediate production blockers and RAG quality issues

### Task 1.1: Disable Query Reformulation (30 min)
**Priority**: CRITICAL
**File**: `packages/core/agent.py:51-81`

**Problem**: Query reformulation destroys semantic relationships in French queries by removing critical prepositions ("de", "à", "pour").

**Implementation**:
```python
def reformulate_query(query: str) -> str:
    """
    Minimal reformulation - only strip punctuation.
    Preserves all semantic content for embedding matching.
    """
    return query.strip().rstrip("?!.")
```

**Testing**:
- Test query: "Quels sont tous les critères de classification pour Type D?"
- Expected: Query preserved with semantic relationships intact
- Verify: Search retrieves Type D criteria successfully

**Success Criteria**:
- French queries maintain semantic relationships
- No loss of prepositions or contextual markers
- Improved retrieval quality for regulatory queries

---

### Task 1.2: Implement Multi-Chunk Retrieval (1 hour)
**Priority**: CRITICAL
**File**: `packages/core/agent.py:179-186`

**Problem**: Current deduplication keeps only 1 chunk per document, losing regulatory exceptions and special cases.

**Implementation**:
```python
# Configuration constant
MAX_CHUNKS_PER_DOCUMENT = 3  # Can be moved to settings later

# Updated deduplication logic
seen_documents: dict[str, list] = {}
deduped_results = []

for row in sorted_results:
    doc_source = row["document_source"]

    if doc_source not in seen_documents:
        seen_documents[doc_source] = []

    # Keep top N chunks per document
    if len(seen_documents[doc_source]) < MAX_CHUNKS_PER_DOCUMENT:
        seen_documents[doc_source].append(row)
        deduped_results.append(row)

logger.info(
    f"Deduplication: {len(sorted_results)} → {len(deduped_results)} chunks "
    f"from {len(seen_documents)} documents (max {MAX_CHUNKS_PER_DOCUMENT} per doc)"
)
```

**Testing**:
- Query documents with multiple relevant chunks
- Verify 3 chunks retrieved per document (not just 1)
- Confirm comprehensive coverage of regulatory exceptions

**Success Criteria**:
- Multi-faceted information preserved
- Regulatory exceptions included in retrieval
- User gets comprehensive answers with all relevant details

---

### Task 1.3: Replace Global State with RAGService (2-3 hours)
**Priority**: CRITICAL
**Files**:
- `packages/core/agent.py:24-28` (remove globals)
- `packages/core/agent.py:109-156` (update search_knowledge_base)
- `packages/core/agent.py:158-208` (update get_last_search_sources)

**Problem**: Module-level globals (`rest_client`, `last_search_sources`) are thread-unsafe for concurrent FastAPI requests.

**Implementation**:

**Step 1: Create RAGService class and context variable**
```python
from contextvars import ContextVar
from typing import Optional
from dataclasses import dataclass, field

@dataclass
class RAGService:
    """RAG service with request-scoped state isolation."""
    supabase_client: AsyncClient
    search_sources: list[dict] = field(default_factory=list)

    def clear_sources(self) -> None:
        """Clear search sources for new request."""
        self.search_sources.clear()

    def add_sources(self, sources: list[dict]) -> None:
        """Add sources from search results."""
        self.search_sources.extend(sources)

    def get_sources(self) -> list[dict]:
        """Get accumulated search sources."""
        return self.search_sources

# Request-scoped service instance
_rag_service: ContextVar[Optional[RAGService]] = ContextVar('rag_service', default=None)

def get_rag_service() -> RAGService:
    """Get current request's RAG service."""
    service = _rag_service.get()
    if service is None:
        raise RuntimeError("RAG service not initialized for this request")
    return service

def set_rag_service(service: RAGService) -> None:
    """Set RAG service for current request."""
    _rag_service.set(service)
```

**Step 2: Update search_knowledge_base tool**
```python
@agent.tool
async def search_knowledge_base(ctx: RunContext[None], query: str, limit: int | None = None) -> str:
    """Search knowledge base using request-scoped service."""
    if limit is None:
        limit = settings.search.default_limit

    similarity_threshold = settings.search.similarity_threshold

    # Get request-scoped service
    service = get_rag_service()

    # Reformulate query (now minimal reformulation)
    reformulated_query = reformulate_query(query)

    logger.info(f"Searching knowledge base with query: {reformulated_query}")

    # Generate embedding
    embedding = await get_embedding(reformulated_query)

    # Search using service's client
    response = await service.supabase_client.rpc(
        "match_chunks",
        {
            "query_embedding": embedding,
            "similarity_threshold": similarity_threshold,
            "match_count": limit,
        },
    )

    results = response.data if response.data else []

    if not results:
        logger.warning(f"No results found for query: {query}")
        return "No relevant information found in the knowledge base."

    # Sort and deduplicate (multi-chunk)
    sorted_results = sorted(results, key=lambda x: x["similarity"], reverse=True)

    # Multi-chunk deduplication
    seen_documents: dict[str, list] = {}
    deduped_results = []
    MAX_CHUNKS_PER_DOCUMENT = 3

    for row in sorted_results:
        doc_source = row["document_source"]

        if doc_source not in seen_documents:
            seen_documents[doc_source] = []

        if len(seen_documents[doc_source]) < MAX_CHUNKS_PER_DOCUMENT:
            seen_documents[doc_source].append(row)
            deduped_results.append(row)

    logger.info(
        f"Deduplication: {len(sorted_results)} → {len(deduped_results)} chunks "
        f"from {len(seen_documents)} documents (max {MAX_CHUNKS_PER_DOCUMENT} per doc)"
    )

    # Format results
    formatted_results = []
    for i, row in enumerate(deduped_results, 1):
        formatted_results.append(
            f"{i}. {row['document_source']} (similarity: {row['similarity']:.2f})\n"
            f"{row['content']}"
        )

    # Store sources in request-scoped service
    service.add_sources([
        {
            'path': row['document_source'],
            'content': row['content_preview'],
            'similarity': row['similarity']
        }
        for row in deduped_results
    ])

    return "\n\n".join(formatted_results)
```

**Step 3: Update get_last_search_sources tool**
```python
@agent.tool
async def get_last_search_sources(ctx: RunContext[None]) -> str:
    """Get sources from last search using request-scoped service."""
    service = get_rag_service()
    sources = service.get_sources()

    if not sources:
        return "No search has been performed yet."

    result = ["Sources from last search:"]
    for i, source in enumerate(sources, 1):
        result.append(
            f"{i}. {source['path']} (similarity: {source['similarity']:.2f})"
        )

    return "\n".join(result)
```

**Step 4: Update FastAPI endpoint** (`services/api/app/api/chat.py`)
```python
@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with request-scoped RAG service."""
    from packages.core.agent import agent, set_rag_service, RAGService
    from packages.utils.supabase_client import get_supabase_client

    # Create request-scoped service
    supabase = get_supabase_client()
    rag_service = RAGService(supabase_client=supabase)
    set_rag_service(rag_service)

    try:
        async def generate():
            try:
                # Stream agent response
                async with agent.run_stream(request.message) as result:
                    async for message in result.stream():
                        # ... existing streaming logic
                        pass

                # Send sources from request-scoped service
                sources = rag_service.get_sources()
                if sources:
                    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

                yield "event: done\ndata: {}\n\n"

            except Exception as e:
                logger.error(f"Chat error: {e}", exc_info=True)
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    finally:
        # Cleanup is automatic with contextvars
        rag_service.clear_sources()
```

**Testing**:
- Run concurrent requests to verify no state collision
- Verify each request gets its own isolated sources
- Load test with 10+ concurrent users

**Success Criteria**:
- Thread-safe for concurrent requests
- No cross-request state pollution
- Production-ready for FastAPI deployment

---

### Task 1.4: Add Basic Error Boundaries (1 hour)
**Priority**: CRITICAL
**File**: `packages/core/agent.py:109-156`

**Problem**: No error handling or graceful degradation.

**Implementation**:
```python
from pydantic_ai import ModelRetry

@agent.tool
async def search_knowledge_base(ctx: RunContext[None], query: str, limit: int | None = None) -> str:
    """Search with basic error handling."""
    try:
        if limit is None:
            limit = settings.search.default_limit

        # Basic input validation
        if not query or not query.strip():
            logger.warning("Empty query received")
            return "Please provide a valid search query."

        query = query.strip()
        if len(query) > 1000:
            logger.warning(f"Query too long: {len(query)} chars")
            return "Query is too long. Please shorten your question."

        similarity_threshold = settings.search.similarity_threshold

        # Get request-scoped service
        service = get_rag_service()

        # Reformulate query
        reformulated_query = reformulate_query(query)

        logger.info(f"Searching knowledge base with query: {reformulated_query}")

        # Generate embedding with error handling
        try:
            embedding = await get_embedding(reformulated_query)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}", exc_info=True)
            raise ModelRetry("Failed to process query. Please try again.")

        # Search with error handling
        try:
            response = await service.supabase_client.rpc(
                "match_chunks",
                {
                    "query_embedding": embedding,
                    "similarity_threshold": similarity_threshold,
                    "match_count": limit,
                },
            )
        except Exception as e:
            logger.error(f"Database search failed: {e}", exc_info=True)
            return "Search temporarily unavailable. Please try again in a moment."

        results = response.data if response.data else []

        if not results:
            logger.warning(f"No results found for query: {query}")
            return "No relevant information found in the knowledge base. Try rephrasing your question."

        # ... rest of processing with multi-chunk deduplication

    except ModelRetry:
        raise  # Let PydanticAI handle retries
    except Exception as e:
        logger.error(f"Unexpected error in search: {e}", exc_info=True)
        return "An error occurred during search. Please try again."
```

**Testing**:
- Test with empty queries
- Test with extremely long queries (>1000 chars)
- Simulate database connection failures
- Verify graceful error messages returned

**Success Criteria**:
- No crashes on invalid input
- Graceful error messages for users
- Proper logging of errors for debugging

---

## Phase 2: High Priority (8-10 hours) ⚠️

**Goal**: Add production-grade validation, retry logic, and type safety

### Task 2.1: Add Input Validation with Pydantic (2 hours)
**Priority**: HIGH
**File**: `packages/core/agent.py` (new models section)

**Implementation**:
```python
from pydantic import BaseModel, Field, validator
from typing import Literal

class SearchRequest(BaseModel):
    """Validated search request."""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)

    @validator('query')
    def validate_query(cls, v):
        # Sanitize input
        sanitized = v.strip()
        if not sanitized:
            raise ValueError("Query cannot be empty")

        # Check for potentially malicious patterns
        if any(char in sanitized for char in ['<', '>', ';', '|', '`']):
            raise ValueError("Query contains invalid characters")

        return sanitized

    @validator('limit')
    def validate_limit(cls, v):
        if v > 100:
            logger.warning(f"Limit {v} exceeds maximum, capping at 100")
            return 100
        return v

# Update search_knowledge_base to use validation
@agent.tool
async def search_knowledge_base(ctx: RunContext[None], query: str, limit: int | None = None) -> str:
    """Search with validated input."""
    try:
        # Validate input
        search_req = SearchRequest(query=query, limit=limit or 10)
    except ValidationError as e:
        logger.warning(f"Invalid search request: {e}")
        return f"Invalid search parameters: {str(e)}"

    # Use validated values
    query = search_req.query
    limit = search_req.limit

    # ... rest of search logic
```

**Testing**:
- Test with malicious input (SQL injection attempts, XSS patterns)
- Test with boundary values (empty, max length, negative limits)
- Verify proper error messages for validation failures

**Success Criteria**:
- All input validated before processing
- Malicious input rejected with clear messages
- No crashes from invalid input

---

### Task 2.2: Implement Retry Logic (2 hours)
**Priority**: HIGH
**File**: `packages/core/agent.py`

**Implementation**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from postgrest.exceptions import APIError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry_if=retry_if_exception_type((APIError, TimeoutError)),
    reraise=True
)
async def _search_with_retry(
    service: RAGService,
    query_embedding: list[float],
    similarity_threshold: float,
    match_count: int
) -> list[dict]:
    """Execute search with exponential backoff retry."""
    response = await service.supabase_client.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "similarity_threshold": similarity_threshold,
            "match_count": match_count,
        },
    )
    return response.data if response.data else []

# Update search_knowledge_base to use retry logic
@agent.tool
async def search_knowledge_base(ctx: RunContext[None], query: str, limit: int | None = None) -> str:
    """Search with retry on transient failures."""
    # ... validation code ...

    try:
        embedding = await get_embedding(reformulated_query)

        # Search with retry
        results = await _search_with_retry(
            service,
            embedding,
            similarity_threshold,
            limit
        )

    except Exception as e:
        logger.error(f"Search failed after retries: {e}", exc_info=True)
        return "Search temporarily unavailable. Please try again."

    # ... rest of processing
```

**Testing**:
- Simulate transient database failures
- Verify 3 retry attempts with exponential backoff
- Confirm proper error handling after max retries

**Success Criteria**:
- Transient failures handled gracefully
- Exponential backoff prevents overwhelming services
- Permanent failures return clear error messages

---

### Task 2.3: Add Type Annotations (2 hours)
**Priority**: HIGH
**File**: `packages/core/agent.py`

**Implementation**:
```python
from typing import TypedDict, NotRequired
from collections.abc import Sequence

class SearchResult(TypedDict):
    """Type-safe search result from database."""
    document_source: str
    content: str
    content_preview: str
    similarity: float
    metadata: NotRequired[dict[str, str]]

class FormattedSource(TypedDict):
    """Type-safe source structure for storage."""
    path: str
    content: str
    similarity: float

def _format_search_results(results: Sequence[SearchResult]) -> str:
    """Format search results with type safety."""
    if not results:
        return "No results found."

    formatted = []
    for i, row in enumerate(results, 1):
        formatted.append(
            f"{i}. {row['document_source']} (similarity: {row['similarity']:.2f})\n"
            f"{row['content']}"
        )

    return "\n\n".join(formatted)

def _extract_sources(results: Sequence[SearchResult]) -> list[FormattedSource]:
    """Extract sources with type safety."""
    return [
        FormattedSource(
            path=row["document_source"],
            content=row["content_preview"],
            similarity=row["similarity"]
        )
        for row in results
    ]
```

**Testing**:
- Run `mypy packages/core/agent.py` to verify type safety
- Ensure no type errors reported
- Verify IDE autocomplete works correctly

**Success Criteria**:
- All functions have proper type annotations
- mypy passes with no errors
- IDE provides accurate type hints

---

### Task 2.4: Implement Search Limits (1 hour)
**Priority**: HIGH
**File**: `packages/config/__init__.py` and `packages/core/agent.py`

**Implementation**:

**Add to config**:
```python
class SearchSettings(BaseModel):
    """Search configuration with limits."""
    default_limit: int = Field(default=10, ge=1, le=100)
    max_limit: int = Field(default=100, ge=1, le=200)
    similarity_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    max_chunks_per_document: int = Field(default=3, ge=1, le=10)
```

**Update search function**:
```python
@agent.tool
async def search_knowledge_base(ctx: RunContext[None], query: str, limit: int | None = None) -> str:
    """Search with enforced limits."""
    # Validate and cap limit
    if limit is None:
        limit = settings.search.default_limit
    else:
        limit = min(limit, settings.search.max_limit)
        if limit < 1:
            limit = settings.search.default_limit

    # Use configured max_chunks_per_document
    MAX_CHUNKS_PER_DOCUMENT = settings.search.max_chunks_per_document

    # ... rest of search logic
```

**Testing**:
- Test with limits exceeding maximum
- Test with negative limits
- Verify configuration limits are enforced

**Success Criteria**:
- All search limits configurable
- Hard limits prevent resource exhaustion
- Configuration validation on startup

---

## Phase 3: Medium Priority (6-8 hours) 📊

**Goal**: Add observability and monitoring capabilities

### Task 3.1: Add Structured Logging (2 hours)
**Priority**: MEDIUM
**File**: `packages/core/agent.py`

**Implementation**:
```python
import structlog

# Replace standard logger
logger = structlog.get_logger(__name__)

@agent.tool
async def search_knowledge_base(ctx: RunContext[None], query: str, limit: int | None = None) -> str:
    """Search with structured logging."""
    # Log request start
    logger.info(
        "search_started",
        query=query[:100],  # Truncate for logging
        limit=limit,
        timestamp=time.time()
    )

    try:
        # ... search logic ...

        logger.info(
            "search_completed",
            query=query[:100],
            result_count=len(results),
            deduped_count=len(deduped_results),
            document_count=len(seen_documents),
            avg_similarity=sum(r['similarity'] for r in results) / len(results) if results else 0,
            duration_ms=(time.time() - start_time) * 1000
        )

    except Exception as e:
        logger.error(
            "search_failed",
            query=query[:100],
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=(time.time() - start_time) * 1000,
            exc_info=True
        )
        raise
```

**Testing**:
- Verify structured logs output JSON format
- Check log aggregation tools can parse logs
- Verify sensitive data is not logged

**Success Criteria**:
- All operations logged with structured context
- Log levels appropriate (INFO for success, ERROR for failures)
- Logs are machine-parseable JSON

---

### Task 3.2: Implement Metrics Collection (2 hours)
**Priority**: MEDIUM
**File**: `packages/core/agent.py` and new `packages/core/metrics.py`

**Implementation**:
```python
# packages/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Metrics
search_counter = Counter(
    'rag_searches_total',
    'Total searches performed',
    ['status']  # success, error, no_results
)

search_duration = Histogram(
    'rag_search_duration_seconds',
    'Search operation duration',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

retrieval_quality = Histogram(
    'rag_retrieval_similarity',
    'Average similarity scores',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

chunks_retrieved = Histogram(
    'rag_chunks_retrieved',
    'Number of chunks retrieved per search',
    buckets=[0, 1, 3, 5, 10, 20, 50, 100]
)

# Update search_knowledge_base
from packages.core.metrics import (
    search_counter, search_duration,
    retrieval_quality, chunks_retrieved
)

@agent.tool
async def search_knowledge_base(ctx: RunContext[None], query: str, limit: int | None = None) -> str:
    """Search with metrics collection."""
    start_time = time.time()

    try:
        # ... search logic ...

        # Record metrics
        duration = time.time() - start_time
        search_duration.observe(duration)
        chunks_retrieved.observe(len(deduped_results))

        if results:
            avg_similarity = sum(r['similarity'] for r in results) / len(results)
            retrieval_quality.observe(avg_similarity)
            search_counter.labels(status='success').inc()
        else:
            search_counter.labels(status='no_results').inc()

        return formatted_results

    except Exception as e:
        search_counter.labels(status='error').inc()
        raise
```

**Testing**:
- Verify metrics endpoint exposes Prometheus format
- Test metric collection with various scenarios
- Verify counters and histograms update correctly

**Success Criteria**:
- All key operations have metrics
- Metrics accessible via `/metrics` endpoint
- Dashboards can visualize search quality

---

### Task 3.3: Add Connection Pooling (2 hours)
**Priority**: MEDIUM
**File**: `packages/utils/supabase_client.py`

**Implementation**:
```python
from httpx import AsyncClient, Limits
from functools import lru_cache

@lru_cache(maxsize=1)
def get_supabase_client() -> AsyncClient:
    """Get singleton Supabase client with connection pooling."""
    limits = Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0
    )

    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_key,
        options=ClientOptions(
            postgrest_client_timeout=10,
            schema="public",
        ),
        http_client=AsyncClient(limits=limits)
    )

async def close_supabase_client():
    """Close Supabase client on shutdown."""
    client = get_supabase_client()
    await client.aclose()
```

**Testing**:
- Load test with 50+ concurrent requests
- Verify connection reuse
- Monitor connection pool metrics

**Success Criteria**:
- Connections pooled and reused efficiently
- No connection leaks under load
- Improved performance under concurrent load

---

## Phase 4: Testing & Validation (4-6 hours) ✅

**Goal**: Comprehensive test coverage and validation

### Task 4.1: Write Unit Tests (2 hours)
**Priority**: HIGH
**File**: `tests/test_agent.py`

**Implementation**:
```python
import pytest
from packages.core.agent import (
    reformulate_query,
    RAGService,
    SearchRequest,
    _format_search_results
)

class TestQueryReformulation:
    def test_minimal_reformulation(self):
        """Test query reformulation preserves content."""
        query = "Quels sont tous les critères de classification pour Type D?"
        result = reformulate_query(query)
        # Should only strip punctuation
        assert result == "Quels sont tous les critères de classification pour Type D"

    def test_preserves_prepositions(self):
        """Test French prepositions are preserved."""
        query = "critères de la classification pour Type D"
        result = reformulate_query(query)
        assert "de" in result
        assert "pour" in result

class TestRAGService:
    def test_service_isolation(self):
        """Test RAG services are isolated."""
        from packages.core.agent import set_rag_service, get_rag_service

        service1 = RAGService(supabase_client=mock_client)
        service1.add_sources([{'path': 'doc1.pdf'}])

        set_rag_service(service1)
        retrieved = get_rag_service()

        assert len(retrieved.get_sources()) == 1
        assert retrieved.get_sources()[0]['path'] == 'doc1.pdf'

    def test_source_accumulation(self):
        """Test sources accumulate correctly."""
        service = RAGService(supabase_client=mock_client)
        service.add_sources([{'path': 'doc1.pdf'}])
        service.add_sources([{'path': 'doc2.pdf'}])

        assert len(service.get_sources()) == 2

class TestInputValidation:
    def test_empty_query_rejected(self):
        """Test empty queries are rejected."""
        with pytest.raises(ValidationError):
            SearchRequest(query="", limit=10)

    def test_long_query_rejected(self):
        """Test overly long queries are rejected."""
        long_query = "a" * 1001
        with pytest.raises(ValidationError):
            SearchRequest(query=long_query, limit=10)

    def test_negative_limit_rejected(self):
        """Test negative limits are rejected."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=-1)

    def test_malicious_input_rejected(self):
        """Test malicious patterns are rejected."""
        with pytest.raises(ValidationError):
            SearchRequest(query="'; DROP TABLE chunks; --", limit=10)

class TestMultiChunkRetrieval:
    def test_keeps_multiple_chunks_per_doc(self):
        """Test multi-chunk retrieval logic."""
        results = [
            {'document_source': 'doc1.pdf', 'similarity': 0.9, 'content': 'chunk1'},
            {'document_source': 'doc1.pdf', 'similarity': 0.8, 'content': 'chunk2'},
            {'document_source': 'doc1.pdf', 'similarity': 0.7, 'content': 'chunk3'},
            {'document_source': 'doc1.pdf', 'similarity': 0.6, 'content': 'chunk4'},
        ]

        # Should keep top 3 from doc1
        deduped = deduplicate_results(results, max_per_doc=3)
        assert len(deduped) == 3
        assert all(r['document_source'] == 'doc1.pdf' for r in deduped)
```

**Testing Commands**:
```bash
pytest tests/test_agent.py -v
pytest tests/test_agent.py --cov=packages/core/agent --cov-report=html
```

**Success Criteria**:
- All unit tests pass
- Code coverage >80%
- Edge cases covered

---

### Task 4.2: Write Integration Tests (2 hours)
**Priority**: HIGH
**File**: `tests/integration/test_agent_integration.py`

**Implementation**:
```python
import pytest
from packages.core.agent import agent, set_rag_service, RAGService

@pytest.mark.asyncio
async def test_french_query_retrieval():
    """Test French query retrieves Type D criteria."""
    # Setup
    service = RAGService(supabase_client=get_test_client())
    set_rag_service(service)

    # Test query from user's screenshot
    query = "Quels sont tous les critères du type D?"

    result = await agent.run(query)

    # Verify response contains Type D information
    assert "Type D" in result.data
    assert "critères" in result.data.lower()

    # Verify sources were retrieved
    sources = service.get_sources()
    assert len(sources) > 0
    assert any("Type D" in s['content'] for s in sources)

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test thread safety with concurrent requests."""
    async def make_request(query: str, expected_content: str):
        service = RAGService(supabase_client=get_test_client())
        set_rag_service(service)

        result = await agent.run(query)
        sources = service.get_sources()

        assert len(sources) > 0
        assert expected_content in result.data

        return sources

    # Run concurrent requests
    results = await asyncio.gather(
        make_request("Type D criteria", "Type D"),
        make_request("Type C criteria", "Type C"),
        make_request("Type A criteria", "Type A")
    )

    # Verify no cross-contamination
    assert len(results) == 3
    assert all(len(r) > 0 for r in results)

@pytest.mark.asyncio
async def test_error_recovery():
    """Test graceful error handling."""
    service = RAGService(supabase_client=get_failing_client())
    set_rag_service(service)

    result = await agent.run("test query")

    # Should return error message, not crash
    assert "unavailable" in result.data.lower() or "error" in result.data.lower()
```

**Testing Commands**:
```bash
pytest tests/integration/test_agent_integration.py -v
pytest tests/integration/ --cov=packages/core
```

**Success Criteria**:
- Integration tests pass with real database
- Concurrent request handling verified
- Error scenarios handled gracefully

---

### Task 4.3: Load Testing (2 hours)
**Priority**: MEDIUM
**File**: `tests/load/test_load.py`

**Implementation**:
```python
import asyncio
import time
from locust import HttpUser, task, between

class RAGUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def chat_query(self):
        """Simulate user chat query."""
        response = self.client.post(
            "/api/v1/chat",
            json={"message": "Quels sont les critères Type D?"},
            headers={"Content-Type": "application/json"}
        )

        # Verify response
        assert response.status_code == 200

# Run with: locust -f tests/load/test_load.py --host http://localhost:8000
```

**Load Test Scenarios**:
1. **Steady Load**: 10 users, 5 min duration
2. **Burst Load**: Ramp from 0 to 50 users over 2 min
3. **Sustained Load**: 25 users, 30 min duration

**Metrics to Monitor**:
- Response time (p50, p95, p99)
- Error rate
- Database connection pool usage
- Memory usage

**Success Criteria**:
- P95 response time <2s under load
- Error rate <0.1% under steady load
- No memory leaks over 30 min test
- Connection pool stable

---

## Configuration Updates

### Task C.1: Update .env File
**File**: `.env`

**Changes**:
```bash
# Line 21 - CRITICAL: Update similarity threshold
SEARCH_SIMILARITY_THRESHOLD=0.65

# Add new configuration
SEARCH_MAX_CHUNKS_PER_DOCUMENT=3
SEARCH_MAX_LIMIT=100
SEARCH_DEFAULT_LIMIT=10
```

---

### Task C.2: Update config/__init__.py
**File**: `packages/config/__init__.py`

**Changes**:
```python
class SearchSettings(BaseModel):
    """Enhanced search configuration."""
    default_limit: int = Field(default=10, ge=1, le=100)
    max_limit: int = Field(default=100, ge=1, le=200)
    similarity_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    max_chunks_per_document: int = Field(default=3, ge=1, le=10)
```

---

## Documentation Updates

### Task D.1: Update CHANGELOG.md

**Add**:
```markdown
## [1.1.0] - 2025-01-XX

### Critical Fixes
- Fixed query reformulation destroying French semantic relationships
- Implemented multi-chunk retrieval (3 chunks per document)
- Replaced global state with thread-safe RAGService using contextvars

### Added
- Input validation with Pydantic models
- Retry logic with exponential backoff
- Comprehensive error handling
- Type safety with TypedDict annotations
- Structured logging with context
- Prometheus metrics collection
- Connection pooling for database

### Changed
- Similarity threshold: 0.4 → 0.65 for better precision
- Search limits: configurable max limits
- Error messages: more user-friendly

### Performance
- Thread-safe for concurrent requests
- Connection pooling reduces latency
- Improved retrieval quality for French queries
```

---

### Task D.2: Update README.md

**Add deployment section**:
```markdown
## Production Deployment

### Requirements
- Thread-safe for concurrent requests
- Connection pooling configured
- Metrics endpoint at `/metrics`
- Structured logging enabled

### Configuration
See `.env.example` for all configuration options.

Key settings:
- `SEARCH_SIMILARITY_THRESHOLD`: 0.65 (recommended for French regulatory content)
- `SEARCH_MAX_CHUNKS_PER_DOCUMENT`: 3 (comprehensive coverage)
- `SEARCH_MAX_LIMIT`: 100 (prevents resource exhaustion)

### Monitoring
Prometheus metrics available at `/metrics`:
- `rag_searches_total`: Total searches by status
- `rag_search_duration_seconds`: Search latency
- `rag_retrieval_similarity`: Retrieval quality
- `rag_chunks_retrieved`: Chunks per search
```

---

## Risk Assessment

### High Risk Areas
1. **Global State Replacement**: Complex refactoring, thorough testing required
2. **Concurrent Request Handling**: Must verify no race conditions
3. **Error Handling**: Ensure no information leakage in error messages

### Mitigation Strategies
1. **Incremental Implementation**: Deploy Phase 1 first, monitor, then proceed
2. **Comprehensive Testing**: Unit, integration, and load tests before production
3. **Gradual Rollout**: Deploy to staging first, A/B test with small user subset
4. **Rollback Plan**: Keep previous version deployable, feature flags for new code

### Validation Checkpoints
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass
- [ ] Load tests pass (P95 <2s, error rate <0.1%)
- [ ] Manual testing with French queries
- [ ] Code review completed
- [ ] Documentation updated

---

## Success Metrics

### Immediate (Phase 1)
- ✅ French queries retrieve Type D criteria successfully
- ✅ Multi-chunk retrieval provides comprehensive information
- ✅ No thread safety issues under load
- ✅ Basic error handling prevents crashes

### Short-term (Phase 2)
- ✅ All inputs validated, no crashes from malicious input
- ✅ Transient failures handled with retries
- ✅ Type-safe code with mypy validation
- ✅ Search limits prevent resource exhaustion

### Long-term (Phase 3)
- ✅ Structured logs enable debugging
- ✅ Metrics provide visibility into search quality
- ✅ Connection pooling improves performance
- ✅ Production-ready monitoring and alerting

---

## Timeline & Dependencies

### Week 1: Critical Fixes
- Day 1-2: Phase 1 implementation
- Day 3: Phase 1 testing and validation
- Day 4: Deploy Phase 1 to staging
- Day 5: Monitor and bug fixes

### Week 2: High Priority
- Day 1-2: Phase 2 implementation
- Day 3: Phase 2 testing
- Day 4-5: Deploy Phase 2, monitor

### Week 3: Medium Priority & Polish
- Day 1-2: Phase 3 implementation
- Day 3: Load testing
- Day 4-5: Production deployment preparation

---

## Agent Assignments

### Phase 1 (Critical)
- **Backend Architect**: Global state refactoring, RAGService design
- **Python Expert**: Query reformulation fix, deduplication logic
- **QA Engineer**: Error handling, validation testing

### Phase 2 (High Priority)
- **Security Engineer**: Input validation, malicious input protection
- **Performance Engineer**: Retry logic, connection pooling
- **Python Expert**: Type safety implementation

### Phase 3 (Medium Priority)
- **DevOps Engineer**: Structured logging, metrics collection
- **Performance Engineer**: Connection pooling, load testing
- **QA Engineer**: Integration and load testing

### Phase 4 (Testing)
- **QA Engineer**: Lead all testing efforts
- **Python Expert**: Unit test implementation
- **Performance Engineer**: Load testing and optimization

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Set up development branch**: `feature/rag-agent-refactor`
3. **Begin Phase 1 implementation** with backend architect and Python expert
4. **Daily standups** to track progress
5. **Weekly demos** to stakeholders

---

## Questions & Decisions Needed

1. **Deployment Strategy**: Blue-green deployment or gradual rollout?
2. **Monitoring Tools**: Which monitoring stack (Prometheus + Grafana)?
3. **Testing Environment**: Separate staging database or use prod replica?
4. **Feature Flags**: Use feature flags for gradual rollout?
5. **Performance Targets**: Confirm P95 <2s is acceptable?

---

**Document Version**: 1.0
**Created**: 2025-01-27
**Last Updated**: 2025-01-27
**Status**: Ready for Implementation
