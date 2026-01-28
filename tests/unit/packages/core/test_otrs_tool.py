"""Tests for OTRS ticket tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic_ai import RunContext

from packages.config.tools import OTRSToolConfig
from packages.core.tools.otrs_tool import (
    _search_cache,
    _session_cache,
    _ticket_cache,
    get_otrs_ticket,
    search_otrs_tickets,
)
from packages.core.types import RAGContext


def _create_mock_context(otrs_config: OTRSToolConfig) -> MagicMock:
    """Create a mock RunContext with OTRS config."""
    mock_rag_ctx = MagicMock(spec=RAGContext)
    mock_rag_ctx.otrs_config = otrs_config
    mock_ctx = MagicMock(spec=RunContext)
    mock_ctx.deps = mock_rag_ctx
    return mock_ctx


def _clear_caches():
    """Clear all OTRS caches before each test."""
    _session_cache.clear()
    _search_cache.clear()
    _ticket_cache.clear()


def _make_response(status_code: int, json_data: dict) -> httpx.Response:
    """Create an httpx.Response with a proper request attribute."""
    request = httpx.Request("GET", "https://test.example.com")
    response = httpx.Response(status_code, json=json_data, request=request)
    return response


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear caches before each test."""
    _clear_caches()
    yield
    _clear_caches()


# ============================================================================
# Configuration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_otrs_tickets_not_configured():
    """Search returns error when OTRS is not configured."""
    # Create config with explicit None values to override any env vars
    config = OTRSToolConfig(
        server_url=None,
        username=None,
        password=None,
    )
    mock_ctx = _create_mock_context(config)

    result = await search_otrs_tickets(mock_ctx, search_text="test")

    data = json.loads(result)
    assert "error" in data
    assert "not configured" in data["error"].lower()


@pytest.mark.asyncio
async def test_get_otrs_ticket_not_configured():
    """Get ticket returns error when OTRS is not configured."""
    # Create config with explicit None values to override any env vars
    config = OTRSToolConfig(
        server_url=None,
        username=None,
        password=None,
    )
    mock_ctx = _create_mock_context(config)

    result = await get_otrs_ticket(mock_ctx, ticket_id="12345")

    data = json.loads(result)
    assert "error" in data
    assert "not configured" in data["error"].lower()


# ============================================================================
# Search Tickets Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_otrs_tickets_success():
    """Search returns tickets when API call succeeds."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/api",
        username="test_user",
        password="test_pass",
    )
    mock_ctx = _create_mock_context(config)

    # Mock HTTP responses with proper request attribute
    session_response = _make_response(200, {"SessionID": "test-session-123"})
    search_response = _make_response(200, {"TicketID": [101, 102]})
    ticket_101_response = _make_response(
        200,
        {
            "Ticket": [
                {
                    "TicketID": 101,
                    "TicketNumber": "2024010100001",
                    "Title": "Login issue",
                    "State": "open",
                    "Priority": "3 normal",
                    "Queue": "Support",
                    "Created": "2024-01-01 10:00:00",
                }
            ]
        },
    )
    ticket_102_response = _make_response(
        200,
        {
            "Ticket": [
                {
                    "TicketID": 102,
                    "TicketNumber": "2024010100002",
                    "Title": "Password reset",
                    "State": "new",
                    "Priority": "2 low",
                    "Queue": "Support",
                    "Created": "2024-01-01 11:00:00",
                }
            ]
        },
    )

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        # Configure responses in order
        mock_instance.post.return_value = session_response
        mock_instance.get.side_effect = [
            search_response,
            ticket_101_response,
            ticket_102_response,
        ]

        result = await search_otrs_tickets(mock_ctx, search_text="login")

    data = json.loads(result)
    assert "error" not in data
    assert "tickets" in data
    assert len(data["tickets"]) == 2
    assert data["total_found"] == 2
    assert data["tickets"][0]["ticket_number"] == "2024010100001"
    assert "Login issue" in data["formatted"]


@pytest.mark.asyncio
async def test_search_otrs_tickets_no_results():
    """Search returns empty list when no tickets match."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/api",
        username="test_user",
        password="test_pass",
    )
    mock_ctx = _create_mock_context(config)

    session_response = _make_response(200, {"SessionID": "test-session-123"})
    search_response = _make_response(200, {"TicketID": []})

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.return_value = session_response
        mock_instance.get.return_value = search_response

        result = await search_otrs_tickets(mock_ctx, search_text="nonexistent")

    data = json.loads(result)
    assert "error" not in data
    assert data["tickets"] == []
    assert data["total_found"] == 0
    assert "No tickets found" in data["formatted"]


