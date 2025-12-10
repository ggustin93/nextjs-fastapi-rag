"""Worksites API router for OSIRIS worksite data.

This module provides REST endpoints to access cached worksite data
including geometry for map visualization in the frontend.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from packages.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/worksites", tags=["worksites"])

# In-memory cache (shared with tool, ideally move to Redis)
_worksite_geometry_cache: dict[str, tuple[dict, datetime]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes


class WorksiteGeometryResponse(BaseModel):
    """Response model for worksite geometry endpoint."""

    id_ws: str = Field(description="Worksite ID")
    geometry: dict[str, Any] = Field(description="GeoJSON geometry (MultiPolygon or Polygon)")
    properties: dict[str, Any] = Field(description="Worksite properties")
    label_fr: str | None = Field(None, description="Label in French")
    label_nl: str | None = Field(None, description="Label in Dutch")
    status_fr: str | None = Field(None, description="Status in French")
    status_nl: str | None = Field(None, description="Status in Dutch")
    road_impl_fr: str | None = Field(None, description="Affected roads in French")
    road_impl_nl: str | None = Field(None, description="Affected roads in Dutch")
    pgm_start_date: str | None = Field(None, description="Planned start date")
    pgm_end_date: str | None = Field(None, description="Planned end date")


@router.get("/{worksite_id}/geometry", response_model=WorksiteGeometryResponse)
async def get_worksite_geometry(
    worksite_id: str,
    language: str = Query("fr", description="Language preference (fr or nl)"),
) -> WorksiteGeometryResponse:
    """Get worksite geometry and metadata from OSIRIS API.

    This endpoint fetches the full GeoJSON feature including geometry
    for map visualization in the frontend.

    Args:
        worksite_id: OSIRIS worksite ID (ID_WS)
        language: Language preference for labels (fr or nl)

    Returns:
        WorksiteGeometryResponse with geometry and metadata

    Raises:
        HTTPException: 404 if worksite not found, 502 if API error
    """
    try:
        # Validate language
        if language not in ["fr", "nl"]:
            language = "fr"

        # Check cache first
        cache_key = worksite_id
        if cache_key in _worksite_geometry_cache:
            cached_data, cached_time = _worksite_geometry_cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=CACHE_TTL_SECONDS):
                logger.info(f"Worksite geometry cache hit for {worksite_id}")
                return WorksiteGeometryResponse(**cached_data)

        # Get OSIRIS config
        config = settings.osiris

        # Construct API URL
        url = f"{config.base_url}/{worksite_id}"

        # Prepare authentication
        auth = None
        if config.username and config.password:
            auth = (config.username, config.password)

        # Make API call
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.get(
                url,
                auth=auth,
                params={"filter": f"ID_WS = {worksite_id}"},
            )

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Worksite {worksite_id} not found in OSIRIS database",
                )

            response.raise_for_status()
            data = response.json()

        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"Worksite {worksite_id} not found in OSIRIS database",
            )

        # Parse GeoJSON Feature
        properties = data.get("properties", {})
        geometry = data.get("geometry", {})

        if not geometry:
            raise HTTPException(
                status_code=404,
                detail=f"No geometry data available for worksite {worksite_id}",
            )

        # Build response
        response_data = {
            "id_ws": worksite_id,
            "geometry": geometry,
            "properties": properties,
            "label_fr": properties.get("LABEL_FR"),
            "label_nl": properties.get("LABEL_NL"),
            "status_fr": properties.get("STATUS_FR"),
            "status_nl": properties.get("STATUS_NL"),
            "road_impl_fr": properties.get("ROAD_IMPL_FR"),
            "road_impl_nl": properties.get("ROAD_IMPL_NL"),
            "pgm_start_date": properties.get("PGM_START_DATE"),
            "pgm_end_date": properties.get("PGM_END_DATE"),
        }

        # Cache result
        _worksite_geometry_cache[cache_key] = (response_data, datetime.now())
        logger.info(f"Worksite geometry fetched for {worksite_id}")

        return WorksiteGeometryResponse(**response_data)

    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.error("OSIRIS API authentication failed")
            raise HTTPException(
                status_code=502,
                detail="Unable to access OSIRIS API (authentication failed)",
            )
        logger.error(f"OSIRIS API error: HTTP {e.response.status_code}")
        raise HTTPException(
            status_code=502,
            detail=f"OSIRIS API error: {e.response.status_code}",
        )
    except httpx.TimeoutException:
        logger.error(f"OSIRIS API timeout for worksite {worksite_id}")
        raise HTTPException(
            status_code=504,
            detail=f"OSIRIS API timeout for worksite {worksite_id}",
        )
    except Exception as e:
        logger.error(f"Worksite geometry error for {worksite_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching worksite {worksite_id}: {str(e)}",
        )
