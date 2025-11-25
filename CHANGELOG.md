# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

### Removed
- **Git History Cleanup**: Gitignored `archives/` and `documents/archive/` (~127MB excluded from tracking)
- **Dead Code Cleanup**:
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
