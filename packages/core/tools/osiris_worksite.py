"""OSIRIS Brussels worksite data tool for RAG agent.

This module provides access to Brussels worksite information from the OSIRIS API.
Supports querying by worksite ID (ID_WS) with multilingual support (FR/NL).

Features:
- Worksite information retrieval by ID
- In-memory caching (15-minute TTL)
- Comprehensive error handling
- PydanticAI RunContext[RAGContext] pattern
- Basic authentication with configurable credentials
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from packages.core.types import RAGContext

logger = logging.getLogger(__name__)

# In-memory cache (use Redis for production)
_worksite_cache: dict[str, tuple[dict, datetime]] = {}


class WorksiteData(BaseModel):
    """OSIRIS worksite response model.

    Contains worksite information including status, dates, and location.
    """

    id_ws: str = Field(description="Worksite ID")
    status_fr: Optional[str] = Field(None, description="Status in French")
    status_nl: Optional[str] = Field(None, description="Status in Dutch")
    label_fr: Optional[str] = Field(None, description="Label/description in French")
    label_nl: Optional[str] = Field(None, description="Label/description in Dutch")
    pgm_start_date: Optional[str] = Field(None, description="Planned start date")
    pgm_end_date: Optional[str] = Field(None, description="Planned end date")
    road_impl_fr: Optional[str] = Field(None, description="Roads affected (French)")
    road_impl_nl: Optional[str] = Field(None, description="Roads affected (Dutch)")
    geometry_type: Optional[str] = Field(None, description="Geometry type (e.g., MultiPolygon)")


async def get_worksite_info(
    ctx: RunContext[RAGContext],
    worksite_id: str,
    language: str = "fr",
) -> str:
    """Get worksite information from OSIRIS Brussels API.

    This tool provides access to Brussels worksite data including status,
    dates, affected roads, and location information.

    Args:
        ctx: RAG context with agent dependencies
        worksite_id: Worksite ID (ID_WS) to query
        language: Language preference - "fr" (French) or "nl" (Dutch). Default: "fr"

    Returns:
        Formatted worksite information with status, dates, and location

    Example:
        User: "What's the status of worksite 12345?"
        Tool: get_worksite_info(worksite_id="12345", language="fr")
        Response: "Worksite 12345: Active, Label: Rue de la Loi renovation,
                   Start: 2024-01-15, End: 2024-06-30, Roads: Rue de la Loi"
    """
    try:
        # Validate language parameter
        if language not in ["fr", "nl"]:
            language = "fr"  # Default to French

        # Check cache first
        cache_key = f"{worksite_id}:{language}"
        if cache_key in _worksite_cache:
            cached_data, cached_time = _worksite_cache[cache_key]
            if datetime.now() - cached_time < timedelta(
                seconds=ctx.deps.osiris_config.cache_ttl_seconds
            ):
                logger.info(f"Worksite cache hit for {worksite_id}")
                return cached_data["formatted"]

        config = ctx.deps.osiris_config

        # Construct API URL with worksite ID
        url = f"{config.base_url}/{worksite_id}"

        # Prepare authentication
        auth = None
        if config.username and config.password:
            auth = (config.username, config.password)

        # Make API call
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.get(url, auth=auth, params={"filter": f"ID_WS = {worksite_id}"})
            response.raise_for_status()
            data = response.json()

        # Parse GeoJSON Feature response
        if not data:
            return f"Worksite {worksite_id} not found in OSIRIS database"

        properties = data.get("properties", {})
        geometry = data.get("geometry", {})

        # Extract data based on language preference
        status = properties.get(f"STATUS_{language.upper()}", "Unknown")
        label = properties.get(f"LABEL_{language.upper()}", "No description")
        roads = properties.get(f"ROAD_IMPL_{language.upper()}", "No road information")
        start_date = properties.get("PGM_START_DATE", "Not specified")
        end_date = properties.get("PGM_END_DATE", "Not specified")

        # Create worksite data model for validation
        worksite_data = WorksiteData(
            id_ws=worksite_id,
            status_fr=properties.get("STATUS_FR"),
            status_nl=properties.get("STATUS_NL"),
            label_fr=properties.get("LABEL_FR"),
            label_nl=properties.get("LABEL_NL"),
            pgm_start_date=properties.get("PGM_START_DATE"),
            pgm_end_date=properties.get("PGM_END_DATE"),
            road_impl_fr=properties.get("ROAD_IMPL_FR"),
            road_impl_nl=properties.get("ROAD_IMPL_NL"),
            geometry_type=geometry.get("type") if geometry else None,
        )

        # Format response
        formatted = (
            f"Worksite {worksite_id}:\n"
            f"Status: {status}\n"
            f"Description: {label}\n"
            f"Planned period: {start_date} to {end_date}\n"
            f"Affected roads: {roads}"
        )

        # Cache result
        _worksite_cache[cache_key] = (
            {"formatted": formatted, "raw": data, "model": worksite_data.model_dump()},
            datetime.now(),
        )

        logger.info(f"Worksite data fetched for {worksite_id} ({language})")
        return formatted

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"Worksite {worksite_id} not found")
            return f"Worksite {worksite_id} not found in OSIRIS database"
        elif e.response.status_code == 401:
            logger.error("OSIRIS API authentication failed")
            return "Unable to access OSIRIS API (authentication failed)"
        else:
            logger.error(f"OSIRIS API error: HTTP {e.response.status_code}")
            return f"Unable to fetch worksite {worksite_id} (API error: {e.response.status_code})"

    except httpx.TimeoutException:
        logger.error(f"OSIRIS API timeout for worksite {worksite_id}")
        return f"Unable to fetch worksite {worksite_id} (timeout)"

    except Exception as e:
        logger.error(f"Worksite tool error for {worksite_id}: {e}", exc_info=True)
        return f"Unable to fetch worksite {worksite_id}: {str(e)}"
