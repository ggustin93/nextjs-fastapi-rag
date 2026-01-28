"""Tickets API router for OTRS ticket data.

This module provides REST endpoints to access OTRS ticket data
including articles for email thread visualization in the frontend.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])

# In-memory caches
_ticket_cache: dict[str, tuple[dict, datetime]] = {}
_session_cache: dict[str, tuple[str, datetime]] = {}

TICKET_CACHE_TTL_SECONDS = 300  # 5 minutes for detailed ticket data
SESSION_CACHE_TTL_SECONDS = 30  # 30 seconds for OTRS session


class TicketAttachment(BaseModel):
    """OTRS article attachment."""

    attachment_id: str
    filename: str
    content_type: str
    file_size: int | None = None


class TicketArticle(BaseModel):
    """OTRS ticket article (email/note in conversation thread)."""

    article_id: str
    from_address: str | None = None
    to_addresses: list[str] = Field(default_factory=list)
    cc_addresses: list[str] = Field(default_factory=list)
    subject: str | None = None
    body: str = ""
    body_type: str = "text/plain"
    sender_type: str = "agent"  # customer, agent, system
    article_type: str | None = None
    created: str | None = None
    attachments: list[TicketAttachment] = Field(default_factory=list)


class TicketDetailResponse(BaseModel):
    """Response model for ticket detail endpoint."""

    ticket_id: str
    ticket_number: str
    title: str | None = None
    state: str | None = None
    priority: str | None = None
    queue: str | None = None
    customer_user: str | None = None
    customer_email: str | None = None
    owner: str | None = None
    responsible: str | None = None
    created: str | None = None
    changed: str | None = None
    articles: list[TicketArticle] = Field(default_factory=list)
    web_url: str | None = None


async def _lookup_ticket_id_by_number(config, session_id: str, ticket_number: str) -> str | None:
    """Lookup internal TicketID by TicketNumber.

    OTRS uses two identifiers:
    - TicketID: Internal numeric ID (e.g., 9022) - used by API
    - TicketNumber: Formatted number (e.g., 2025121810000021) - shown to users

    This function converts TicketNumber to TicketID.
    """
    try:
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
            if response.status_code != 200:
                return None
            data = response.json()

        ticket_ids = data.get("TicketID", [])
        if isinstance(ticket_ids, list) and ticket_ids:
            logger.info(f"Resolved TicketNumber {ticket_number} → TicketID {ticket_ids[0]}")
            return str(ticket_ids[0])
        return None
    except Exception as e:
        logger.warning(f"Failed to lookup TicketNumber {ticket_number}: {e}")
        return None


async def _get_otrs_session() -> str:
    """Get or create OTRS session ID with caching."""
    config = settings.otrs

    if not config.is_configured:
        raise HTTPException(status_code=503, detail="OTRS integration not configured")

    cache_key = config.server_url

    # Check session cache
    if cache_key in _session_cache:
        session_id, cached_time = _session_cache[cache_key]
        if datetime.now() - cached_time < timedelta(seconds=SESSION_CACHE_TTL_SECONDS):
            return session_id

    # Create new session
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
        raise HTTPException(status_code=401, detail=f"OTRS authentication failed: {error_msg}")

    # Cache session
    _session_cache[cache_key] = (session_id, datetime.now())
    logger.info("OTRS session created successfully")

    return session_id


def _parse_articles(raw_articles: list[dict]) -> list[TicketArticle]:
    """Parse raw OTRS article data into TicketArticle objects."""
    articles = []

    for raw in raw_articles:
        # Parse To addresses
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
                TicketAttachment(
                    attachment_id=str(att.get("AttachmentID", att.get("FileID", ""))),
                    filename=att.get("Filename", att.get("FileName", "unknown")),
                    content_type=att.get("ContentType", "application/octet-stream"),
                    file_size=att.get("FilesizeRaw") or att.get("Filesize"),
                )
            )

        # Determine body type
        body = raw.get("Body", "")
        body_type = raw.get("ContentType") or raw.get("MimeType") or "text/plain"

        # Map sender type
        sender_type = raw.get("SenderType", "agent").lower()
        if sender_type not in ("customer", "agent", "system"):
            sender_type = "agent"

        article = TicketArticle(
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

    # Sort by created timestamp (oldest first)
    articles.sort(key=lambda a: a.created or "")

    return articles


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(ticket_id: str) -> TicketDetailResponse:
    """Get detailed ticket information including articles.

    This endpoint fetches full ticket details from OTRS including
    all articles (emails, notes, phone calls) for thread visualization.

    Args:
        ticket_id: OTRS ticket ID (numeric)

    Returns:
        TicketDetailResponse with ticket metadata and articles

    Raises:
        HTTPException: 404 if ticket not found, 502 if API error
    """
    try:
        config = settings.otrs

        if not config.is_configured:
            raise HTTPException(status_code=503, detail="OTRS integration not configured")

        # Check cache
        cache_key = f"ticket:{ticket_id}"
        if cache_key in _ticket_cache:
            cached_data, cached_time = _ticket_cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=TICKET_CACHE_TTL_SECONDS):
                logger.info(f"Ticket cache hit for {ticket_id}")
                return TicketDetailResponse(**cached_data)

        # Get session
        session_id = await _get_otrs_session()

        # Fetch ticket with articles
        ticket_url = f"{config.server_url.rstrip('/')}/Ticket/{ticket_id}"
        params: dict[str, Any] = {
            "SessionID": session_id,
            "AllArticles": 1,
        }

        async with httpx.AsyncClient(
            timeout=config.timeout_seconds, verify=config.verify_ssl
        ) as client:
            response = await client.get(ticket_url, params=params)

            # Handle auth failure - clear cache and retry
            if response.status_code == 401:
                _session_cache.pop(config.server_url, None)
                session_id = await _get_otrs_session()
                params["SessionID"] = session_id
                response = await client.get(ticket_url, params=params)

            if response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

            response.raise_for_status()
            data = response.json()

        # Extract ticket data
        ticket_list = data.get("Ticket", [])

        # If not found and ID looks like a TicketNumber (10+ digits), try lookup
        if not ticket_list and len(ticket_id) >= 10:
            logger.info(f"Ticket {ticket_id} not found directly, trying TicketNumber lookup...")
            real_ticket_id = await _lookup_ticket_id_by_number(config, session_id, ticket_id)

            if real_ticket_id and real_ticket_id != ticket_id:
                # Fetch again with real TicketID
                ticket_url = f"{config.server_url.rstrip('/')}/Ticket/{real_ticket_id}"
                async with httpx.AsyncClient(
                    timeout=config.timeout_seconds, verify=config.verify_ssl
                ) as client:
                    response = await client.get(ticket_url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        ticket_list = data.get("Ticket", [])

        if not ticket_list:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

        ticket_data = ticket_list[0] if isinstance(ticket_list, list) else ticket_list

        # Parse articles
        raw_articles = ticket_data.get("Article", [])
        if isinstance(raw_articles, dict):
            raw_articles = [raw_articles]
        articles = _parse_articles(raw_articles) if raw_articles else []

        # Build web URL
        web_url = None
        if config.effective_web_url:
            web_url = (
                f"{config.effective_web_url}/otrs/index.pl?"
                f"Action=AgentTicketZoom;TicketID={ticket_data.get('TicketID', ticket_id)}"
            )

        # Build response
        response_data = {
            "ticket_id": str(ticket_data.get("TicketID", ticket_id)),
            "ticket_number": ticket_data.get("TicketNumber", str(ticket_id)),
            "title": ticket_data.get("Title"),
            "state": ticket_data.get("State"),
            "priority": ticket_data.get("Priority"),
            "queue": ticket_data.get("Queue"),
            "customer_user": ticket_data.get("CustomerUserID"),
            "customer_email": ticket_data.get("CustomerID"),
            "owner": ticket_data.get("Owner"),
            "responsible": ticket_data.get("Responsible"),
            "created": ticket_data.get("Created"),
            "changed": ticket_data.get("Changed"),
            "articles": [a.model_dump() for a in articles],
            "web_url": web_url,
        }

        # Cache result
        _ticket_cache[cache_key] = (response_data, datetime.now())
        logger.info(f"Ticket {ticket_id} fetched with {len(articles)} articles")

        return TicketDetailResponse(**response_data)

    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"OTRS API error: HTTP {e.response.status_code}")
        raise HTTPException(
            status_code=502,
            detail=f"OTRS API error: {e.response.status_code}",
        )
    except httpx.TimeoutException:
        logger.error(f"OTRS API timeout for ticket {ticket_id}")
        raise HTTPException(
            status_code=504,
            detail=f"OTRS API timeout for ticket {ticket_id}",
        )
    except Exception as e:
        logger.error(f"Ticket fetch error for {ticket_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching ticket {ticket_id}: {str(e)}",
        )
