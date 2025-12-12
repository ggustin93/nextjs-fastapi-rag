"""KISS tests for OSIRIS worksite tool and API endpoint.

Simple tests to verify the tool works end-to-end.

Run: pytest tests/unit/packages/test_osiris_tool.py -v
"""

import os
import sys

# Add project paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "services", "api")
)

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Test data: Real OSIRIS API response structure
MOCK_OSIRIS_RESPONSE = {
    "type": "Feature",
    "geometry": {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [4.3517, 50.8503],  # Brussels center
                    [4.3520, 50.8503],
                    [4.3520, 50.8506],
                    [4.3517, 50.8506],
                    [4.3517, 50.8503],
                ]
            ]
        ],
    },
    "properties": {
        "ID_WS": "12345",
        "STATUS_FR": "En cours",
        "STATUS_NL": "In uitvoering",
        "LABEL_FR": "Rénovation Rue de la Loi",
        "LABEL_NL": "Renovatie Wetstraat",
        "PGM_START_DATE": "2024-01-15",
        "PGM_END_DATE": "2024-06-30",
        "ROAD_IMPL_FR": "Rue de la Loi",
        "ROAD_IMPL_NL": "Wetstraat",
    },
}


class TestOsirisWorksiteTool:
    """Test the OSIRIS worksite tool function."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock RAG context with OSIRIS config."""
        ctx = MagicMock()
        ctx.deps = MagicMock()
        ctx.deps.osiris_config = MagicMock()
        ctx.deps.osiris_config.base_url = "https://api.osiris.brussels/worksites"
        ctx.deps.osiris_config.username = "test"
        ctx.deps.osiris_config.password = "test"
        ctx.deps.osiris_config.timeout_seconds = 30
        ctx.deps.osiris_config.cache_ttl_seconds = 900
        return ctx

    @pytest.mark.asyncio
    async def test_get_worksite_info_success(self, mock_context):
        """Test successful worksite data retrieval."""
        from packages.core.tools.osiris_worksite import get_worksite_info

        with patch("packages.core.tools.osiris_worksite.httpx.AsyncClient") as mock_client:
            # Setup mock response - json() returns dict directly (sync method in httpx)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = MOCK_OSIRIS_RESPONSE

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            # Call the tool
            result = await get_worksite_info(mock_context, "12345", "fr")

            # Verify result
            assert "Worksite 12345" in result
            assert "En cours" in result
            assert "Rue de la Loi" in result

    @pytest.mark.asyncio
    async def test_get_worksite_info_not_found(self, mock_context):
        """Test worksite not found response."""
        import httpx

        from packages.core.tools.osiris_worksite import get_worksite_info

        with patch("packages.core.tools.osiris_worksite.httpx.AsyncClient") as mock_client:
            # Setup 404 response
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            # Call the tool
            result = await get_worksite_info(mock_context, "99999", "fr")

            # Verify not found message
            assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_worksite_info_bilingual(self, mock_context):
        """Test bilingual support (NL)."""
        from packages.core.tools.osiris_worksite import get_worksite_info

        with patch("packages.core.tools.osiris_worksite.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = MOCK_OSIRIS_RESPONSE

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            # Call with Dutch
            result = await get_worksite_info(mock_context, "12345", "nl")

            # Verify Dutch content
            assert "In uitvoering" in result
            assert "Wetstraat" in result


class TestWorksitesApiEndpoint:
    """Test the /worksites API endpoint."""

    @pytest.mark.asyncio
    async def test_geometry_endpoint_success(self):
        """Test successful geometry retrieval from API."""
        try:
            from app.api.worksites import router
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("FastAPI not available or import path issue")

        app = FastAPI()
        app.include_router(router)

        with patch("app.api.worksites.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = MOCK_OSIRIS_RESPONSE

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            client = TestClient(app)
            response = client.get("/worksites/12345/geometry")

            assert response.status_code == 200
            data = response.json()
            assert data["id_ws"] == "12345"
            assert data["geometry"]["type"] == "MultiPolygon"
            assert data["label_fr"] == "Rénovation Rue de la Loi"


# Run tests: pytest tests/unit/packages/test_osiris_tool.py -v
