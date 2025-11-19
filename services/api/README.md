# FastAPI Backend for Docling RAG Agent

Minimal FastAPI backend that wraps the existing Python RAG agent for use with the Next.js chat interface.

## Features

- **Streaming Chat**: Server-Sent Events (SSE) for real-time responses
- **RAG Integration**: Uses existing PydanticAI agent and knowledge base
- **CORS Enabled**: Configured for Next.js frontend on localhost:3000
- **Health Checks**: Endpoint monitoring

## Setup

### 1. Install Dependencies

From the project root:

```bash
cd backend
pip install -r requirements.txt
```

Or using uv (recommended):

```bash
cd backend
uv pip install -r requirements.txt
```

### 2. Environment Variables

The backend uses the same `.env` file as the main project. Ensure these variables are set in the root `.env`:

```bash
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_KEY=...
```

### 3. Run the Server

**Development mode with auto-reload:**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Production mode:**

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

## API Endpoints

### Chat Streaming

**POST** `/api/v1/chat/stream`

Stream chat responses using Server-Sent Events.

**Request:**
```json
{
  "message": "What is in the knowledge base?",
  "session_id": "optional-session-id"
}
```

**Response:** SSE stream with events:

```
event: token
data: {"content": "Based"}

event: token
data: {"content": " on"}

event: done
data: {"content": ""}
```

### Health Check

**GET** `/api/v1/chat/health`

Check if the chat service is running.

**Response:**
```json
{
  "status": "healthy",
  "service": "chat"
}
```

## Architecture

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app with CORS
│   ├── core/
│   │   └── rag_wrapper.py   # Wraps existing rag_agent.py
│   └── api/
│       └── chat.py          # Chat endpoints
└── requirements.txt
```

### Integration with Existing Code

The backend reuses existing project modules:
- `utils/providers.py` - OpenAI client configuration
- `utils/db_utils.py` - Database utilities
- `ingestion/embedder.py` - Embedding generation
- `rag_agent.py` logic - Wrapped in `rag_wrapper.py`

## Testing

### Test with curl

```bash
# Health check
curl http://localhost:8000/health

# Chat (non-streaming)
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### Test SSE Streaming

Use a tool like [websocat](https://github.com/vi/websocat) or the Next.js frontend to test streaming responses.

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn app.main:app --reload --port 8001
```

### Module Import Errors

If you see `ModuleNotFoundError`, ensure you're running from the backend directory and the parent project is in the Python path:

```bash
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
uvicorn app.main:app --reload
```

### Database Connection Errors

Ensure PostgreSQL is running and the DATABASE_URL in `.env` is correct:

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1;"
```

## Development

### Hot Reload

The `--reload` flag enables auto-reload when code changes:

```bash
uvicorn app.main:app --reload
```

### API Documentation

FastAPI automatically generates interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Next Steps

1. ✅ Backend is running
2. Set up the Next.js frontend (see `../frontend/README.md`)
3. Test the full stack integration

## License

Same as parent project
