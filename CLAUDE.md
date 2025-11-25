# Osiris MultiRAG Agent - Project Context

## Overview
RAG (Retrieval-Augmented Generation) agent for document Q&A using Docling for document processing and Supabase for vector storage.

## Project Structure
```
osiris-multirag-agent/
├── services/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py         # App entry point
│   │   │   └── api/            # API routes (chat.py, documents.py)
│   │   └── .venv/              # Python virtual environment
│   └── web/                    # Next.js frontend
│       └── src/
│           ├── app/            # Next.js app router
│           ├── components/     # React components
│           ├── hooks/          # Custom hooks (useChat.ts)
│           └── types/          # TypeScript types
├── data/                       # Data directory (gitignored except examples/)
│   ├── raw/pdfs/               # Manual PDF documents for ingestion
│   ├── processed/scraped/      # Web scraper output (auto-generated)
│   └── examples/               # Tutorial examples (tracked in git)
├── packages/                   # Shared Python packages
│   ├── core/                   # RAG agent and CLI
│   ├── ingestion/              # Document processing pipeline
│   ├── scraper/                # Web scraper module
│   └── utils/                  # Shared utilities
├── scripts/                    # Utility scripts
│   └── restart-servers.sh      # Dev server restart script
└── logs/                       # Server logs
```

## Tech Stack

### Backend
- **Framework**: FastAPI with Python 3.9+
- **Server**: Uvicorn with auto-reload
- **AI**: PydanticAI for agent orchestration
- **Vector DB**: Supabase pgvector
- **Document Processing**: Docling

### Frontend
- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript
- **UI**: Radix UI, Tailwind CSS, shadcn/ui
- **Markdown**: react-markdown with remark-gfm

## Development Commands

### Start Development Servers
```bash
./scripts/restart-servers.sh
```
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health

### Manual Start
```bash
# Backend (from project root)
cd services/api
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd services/web
npm run dev
```

### View Logs
```bash
tail -f logs/backend_*.log
tail -f logs/frontend_*.log
```

## API Endpoints

### Chat
- `POST /api/v1/chat` - Stream chat responses (SSE)

### Documents
- `GET /api/v1/documents/{path}` - Serve documents inline

## Key Patterns

### Chat Streaming (SSE)
Backend sends Server-Sent Events:
- `thinking` - Agent reasoning
- `chunk` - Response text chunk
- `sources` - Retrieved document sources
- `done` - Stream complete

### Source Deduplication
Frontend deduplicates sources by path, keeping highest similarity score.

### Document Serving
Documents served inline with `Content-Disposition: inline` for browser display.

## Environment Variables

### Backend
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `OPENAI_API_KEY` - OpenAI API key

### Frontend
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000/api/v1)

## Conventions

### Code Style
- Python: PEP 8, type hints required
- TypeScript: Strict mode, explicit types
- React: Functional components with hooks

### File Organization
- API routes in `services/api/app/api/`
- React components in `services/web/src/components/`
- Tests in `tests/` directories
- Scripts in `scripts/`

### Git Workflow
- Feature branches for all work
- Meaningful commit messages
- Run lint/typecheck before committing

## Common Issues

### Backend won't start
1. Check `.venv` exists in `services/api/` or project root
2. Verify PYTHONPATH includes project root for `packages/`
3. Check port 8000 is free: `lsof -i :8000`

### Frontend API errors
1. Verify `NEXT_PUBLIC_API_URL` is set correctly
2. Check backend is running and healthy
3. Avoid duplicate `/api/v1/` in URLs

### Documents not found
1. Documents should be in `data/raw/` or `data/processed/` directories
2. Backend searches both raw and processed directories recursively
3. Check file permissions
