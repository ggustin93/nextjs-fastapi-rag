# Quick Start: Chat Interface

This guide will help you quickly get the Next.js chat interface running with the Docling RAG Agent backend.

## Prerequisites

1. **Backend Setup**: Ensure you have completed the backend setup (see `services/api/README.md`)
2. **Node.js**: Version 18.x or higher installed
3. **Database**: PostgreSQL with documents ingested

## Step 1: Start the Backend

```bash
cd services/api

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the FastAPI server
uvicorn app.main:app --reload
```

The backend will be available at `http://localhost:8000`

Verify it's running by visiting: `http://localhost:8000/api/v1/chat/health`

## Step 2: Start the Frontend

Open a new terminal:

```bash
cd services/web

# Install dependencies (if not already done)
npm install

# Start the development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Step 3: Chat with Your Documents

1. Open your browser to `http://localhost:3000`
2. Type a question about your ingested documents
3. Watch as the AI streams its response in real-time!

## Example Questions

Try asking questions like:

- "What are the main topics in the documents?"
- "Summarize the key findings"
- "What does the document say about [specific topic]?"
- "Can you explain [concept] from the documents?"

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌────────────────┐
│   Next.js       │         │   FastAPI        │         │  PostgreSQL    │
│   Frontend      │  SSE    │   Backend        │  Query  │  + PGVector    │
│   (Port 3000)   │────────▶│  (Port 8000)     │────────▶│                │
└─────────────────┘         └──────────────────┘         └────────────────┘
                                      │
                                      │ Wraps
                                      ▼
                            ┌──────────────────┐
                            │  RAG Agent       │
                            │  (PydanticAI)    │
                            └──────────────────┘
```

## Technology Stack

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **Components**: shadcn/ui (accessible, customizable)
- **Icons**: Lucide React
- **Communication**: Server-Sent Events (SSE)

### Backend
- **Framework**: FastAPI
- **AI Framework**: PydanticAI
- **LLM**: OpenAI GPT-4o-mini
- **Embeddings**: OpenAI text-embedding-3-small (1536d)
- **Database**: PostgreSQL with PGVector extension
- **Streaming**: sse-starlette

## Project Structure

```
osiris-multirag-agent/
├── packages/               # Core Python packages
│   ├── core/              # RAG agent and CLI
│   │   ├── agent.py       # Core RAG logic
│   │   └── cli.py         # CLI interface
│   └── ingestion/         # Document processing
├── services/              # Deployable services
│   ├── api/               # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py    # FastAPI app with CORS
│   │   │   ├── core/      # RAG wrapper
│   │   │   └── routers/   # Chat endpoint
│   │   └── requirements.txt
│   └── web/               # Next.js frontend
│       ├── src/
│       │   ├── app/       # Next.js App Router
│       │   ├── components/# React components
│       │   ├── hooks/     # React hooks (useChat)
│       │   └── lib/       # API client, utilities
│       └── package.json
├── tests/                 # Python test suite
├── deploy/                # Docker configuration
└── docs/                  # Documentation
```

## Features

### Current Features
- ✅ Real-time chat with streaming responses
- ✅ Clean, responsive UI with dark mode support
- ✅ Error handling and loading states
- ✅ Clear chat history
- ✅ SSE streaming for token-by-token responses
- ✅ Accessible components (WCAG compliant)

### Future Enhancements
- 🔄 Session history persistence
- 🔄 Source citations with document snippets
- 🔄 Document upload interface
- 🔄 Multi-session management
- 🔄 User authentication
- 🔄 Export chat history

## Troubleshooting

### Backend not responding
- Check if the backend is running: `ps aux | grep uvicorn`
- Verify the port is correct: `lsof -i :8000`
- Check backend logs for errors

### Frontend connection errors
- Verify `.env.local` has the correct API URL
- Check CORS configuration in `services/api/app/main.py`
- Check browser console for detailed error messages

### Database connection issues
- Ensure PostgreSQL is running
- Check database credentials in environment variables
- Verify PGVector extension is installed

### No documents returned
- Ensure documents have been ingested
- Check if vector embeddings exist: `SELECT COUNT(*) FROM document_chunks;`
- Verify OpenAI API key is set correctly

## Environment Variables

### Backend (.env)
```bash
# Required
OPENAI_API_KEY=your_openai_api_key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Optional
LOG_LEVEL=INFO
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Development Workflow

### 1. Backend Development
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Development
```bash
cd frontend
npm run dev
```

### 3. Testing the Integration
1. Start both backend and frontend
2. Open `http://localhost:3000`
3. Send a test message
4. Check backend logs for request processing
5. Verify streaming response in browser

## Next Steps

1. **Ingest Documents**: Use the CLI to ingest your documents
   ```bash
   python -m packages.ingestion.ingest --documents /path/to/docs
   ```

2. **Customize UI**: Modify components in `services/web/src/components/`

3. **Add Features**: Extend functionality based on your needs
   - Session persistence
   - Source citations
   - Document management

4. **Deploy**: Follow deployment guides in respective README files

## Resources

- [Backend Documentation](../services/api/README.md)
- [Frontend Documentation](../services/web/README.md)
- [Architecture Overview](claudedocs/architecture.md)
- [API Reference](claudedocs/api-reference.md)
- [Project Structure](claudedocs/project-structure.md)

## Support

For issues or questions:
1. Check the troubleshooting sections
2. Review the documentation in `claudedocs/`
3. Check backend and frontend logs
4. Verify environment variables are set correctly

Happy chatting! 🎉
