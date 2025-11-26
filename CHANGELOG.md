# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **RAG Relevance Scoring**: Search results now include visible pertinence scores
  - Results sorted by similarity (highest first)
  - Citations format: `[Source: Title | Pertinence: 85%]`
  - Configurable similarity threshold via `SEARCH_SIMILARITY_THRESHOLD` (default: 0.3)
- **Improved RAG Search Config**: Enhanced search defaults
  - Default result limit increased from 5 to 10 chunks
  - New `similarity_threshold` setting to filter low-quality matches
  - Environment variables: `SEARCH_DEFAULT_LIMIT`, `SEARCH_SIMILARITY_THRESHOLD`
- **Centralized Configuration System**: New `packages/config/` module for type-safe configuration
  - Frozen dataclasses with environment variable support and sensible defaults
  - Domain-specific configs: `LLMConfig`, `EmbeddingConfig`, `DatabaseConfig`, `ChunkingConfig`, `SearchConfig`, `APIConfig`
  - Singleton pattern with `@lru_cache` for consistent settings across application
  - Multi-provider LLM support via `settings.llm.create_model()` method
- **Multi-Provider LLM Support**: Support for OpenAI, Chutes.ai (Bittensor), Ollama, and any OpenAI-compatible API
  - Configure via `LLM_BASE_URL` for custom API endpoints
  - Separate embedding provider configuration via `EMBEDDING_BASE_URL`
  - Fallback chain for API keys: `LLM_API_KEY` → `OPENAI_API_KEY`
- **Web Scraper Module**: New `packages/scraper/` module using Crawl4AI for markdown generation
  - YAML-based source configuration (`sources.yaml`) with rate limiting and retry support
  - Supports depth-based crawling, URL pattern filtering, and concurrent page limits
  - Outputs markdown files with YAML frontmatter metadata
  - Generates crawl summaries for each source
- **HyDE (Hypothetical Document Embedding)**: Query transformation in `packages/core/agent.py`
  - Generates hypothetical document answer using GPT-4o-mini before embedding
  - Improves semantic matching between queries and document chunks
  - French-language prompt optimized for Brussels public space regulations
- **Markdown Document Viewer**: Extended `DocumentViewer.tsx` for markdown support
  - Auto-detects file type (`.md` vs `.pdf`) and renders appropriately
  - Uses `ReactMarkdown` with `remark-gfm` for GitHub-flavored markdown
- **Document Corpus**: 838 chunks from 62 files (legal, PDFs, scraped web content)
- **ErrorBoundary**: Implemented error boundary wrapper in layout.tsx for graceful error handling

### Changed

- **RAG Agent System Prompt**: Complete rewrite in French for better factual responses
  - Explicit instructions to prioritize high-relevance results (>70%)
  - Must cite sources with pertinence scores
  - Never guess - only use information from knowledge base
- **Similarity Search**: Now filters results below threshold before returning
  - Logs filtered vs total results for debugging
- **Configuration Consolidation**: All hardcoded values now configurable via environment variables
  - Database pool settings: `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_COMMAND_TIMEOUT`
  - Chunking parameters: `CHUNK_SIZE`, `CHUNK_OVERLAP`, `CHUNK_MAX_SIZE`, `CHUNK_MIN_SIZE`
  - Embedding settings: `EMBEDDING_BATCH_SIZE`, `EMBEDDING_MAX_RETRIES`, `EMBEDDING_CACHE_MAX_SIZE`
  - API settings: `CORS_ORIGINS`, `SLOW_REQUEST_THRESHOLD_MS`
- **Files Updated for Centralized Config**:
  - `packages/utils/db_utils.py` - Uses `settings.database.*` for pool configuration
  - `packages/ingestion/chunker.py` - Uses `settings.chunking.*` for chunk parameters
  - `packages/ingestion/embedder.py` - Uses `settings.embedding.*` for batch/retry settings
  - `packages/core/agent.py` - Uses `settings.llm.create_model()` for multi-provider support
  - `services/api/app/main.py` - Uses `settings.api.*` for CORS and performance settings