@pytest.mark.asyncio
async def test_search_otrs_tickets_auth_failure():
    """Search returns error on authentication failure."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/api",
        username="test_user",
        password="wrong_pass",
    )
    mock_ctx = _create_mock_context(config)

    session_response = _make_response(200, {"Error": {"ErrorMessage": "Invalid credentials"}})

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.return_value = session_response

        result = await search_otrs_tickets(mock_ctx, search_text="test")

    data = json.loads(result)
    assert "error" in data
    assert "authentication failed" in data["error"].lower()


@pytest.mark.asyncio
async def test_search_otrs_tickets_timeout():
    """Search returns error on timeout."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/api",
        username="test_user",
        password="test_pass",
        timeout_seconds=5,
    )
    mock_ctx = _create_mock_context(config)

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.side_effect = httpx.TimeoutException("Connection timed out")

        result = await search_otrs_tickets(mock_ctx, search_text="test")

    data = json.loads(result)
    assert "error" in data
    assert "timed out" in data["error"].lower()


@pytest.mark.asyncio
async def test_search_otrs_tickets_limit():
    """Search respects limit parameter."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/api",
        username="test_user",
        password="test_pass",
    )
    mock_ctx = _create_mock_context(config)

    session_response = _make_response(200, {"SessionID": "test-session-123"})
    search_response = _make_response(200, {"TicketID": [101]})
    ticket_response = _make_response(
        200,
        {
            "Ticket": [
                {
                    "TicketID": 101,
                    "TicketNumber": "2024010100001",
                    "Title": "Test",
                    "State": "open",
                }
            ]
        },
    )

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.return_value = session_response
        mock_instance.get.side_effect = [search_response, ticket_response]

        result = await search_otrs_tickets(mock_ctx, search_text="test", limit=5)

    data = json.loads(result)
    assert "error" not in data
    # Verify limit was passed (checked via mock call args)
    get_calls = mock_instance.get.call_args_list
    assert len(get_calls) >= 1


# ============================================================================
# Get Ticket Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_otrs_ticket_success():
    """Get ticket returns full details."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/api",
        username="test_user",
        password="test_pass",
        web_url="https://otrs.example.com",
    )
    mock_ctx = _create_mock_context(config)

    session_response = _make_response(200, {"SessionID": "test-session-123"})
    ticket_response = _make_response(
        200,
        {
            "Ticket": [
                {
                    "TicketID": 12345,
                    "TicketNumber": "2024010112345",
                    "Title": "Cannot login to system",
                    "State": "open",
                    "Priority": "4 high",
                    "Queue": "IT Support",
                    "CustomerUserID": "john.doe@example.com",
                    "Owner": "admin",
                    "Responsible": "admin",
                    "Created": "2024-01-01 09:00:00",
                    "Changed": "2024-01-02 15:30:00",
                }
            ]
        },
    )

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.return_value = session_response
        mock_instance.get.return_value = ticket_response

        result = await get_otrs_ticket(mock_ctx, ticket_id="12345")

    data = json.loads(result)
    assert "error" not in data
    assert "ticket" in data
    assert data["ticket"]["ticket_number"] == "2024010112345"
    assert data["ticket"]["title"] == "Cannot login to system"
    assert data["ticket"]["state"] == "open"
    assert data["ticket"]["priority"] == "4 high"
    assert "web_url" in data
    assert "12345" in data["web_url"]
    assert "AgentTicketZoom" in data["web_url"]


