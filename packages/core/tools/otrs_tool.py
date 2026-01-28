"""OTRS ticket system tool for RAG agent.

This module provides access to OTRS ticket data via the GenericInterface REST API.
Supports searching tickets and retrieving ticket details with optional articles.

Features:
- Ticket search with filters (state, priority, queue, free text)
- Ticket detail retrieval with optional articles/comments
- In-memory caching with configurable TTL
- Session caching for burst queries (30s)
- Comprehensive error handling with JSON responses
- PydanticAI RunContext[RAGContext] dependency injection pattern

Environment Variables:
    OTRS_SERVER_URL: REST API endpoint (required)
    OTRS_USERNAME: API username (required)
    OTRS_PASSWORD: API password (required)
    OTRS_WEB_URL: Web interface URL for iframe viewing (optional)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from packages.core.types import RAGContext

logger = logging.getLogger(__name__)

# In-memory caches
_ticket_cache: dict[str, tuple[dict, datetime]] = {}
_search_cache: dict[str, tuple[list, datetime]] = {}
_session_cache: dict[str, tuple[str, datetime]] = {}  # server_url -> (session_id, timestamp)

# Session cache TTL (short to handle session expiry gracefully)
_SESSION_CACHE_TTL_SECONDS = 30


class OTRSAttachment(BaseModel):
    """OTRS article attachment."""

    attachment_id: str = Field(description="Attachment ID")
    filename: str = Field(description="Original filename")
    content_type: str = Field(description="MIME content type")
    file_size: Optional[int] = Field(None, description="File size in bytes")


class OTRSArticle(BaseModel):
    """OTRS ticket article (email/note/phone entry in the conversation thread)."""

    article_id: str = Field(description="Article ID")
    from_address: Optional[str] = Field(None, description="Sender email/name")
    to_addresses: list[str] = Field(default_factory=list, description="Recipient addresses")
    cc_addresses: list[str] = Field(default_factory=list, description="CC addresses")
    subject: Optional[str] = Field(None, description="Article subject")
    body: str = Field(default="", description="Article body content")
    body_type: str = Field(
        default="text/plain", description="Body MIME type (text/plain or text/html)"
    )
    sender_type: str = Field(default="agent", description="Sender type: customer, agent, system")
    article_type: Optional[str] = Field(
        None, description="Article type: email-external, email-internal, note-internal, phone, etc."
    )
    created: Optional[str] = Field(None, description="Creation timestamp")
    attachments: list[OTRSAttachment] = Field(default_factory=list, description="File attachments")


class OTRSTicketSummary(BaseModel):
    """OTRS ticket summary for search results."""

    ticket_id: str = Field(description="Internal ticket ID (numeric)")
    ticket_number: str = Field(description="Display ticket number (e.g., 2024010112345)")
    title: Optional[str] = Field(None, description="Ticket title/subject")
    state: Optional[str] = Field(None, description="Ticket state (open, new, pending, closed)")
    priority: Optional[str] = Field(None, description="Ticket priority (1-5)")
    queue: Optional[str] = Field(None, description="Ticket queue name")
    created: Optional[str] = Field(None, description="Creation timestamp")
    web_url: Optional[str] = Field(None, description="URL to view ticket in OTRS web interface")


class OTRSTicketDetail(BaseModel):
    """OTRS ticket full details."""

    ticket_id: str
    ticket_number: str
    title: Optional[str] = None
    state: Optional[str] = None
    priority: Optional[str] = None
    queue: Optional[str] = None
    customer_user: Optional[str] = None
    customer_email: Optional[str] = None
    owner: Optional[str] = None
    responsible: Optional[str] = None
    created: Optional[str] = None
    changed: Optional[str] = None
    articles: Optional[list[OTRSArticle]] = None


def _parse_articles(raw_articles: list[dict]) -> list[OTRSArticle]:
    """Parse raw OTRS article data into structured OTRSArticle objects.

    Args:
        raw_articles: List of article dicts from OTRS API

    Returns:
        List of OTRSArticle objects, sorted chronologically (oldest first)
    """
    articles = []
    for raw in raw_articles:
        # Parse To addresses (may be comma-separated string or list)
        to_raw = raw.get("To", "")
        to_addresses = []
        if isinstance(to_raw, str) and to_raw:
            to_addresses = [addr.strip() for addr in to_raw.split(",") if addr.strip()]
        elif isinstance(to_raw, list):
            to_addresses = to_raw

        # Parse Cc addresses
        cc_raw = raw.get("Cc", "")
        cc_addresses = []
        if isinstance(cc_raw, str) and cc_raw:
            cc_addresses = [addr.strip() for addr in cc_raw.split(",") if addr.strip()]
        elif isinstance(cc_raw, list):
            cc_addresses = cc_raw

        # Parse attachments
        attachments = []
        raw_attachments = raw.get("Attachment", [])
        if isinstance(raw_attachments, dict):
            raw_attachments = [raw_attachments]
        for att in raw_attachments:
            attachments.append(
                OTRSAttachment(
                    attachment_id=str(att.get("AttachmentID", att.get("FileID", ""))),
                    filename=att.get("Filename", att.get("FileName", "unknown")),
                    content_type=att.get("ContentType", "application/octet-stream"),
                    file_size=att.get("FilesizeRaw") or att.get("Filesize"),
                )
            )

        # Determine body type - prefer plain text, fall back to HTML
        body = raw.get("Body", "")
        body_type = "text/plain"
        if raw.get("ContentType"):
            body_type = raw.get("ContentType", "text/plain")
        elif raw.get("MimeType"):
            body_type = raw.get("MimeType", "text/plain")

        # Map sender type - OTRS uses SenderType field
        sender_type = raw.get("SenderType", "agent").lower()
        if sender_type not in ("customer", "agent", "system"):
            sender_type = "agent"

        article = OTRSArticle(
            article_id=str(raw.get("ArticleID", "")),
            from_address=raw.get("From"),
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            subject=raw.get("Subject"),
            body=body,
            body_type=body_type,
            sender_type=sender_type,
            article_type=raw.get("ArticleType") or raw.get("CommunicationChannel"),
            created=raw.get("Created") or raw.get("CreateTime"),
            attachments=attachments,
        )
        articles.append(article)

    # Sort by created timestamp (oldest first for thread view)
    articles.sort(key=lambda a: a.created or "")

    return articles


async def _get_session_id(config) -> str:
    """Get or create OTRS session ID with caching.

    OTRS uses session-based authentication. Sessions typically have a 2-hour timeout.
    We cache the session ID for 30 seconds to handle burst queries efficiently
    while reconnecting automatically if the session expires.

    Args:
        config: OTRSToolConfig with server_url, username, password

    Returns:
        Valid SessionID string

    Raises:
        ValueError: If authentication fails or server unreachable
    """
    cache_key = config.server_url

    # Check session cache (30s TTL)
    if cache_key in _session_cache:
        session_id, cached_time = _session_cache[cache_key]
        if datetime.now() - cached_time < timedelta(seconds=_SESSION_CACHE_TTL_SECONDS):
            logger.debug("OTRS session cache hit")
            return session_id

    # Create new session via POST to /Session endpoint
    session_url = f"{config.server_url.rstrip('/')}/Session"

    async with httpx.AsyncClient(
        timeout=config.timeout_seconds, verify=config.verify_ssl
    ) as client:
        response = await client.post(
            session_url,
            json={
                "UserLogin": config.username,
                "Password": config.password,
            },
        )
        response.raise_for_status()
        data = response.json()

    session_id = data.get("SessionID")
    if not session_id:
        error_msg = data.get("Error", {}).get("ErrorMessage", "Unknown error")
        raise ValueError(f"OTRS authentication failed: {error_msg}")

    # Cache session
    _session_cache[cache_key] = (session_id, datetime.now())
    logger.info("OTRS session created successfully")

    return session_id


def _clear_session_cache(config) -> None:
    """Clear cached session for a server (on auth failure)."""
    cache_key = config.server_url
    if cache_key in _session_cache:
        del _session_cache[cache_key]
        logger.debug("OTRS session cache cleared")


async def _lookup_ticket_id_by_number(config, session_id: str, ticket_number: str) -> Optional[str]:
    """Lookup internal TicketID by TicketNumber.

    OTRS has two identifiers:
    - TicketID: Internal numeric ID (e.g., 9022)
    - TicketNumber: Formatted number shown to users (e.g., 2025121810000021)

    The REST API /Ticket/{id} typically expects TicketID, not TicketNumber.
    This helper searches for a ticket by its TicketNumber and returns the TicketID.

    Args:
        config: OTRSToolConfig with server settings
        session_id: Valid OTRS session ID
        ticket_number: The TicketNumber to lookup

    Returns:
        The internal TicketID if found, None otherwise
    """
    try:
        # Search for ticket by TicketNumber
        search_url = f"{config.server_url.rstrip('/')}/Ticket"
        search_params = {
            "SessionID": session_id,
            "TicketNumber": ticket_number,
            "Limit": 1,
        }

        async with httpx.AsyncClient(
            timeout=config.timeout_seconds, verify=config.verify_ssl
        ) as client:
            response = await client.get(search_url, params=search_params)
            response.raise_for_status()
            data = response.json()

        ticket_ids = data.get("TicketID", [])
        if isinstance(ticket_ids, list) and ticket_ids:
            logger.info(f"Found TicketID {ticket_ids[0]} for TicketNumber {ticket_number}")
            return str(ticket_ids[0])
        elif isinstance(ticket_ids, (int, str)) and ticket_ids:
            logger.info(f"Found TicketID {ticket_ids} for TicketNumber {ticket_number}")
            return str(ticket_ids)

        return None

    except Exception as e:
        logger.warning(f"Failed to lookup TicketNumber {ticket_number}: {e}")
        return None


async def search_otrs_tickets(
    ctx: RunContext[RAGContext],
    search_text: Optional[str] = None,
    state: Optional[str] = None,
    priority: Optional[str] = None,
    queue: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Search OTRS tickets with optional filters.

    This tool searches the OTRS ticket system for tickets matching the given criteria.
    Use it when users ask about tickets, incidents, support requests, or issues.

    Args:
        ctx: RAG context with agent dependencies (automatically injected)
        search_text: Free-text search in ticket title and body (optional)
        state: Filter by ticket state - "open", "new", "pending reminder",
               "pending auto close", "closed successful", "closed unsuccessful" (optional)
        priority: Filter by priority - "1 very low", "2 low", "3 normal",
                  "4 high", "5 very high" (optional)
        queue: Filter by queue name, e.g., "Support", "IT", "Sales" (optional)
        limit: Maximum number of tickets to return (default: 20, max: 100)

    Returns:
        JSON string with:
        - formatted: Human-readable summary
        - tickets: List of ticket summaries with id, number, title, state
        - total_found: Number of tickets found

    Example queries:
        - "Show me open high priority tickets" -> state="open", priority="4 high"
        - "Find tickets about login problems" -> search_text="login"
        - "List tickets in Support queue" -> queue="Support"
    """
    try:
        config = ctx.deps.otrs_config

        if not config.is_configured:
            return json.dumps(
                {
                    "error": "OTRS not configured. Please set OTRS_SERVER_URL, OTRS_USERNAME, and OTRS_PASSWORD environment variables.",
                    "formatted": "OTRS integration is not configured.",
                }
            )

        # Validate and cap limit
        limit = min(max(1, limit), 100)

        # Build cache key from search parameters
        cache_key = f"search:{search_text}:{state}:{priority}:{queue}:{limit}"

        # Check search cache
        if cache_key in _search_cache:
            cached_data, cached_time = _search_cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=config.search_cache_ttl_seconds):
                logger.info(f"OTRS search cache hit for: {cache_key[:50]}...")
                return json.dumps(
                    {
                        "formatted": f"Found {len(cached_data)} tickets (cached)",
                        "tickets": cached_data,
                        "total_found": len(cached_data),
                        "cached": True,
                    },
                    ensure_ascii=False,
                    default=str,
                )

        # Get session
        try:
            session_id = await _get_session_id(config)
        except ValueError as e:
            return json.dumps({"error": str(e), "formatted": f"Authentication failed: {e}"})

        # Build search request
        # OTRS TicketSearch expects specific parameter names
        search_url = f"{config.server_url.rstrip('/')}/Ticket"
        search_params: dict = {
            "SessionID": session_id,
            "Limit": limit,
        }

        # Add filters
        if search_text:
            # Search in title using wildcard pattern
            search_params["Title"] = f"*{search_text}*"
        if state:
            search_params["States"] = [state]
        if priority:
            search_params["Priorities"] = [priority]
        if queue:
            search_params["Queues"] = [queue]

        # Execute search
        async with httpx.AsyncClient(
            timeout=config.timeout_seconds, verify=config.verify_ssl
        ) as client:
            response = await client.get(search_url, params=search_params)

            # Handle auth failure - clear cache and retry once
            if response.status_code == 401:
                _clear_session_cache(config)
                session_id = await _get_session_id(config)
                search_params["SessionID"] = session_id
                response = await client.get(search_url, params=search_params)

            response.raise_for_status()
            data = response.json()

        # Extract ticket IDs from response
        ticket_ids = data.get("TicketID", [])
        if not isinstance(ticket_ids, list):
            ticket_ids = [ticket_ids] if ticket_ids else []

        if not ticket_ids:
            return json.dumps(
                {
                    "formatted": "No tickets found matching your criteria.",
                    "tickets": [],
                    "total_found": 0,
                }
            )

        # Fetch basic info for each ticket (batch would be better but OTRS API limits)
        tickets = []
        for tid in ticket_ids[:limit]:
            try:
                ticket_url = f"{config.server_url.rstrip('/')}/Ticket/{tid}"
                async with httpx.AsyncClient(
                    timeout=config.timeout_seconds, verify=config.verify_ssl
                ) as client:
                    resp = await client.get(ticket_url, params={"SessionID": session_id})
                    resp.raise_for_status()
                    ticket_data = resp.json().get("Ticket", [{}])
                    if isinstance(ticket_data, list) and ticket_data:
                        ticket_data = ticket_data[0]
                    elif not ticket_data:
                        continue

                # Build web URL for this ticket
                web_url = None
                if config.effective_web_url:
                    web_url = (
                        f"{config.effective_web_url}/otrs/index.pl?"
                        f"Action=AgentTicketZoom;TicketID={tid}"
                    )

                summary = OTRSTicketSummary(
                    ticket_id=str(tid),
                    ticket_number=ticket_data.get("TicketNumber", str(tid)),
                    title=ticket_data.get("Title"),
                    state=ticket_data.get("State"),
                    priority=ticket_data.get("Priority"),
                    queue=ticket_data.get("Queue"),
                    created=ticket_data.get("Created"),
                    web_url=web_url,
                )
                tickets.append(summary.model_dump())
            except Exception as e:
                logger.warning(f"Failed to fetch ticket {tid}: {e}")
                continue

        # Cache results
        _search_cache[cache_key] = (tickets, datetime.now())

        # Format human-readable response
        formatted_lines = [f"Found {len(tickets)} ticket(s):"]
        for t in tickets:
            state_emoji = {"open": "🟢", "new": "🔵", "pending": "🟡", "closed": "⚫"}.get(
                (t.get("state") or "").split()[0].lower(), "⚪"
            )
            formatted_lines.append(
                f"{state_emoji} #{t['ticket_number']} [{t.get('state', 'N/A')}]: {t.get('title', 'No title')}"
            )

        logger.info(f"OTRS search returned {len(tickets)} tickets")

        return json.dumps(
            {
                "formatted": "\n".join(formatted_lines),
                "tickets": tickets,
                "total_found": len(tickets),
            },
            ensure_ascii=False,
            default=str,
        )

    except httpx.HTTPStatusError as e:
        error_msg = f"OTRS API error: HTTP {e.response.status_code}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "formatted": error_msg})

    except httpx.TimeoutException:
        error_msg = "OTRS API request timed out. Please try again."
        logger.error("OTRS search timeout")
        return json.dumps({"error": error_msg, "formatted": error_msg})

    except Exception as e:
        error_msg = f"OTRS search failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"error": error_msg, "formatted": error_msg})