- **CLI Logging**: Re-enabled logger statements in cli.py (active in verbose mode)
- **License**: MIT → Apache 2.0 (required by Crawl4AI dependency)
- **Directory Structure**: Reorganized from `documents/` to `data/` with input/output separation
  - `data/raw/pdfs/` - Manual PDF documents (input)
  - `data/processed/scraped/` - Web scraper output (generated)
  - `data/examples/` - Tutorial files (tracked in git)
  - Updated code references in `documents.py`, `config.py`, `sources.yaml`
- **Anti-Hallucination System Prompt**: Rewrote in French to prevent hallucination
  - Agent MUST only use content from retrieved chunks
  - Explicit instructions to NEVER use general LLM knowledge
  - French language response requirement for Brussels context
- **Retrieval Quality**: Added rerank score threshold filtering (-2.0 minimum)

### Fixed
- **Ingestion Pipeline**: Fixed `IngestionResult` Pydantic model mismatch
  - Removed unused fields that didn't exist in model definition
- **Cache Async Methods**: Fixed method naming in `packages/utils/cache.py`
  - Renamed `get()` → `async_get()`, `set()` → `async_set()` to avoid shadowing builtins

### Removed
- **Performance Middleware Simplification**: Reduced `services/api/app/middleware/performance.py` from 235 to 73 lines
  - Removed unused `PerformanceMetricsStore` and `EndpointMetrics` classes
  - Removed `/metrics` and `/metrics/reset` endpoints (no consumer)
  - Kept valuable slow request logging and `X-Response-Time` header
- **Frontend Web Vitals Removal**: Removed 433 lines of unused code (YAGNI)
  - Deleted `services/web/src/lib/performance.ts` (302 lines)
  - Deleted `services/web/src/hooks/useWebVitals.ts` (131 lines)
  - Simplified `Providers.tsx` (removed Web Vitals initialization)
  - Removed `web-vitals` npm dependency
- **Git History Cleanup**: Gitignored `archives/` and `documents/archive/` (~127MB excluded from tracking)
- **Dead Code Cleanup** (~867 lines removed, ~20% reduction):
  - `packages/utils/models.py` - 8 unused Pydantic models (213 lines)
  - `packages/core/reranker.py` - Unused cross-encoder module (96 lines)
  - `packages/utils/cache.py` - Removed LRUCache base class, `@cached` decorator, `get_or_set()`, `cleanup_expired()`
  - `packages/utils/providers.py` - Removed unused `get_llm_model()`, `get_ingestion_model()`, `validate_configuration()`, `get_model_info()`
  - `packages/ingestion/chunker.py` - Removed unused `SimpleChunker` class
  - `packages/ingestion/embedder.py` - Removed unused `EmbeddingCache` class
  - `chunker_no_docling.py` - Superseded chunker implementation
  - `SourceLink.tsx` - Unused component with broken logic
  - `scroll-area.tsx`, `skeleton.tsx` - Unused UI components
  - `checkHealth()` in api-client.ts - Unused function
  - `clear_message_history()` in rag_wrapper.py - Unused function
  - Removed graph-related remnants from `ingest.py`
- **Metadata Cleanup**: Updated placeholder "Create Next App" metadata in layout.tsx
- **Unused Dependencies**: Removed `aiohttp`, `numpy`, `hf-xet`, `openai-whisper` from pyproject.toml

### Security
- **Config Protection**: Added `.mcp.json` to `.gitignore`
- **Template Added**: Created `.mcp.json.example` for safe configuration sharing

## [0.1.0] - 2025-11-21

### Added
- Initial RAG agent implementation with PydanticAI
- Document ingestion pipeline with Docling for PDF processing
- Supabase pgvector integration for vector storage
- FastAPI backend with streaming SSE responses
- Next.js frontend with chat interface
- Cross-encoder reranking for improved retrieval quality
- PDF viewer with zoom controls in web interface

### Architecture
- **Backend**: FastAPI + Uvicorn + PydanticAI
- **Frontend**: Next.js 14+ with App Router, Radix UI, Tailwind CSS
- **Vector DB**: Supabase pgvector with IVFFlat index
- **Embeddings**: OpenAI text-embedding-3-small
- **Document Processing**: Docling with hybrid chunking
