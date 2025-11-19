"""
Tests for FastAPI endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport

# Import the FastAPI app
import sys
sys.path.insert(0, "services/api")
from app.main import app


@pytest.fixture
async def client():
    """Create test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    """Test health and status endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Root endpoint should return API info."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["name"] == "Docling RAG Agent API"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Health endpoint should return healthy status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_docs_available(self, client):
        """OpenAPI docs should be available."""
        response = await client.get("/docs")

        # Docs page returns HTML
        assert response.status_code == 200
