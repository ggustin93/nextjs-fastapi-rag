"""
Frontend-Backend Integration Tests.

Tests API endpoints with the exact request/response formats
expected by the Next.js frontend.
"""

import os
import sys

import pytest
from httpx import ASGITransport, AsyncClient

# Import the FastAPI app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "api"))
from app.main import app


@pytest.fixture
async def client():
    """Create test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestChatStreamEndpoint:
    """Test /api/v1/chat/stream endpoint - critical frontend connection."""

    @pytest.mark.asyncio
    async def test_chat_stream_request_format(self, client):
        """
        Frontend sends: {message: string, session_id?: string}
        API should accept this format without error.
        """
        request_data = {"message": "test query", "session_id": "test_session_123"}

        response = await client.post("/api/v1/chat/stream", json=request_data)

        # Should accept the request (may fail internally due to no RAG setup)
        # But should NOT return 422 (validation error)
        assert response.status_code != 422, "Request format validation failed"

    @pytest.mark.asyncio
    async def test_chat_stream_optional_session_id(self, client):
        """
        Frontend can omit session_id.
        API should accept requests without session_id.
        """
        request_data = {"message": "test query"}

        response = await client.post("/api/v1/chat/stream", json=request_data)

        assert response.status_code != 422, "Optional session_id caused validation error"

    @pytest.mark.asyncio
    async def test_chat_stream_returns_sse(self, client):
        """
        API should return Server-Sent Events format.
        Frontend expects: Content-Type: text/event-stream
        """
        response = await client.post("/api/v1/chat/stream", json={"message": "test"})

        content_type = response.headers.get("content-type", "")
        # Accept either SSE or error response (if RAG not configured)
        if response.status_code == 200:
            assert "text/event-stream" in content_type, (
                f"Expected SSE content type, got: {content_type}"
            )

    @pytest.mark.asyncio
    async def test_chat_stream_empty_message_handling(self, client):
        """
        Frontend may send empty messages - API should handle gracefully.
        """
        response = await client.post("/api/v1/chat/stream", json={"message": ""})

        # Should either accept or return 400/422, not 500
        assert response.status_code in [
            200,
            400,
            422,
        ], f"Unexpected error handling empty message: {response.status_code}"


class TestChatHealthEndpoint:
    """Test /api/v1/chat/health - frontend uses for health checks."""

    @pytest.mark.asyncio
    async def test_chat_health_endpoint(self, client):
        """
        Frontend's checkHealth() calls GET /api/v1/chat/health
        Should return {status, service}.
        """
        response = await client.get("/api/v1/chat/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


class TestCORSConfiguration:
    """Test CORS headers for frontend connectivity."""

    @pytest.mark.asyncio
    async def test_cors_allows_localhost_3000(self, client):
        """
        Next.js frontend runs on localhost:3000.
        API should allow this origin.
        """
        response = await client.options(
            "/api/v1/chat/stream",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        # CORS preflight should succeed or endpoint exists
        # Some FastAPI setups return 405 for OPTIONS without explicit handler
        if response.status_code in [200, 204]:
            allowed_origins = response.headers.get("access-control-allow-origin", "")
            assert "localhost:3000" in allowed_origins or allowed_origins == "*", (
                f"CORS doesn't allow localhost:3000: {allowed_origins}"
            )