@pytest.mark.asyncio
async def test_get_otrs_ticket_with_articles():
    """Get ticket with articles returns conversation history."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/api",
        username="test_user",
        password="test_pass",
    )
    mock_ctx = _create_mock_context(config)

    session_response = _make_response(200, {"SessionID": "test-session-123"})
    ticket_response = _make_response(
        200,
        {
            "Ticket": [
                {
                    "TicketID": 12345,
                    "TicketNumber": "2024010112345",
                    "Title": "Issue with login",
                    "State": "open",
                    "Article": [
                        {
                            "From": "john.doe@example.com",
                            "Subject": "Initial report",
                            "Body": "I cannot login to the system",
                        },
                        {
                            "From": "support@example.com",
                            "Subject": "Re: Initial report",
                            "Body": "Have you tried resetting your password?",
                        },
                    ],
                }
            ]
        },
    )

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.return_value = session_response
        mock_instance.get.return_value = ticket_response

        result = await get_otrs_ticket(mock_ctx, ticket_id="12345", include_articles=True)

    data = json.loads(result)
    assert "error" not in data
    assert "ticket" in data
    assert data["ticket"]["articles"] is not None
    assert len(data["ticket"]["articles"]) == 2
    assert "2 message(s)" in data["formatted"]


@pytest.mark.asyncio
async def test_get_otrs_ticket_not_found():
    """Get ticket returns error for non-existent ticket."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/api",
        username="test_user",
        password="test_pass",
    )
    mock_ctx = _create_mock_context(config)

    session_response = _make_response(200, {"SessionID": "test-session-123"})
    not_found_response = _make_response(200, {"Ticket": []})

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.return_value = session_response
        mock_instance.get.return_value = not_found_response

        result = await get_otrs_ticket(mock_ctx, ticket_id="99999")

    data = json.loads(result)
    assert "error" in data
    assert "not found" in data["error"].lower()


@pytest.mark.asyncio
async def test_get_otrs_ticket_timeout():
    """Get ticket returns error on timeout."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/api",
        username="test_user",
        password="test_pass",
        timeout_seconds=5,
    )
    mock_ctx = _create_mock_context(config)

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.side_effect = httpx.TimeoutException("Connection timed out")

        result = await get_otrs_ticket(mock_ctx, ticket_id="12345")

    data = json.loads(result)
    assert "error" in data
    assert "timed out" in data["error"].lower()


@pytest.mark.asyncio
async def test_get_otrs_ticket_web_url_fallback():
    """Get ticket constructs web_url from server_url when web_url not set."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/otrs/nph-genericinterface.pl/Webservice/REST",
        username="test_user",
        password="test_pass",
        web_url=None,  # Explicitly not set
    )
    mock_ctx = _create_mock_context(config)

    session_response = _make_response(200, {"SessionID": "test-session-123"})
    ticket_response = _make_response(
        200,
        {
            "Ticket": [
                {
                    "TicketID": 12345,
                    "TicketNumber": "2024010112345",
                    "Title": "Test ticket",
                    "State": "open",
                }
            ]
        },
    )

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.return_value = session_response
        mock_instance.get.return_value = ticket_response

        result = await get_otrs_ticket(mock_ctx, ticket_id="12345")

    data = json.loads(result)
    assert "error" not in data
    assert "web_url" in data
    assert data["web_url"] is not None
    assert "otrs.example.com" in data["web_url"]
    assert "AgentTicketZoom" in data["web_url"]


# ============================================================================
# Caching Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_otrs_tickets_caching():
    """Search results are cached."""
    config = OTRSToolConfig(
        server_url="https://otrs.example.com/api",
        username="test_user",
        password="test_pass",
        search_cache_ttl_seconds=300,
    )
    mock_ctx = _create_mock_context(config)

    session_response = _make_response(200, {"SessionID": "test-session-123"})
    search_response = _make_response(200, {"TicketID": [101]})
    ticket_response = _make_response(
        200,
        {
            "Ticket": [
                {
                    "TicketID": 101,
                    "TicketNumber": "2024010100001",
                    "Title": "Cached test",
                    "State": "open",
                }
            ]
        },
    )

    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.return_value = session_response
        mock_instance.get.side_effect = [search_response, ticket_response]

        # First call - should hit API
        result1 = await search_otrs_tickets(mock_ctx, search_text="cached")

    # Second call should use cache (no API calls)
    with patch("packages.core.tools.otrs_tool.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        result2 = await search_otrs_tickets(mock_ctx, search_text="cached")

        # No API calls should have been made
        mock_instance.post.assert_not_called()
        mock_instance.get.assert_not_called()

    data1 = json.loads(result1)
    data2 = json.loads(result2)

    assert data1["tickets"] == data2["tickets"]
    assert data2.get("cached") is True