async def get_otrs_ticket(
    ctx: RunContext[RAGContext],
    ticket_id: str,
    include_articles: bool = False,
) -> str:
    """Get detailed information about a specific OTRS ticket.

    This tool retrieves full details about a ticket including metadata and optionally
    the conversation history (articles). Use it when users want to know more about
    a specific ticket they found or mentioned.

    Args:
        ctx: RAG context with agent dependencies (automatically injected)
        ticket_id: The ticket ID (numeric) or ticket number to retrieve
        include_articles: Whether to include ticket articles/comments history (default: False)
                         Set to True when user wants to see the full conversation

    Returns:
        JSON string with:
        - formatted: Human-readable ticket summary
        - ticket: Full ticket details object
        - web_url: URL to view ticket in OTRS web interface (for iframe viewing)
        - raw_api_response: Original API response for debugging

    Example queries:
        - "Show me ticket 12345" -> ticket_id="12345"
        - "What's the status of ticket 2024010112345?" -> ticket_id="2024010112345"
        - "Show full history of ticket 100" -> ticket_id="100", include_articles=True
    """
    try:
        config = ctx.deps.otrs_config

        if not config.is_configured:
            return json.dumps(
                {
                    "error": "OTRS not configured. Please set OTRS_SERVER_URL, OTRS_USERNAME, and OTRS_PASSWORD environment variables.",
                    "formatted": "OTRS integration is not configured.",
                }
            )

        # Build cache key
        cache_key = f"ticket:{ticket_id}:{include_articles}"

        # Check ticket cache
        if cache_key in _ticket_cache:
            cached_data, cached_time = _ticket_cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=config.cache_ttl_seconds):
                logger.info(f"OTRS ticket cache hit for: {ticket_id}")
                cached_data["cached"] = True
                return json.dumps(cached_data, ensure_ascii=False, default=str)

        # Get session
        try:
            session_id = await _get_session_id(config)
        except ValueError as e:
            return json.dumps({"error": str(e), "formatted": f"Authentication failed: {e}"})

        # Fetch ticket details - try with provided ID first
        actual_ticket_id = ticket_id
        ticket_url = f"{config.server_url.rstrip('/')}/Ticket/{actual_ticket_id}"
        params: dict = {"SessionID": session_id}

        if include_articles:
            params["AllArticles"] = 1

        async with httpx.AsyncClient(
            timeout=config.timeout_seconds, verify=config.verify_ssl
        ) as client:
            response = await client.get(ticket_url, params=params)

            # Handle auth failure - clear cache and retry once
            if response.status_code == 401:
                _clear_session_cache(config)
                session_id = await _get_session_id(config)
                params["SessionID"] = session_id
                response = await client.get(ticket_url, params=params)

            response.raise_for_status()
            data = response.json()

        # Extract ticket from response
        ticket_list = data.get("Ticket", [])

        # If not found and ID looks like a TicketNumber (long format), try lookup
        if not ticket_list and len(ticket_id) >= 10:
            logger.info(f"Direct fetch failed, trying TicketNumber lookup for: {ticket_id}")
            real_ticket_id = await _lookup_ticket_id_by_number(config, session_id, ticket_id)

            if real_ticket_id and real_ticket_id != ticket_id:
                actual_ticket_id = real_ticket_id
                ticket_url = f"{config.server_url.rstrip('/')}/Ticket/{actual_ticket_id}"
                params["SessionID"] = session_id

                async with httpx.AsyncClient(
                    timeout=config.timeout_seconds, verify=config.verify_ssl
                ) as client:
                    response = await client.get(ticket_url, params=params)
                    response.raise_for_status()
                    data = response.json()

                ticket_list = data.get("Ticket", [])

        if not ticket_list:
            return json.dumps(
                {
                    "error": f"Ticket {ticket_id} not found",
                    "formatted": f"Ticket {ticket_id} was not found in OTRS.",
                }
            )

        ticket_data = ticket_list[0] if isinstance(ticket_list, list) else ticket_list

        # Parse articles if requested
        parsed_articles = None
        if include_articles:
            raw_articles = ticket_data.get("Article", [])
            if isinstance(raw_articles, dict):
                raw_articles = [raw_articles]
            if raw_articles:
                parsed_articles = _parse_articles(raw_articles)

        # Parse into structured model
        detail = OTRSTicketDetail(
            ticket_id=str(ticket_data.get("TicketID", ticket_id)),
            ticket_number=ticket_data.get("TicketNumber", str(ticket_id)),
            title=ticket_data.get("Title"),
            state=ticket_data.get("State"),
            priority=ticket_data.get("Priority"),
            queue=ticket_data.get("Queue"),
            customer_user=ticket_data.get("CustomerUserID"),
            customer_email=ticket_data.get("CustomerID"),  # Often contains email
            owner=ticket_data.get("Owner"),
            responsible=ticket_data.get("Responsible"),
            created=ticket_data.get("Created"),
            changed=ticket_data.get("Changed"),
            articles=parsed_articles,
        )

        # Build web URL for iframe viewing
        web_url = None
        if config.effective_web_url:
            web_url = (
                f"{config.effective_web_url}/otrs/index.pl?"
                f"Action=AgentTicketZoom;TicketID={detail.ticket_id}"
            )

        # Format human-readable response
        state_emoji = {"open": "🟢", "new": "🔵", "pending": "🟡", "closed": "⚫"}.get(
            (detail.state or "").split()[0].lower(), "⚪"
        )

        formatted_lines = [
            f"{state_emoji} Ticket #{detail.ticket_number}",
            "",
            f"**Title:** {detail.title or 'N/A'}",
            f"**State:** {detail.state or 'N/A'}",
            f"**Priority:** {detail.priority or 'N/A'}",
            f"**Queue:** {detail.queue or 'N/A'}",
            f"**Owner:** {detail.owner or 'N/A'}",
            f"**Customer:** {detail.customer_user or 'N/A'}",
            f"**Created:** {detail.created or 'N/A'}",
            f"**Last Updated:** {detail.changed or 'N/A'}",
        ]

        if include_articles and detail.articles:
            formatted_lines.append("")
            formatted_lines.append(f"**Articles:** {len(detail.articles)} message(s)")
            for i, article in enumerate(detail.articles[:5], 1):  # Show first 5
                sender_icon = "👤" if article.sender_type == "customer" else "🧑‍💼"
                from_addr = article.from_address or "Unknown"
                subject = article.subject or "No subject"
                formatted_lines.append(f"  {i}. {sender_icon} {from_addr} - {subject}")
            if len(detail.articles) > 5:
                formatted_lines.append(f"  ... and {len(detail.articles) - 5} more")

        result = {
            "formatted": "\n".join(formatted_lines),
            "ticket": detail.model_dump(),
            "web_url": web_url,
            "raw_api_response": ticket_data,
        }

        # Cache result
        _ticket_cache[cache_key] = (result, datetime.now())

        logger.info(f"OTRS ticket {ticket_id} fetched successfully")

        return json.dumps(result, ensure_ascii=False, default=str)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            error_msg = f"Ticket {ticket_id} not found"
        else:
            error_msg = f"OTRS API error: HTTP {e.response.status_code}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "formatted": error_msg})

    except httpx.TimeoutException:
        error_msg = f"OTRS API request timed out for ticket {ticket_id}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "formatted": error_msg})

    except Exception as e:
        error_msg = f"Failed to fetch ticket {ticket_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"error": error_msg, "formatted": error_msg})


# Export for registration
__all__ = [
    "search_otrs_tickets",
    "get_otrs_ticket",
    "OTRSArticle",
    "OTRSAttachment",
    "OTRSTicketDetail",
    "OTRSTicketSummary",
]
