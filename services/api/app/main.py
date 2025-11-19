"""FastAPI application entry point for Docling RAG Agent."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api import chat, documents

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Docling RAG Agent API",
    description="RESTful API for conversational RAG using PydanticAI",
    version="0.1.0"
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Docling RAG Agent API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/chat/health"
    }


@app.get("/health")
async def health():
    """Global health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
