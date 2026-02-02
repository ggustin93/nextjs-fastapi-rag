# Changelog

All notable changes to the nextjs-fastapi-rag project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adhering to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-01-30

### Added

- **Cross-encoder reranking** - Neural reranking with BAAI/bge-reranker-v2-m3 for improved retrieval precision (+20-35% Precision@10 expected)
  - Hybrid architecture: BGE primary with Cohere API fallback
  - Lazy model loading for efficient resource usage
  - Configuration via environment variables:
    ```bash
    RERANKER_ENABLED=true
    RERANKER_MODEL=BAAI/bge-reranker-v2-m3
    RERANKER_TOP_K=10
    RERANKER_BATCH_SIZE=32
    RERANKER_FALLBACK_ENABLED=true
    ```
  - Requires: `pip install transformers torch` (optional Cohere: `pip install cohere`)

- **HNSW index with ef_search tuning** - Upgraded from IVFFlat to HNSW for ~10x faster vector search
  - Query-time recall/latency tradeoff via `ef_search` parameter
  - Migration: `sql/migrations/001_hnsw_index.sql`

- **Hybrid search ef_search parameter** - Runtime HNSW tuning in search queries
  - Default: 100 (balanced), use 200+ for high-recall scenarios
  - Migration: `sql/migrations/002_hybrid_search_ef_search.sql`

- **OTRS ticket system integration** - Search and view OTRS tickets via GenericInterface REST API
  - TicketViewer component for iframe-based ticket viewing
  - Session-based authentication with automatic caching

### Changed

- **Agent renaming**: OTRS agent ID changed from `otrs-agent` to `otrs` for consistency
- **Chat UI enhancements** for OTRS integration with improved agent configuration

### Fixed

- CI disk space exhaustion in Docker builds
- Concurrency deadlock in deploy workflow
- System prompt tests made language-agnostic
- Tool badge bleeding and RAG hallucination prevention

## [0.1.0] - 2025-01-17

### Added

- Initial RAG pipeline with hybrid search (vector + full-text)
- RRF (Reciprocal Rank Fusion) for result combination
- Query expansion with LLM-based synonym generation
- Title-based re-ranking for document relevance
- Multi-provider LLM support (OpenAI, Chutes.ai, Ollama)
- Streaming chat with SSE (Server-Sent Events)
- Tool registry with extensible architecture
- Weather tool (Open-Meteo integration)
- OSIRIS Brussels worksite tool
- French technical content optimization
- Docling-based document ingestion
- Crawl4AI web scraper integration
