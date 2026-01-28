"""External tool integration configurations.

This module contains configurations for external API integrations
that are separate from the core RAG pipeline (LLM, Embedding, Database, etc.).

These tools are optional features that enhance the RAG agent's capabilities
but are not required for basic knowledge base functionality.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


def _get_clean_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with validation and comment stripping.

    Handles common .env file issues:
    - Strips whitespace
    - Treats comment-only values as None
    - Validates no invalid characters like '#' in actual values
    """
    value = os.getenv(key)

    if not value:
        return default

    value = value.strip()

    if not value or value.startswith("#"):
        return default

    if "#" in value:
        import logging

        logging.warning(
            f"Environment variable {key} contains '#' - likely malformed comment. "
            f"Using default value. Check your .env file."
        )
        return default

    return value


@dataclass(frozen=True)
class WeatherToolConfig:
    """Weather API tool configuration using Open-Meteo.

    Open-Meteo is a free weather API with no API key required.
    Includes geocoding support for city name → coordinates conversion.

    Environment Variables:
        WEATHER_BASE_URL: Open-Meteo forecast endpoint (default: "https://api.open-meteo.com/v1/forecast")
        WEATHER_GEOCODE_URL: Open-Meteo geocoding endpoint (default: "https://geocoding-api.open-meteo.com/v1/search")
        WEATHER_CACHE_TTL: Cache time-to-live in seconds (default: 900 = 15 minutes)
        WEATHER_TIMEOUT: API request timeout in seconds (default: 5)
        WEATHER_TEMPERATURE_UNIT: Temperature unit - "celsius" or "fahrenheit" (default: "celsius")
    """

    base_url: str = field(
        default_factory=lambda: os.getenv(
            "WEATHER_BASE_URL", "https://api.open-meteo.com/v1/forecast"
        )
    )
    geocode_url: str = field(
        default_factory=lambda: os.getenv(
            "WEATHER_GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search"
        )
    )
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("WEATHER_CACHE_TTL", "900"))
    )
    timeout_seconds: int = field(default_factory=lambda: int(os.getenv("WEATHER_TIMEOUT", "5")))
    temperature_unit: str = field(
        default_factory=lambda: os.getenv("WEATHER_TEMPERATURE_UNIT", "celsius")
    )


@dataclass(frozen=True)
class OsirisWorksiteConfig:
    """OSIRIS Brussels worksite API configuration.

    OSIRIS provides Brussels worksite data via GeoJSON API with Basic authentication.

    Environment Variables:
        OSIRIS_BASE_URL: OSIRIS API endpoint (default: "https://api.osiris.brussels/geoserver/ogc/features/v1/collections/api:WORKSITES/items")
        OSIRIS_USERNAME: Basic auth username (default: "cdco")
        OSIRIS_PASSWORD: Basic auth password (required - set in .env)
        OSIRIS_CACHE_TTL: Cache time-to-live in seconds (default: 900 = 15 minutes)
        OSIRIS_TIMEOUT: API request timeout in seconds (default: 10)
    """

    base_url: str = field(
        default_factory=lambda: os.getenv(
            "OSIRIS_BASE_URL",
            "https://api.osiris.brussels/geoserver/ogc/features/v1/collections/api:WORKSITES/items",
        )
    )
    username: str = field(default_factory=lambda: os.getenv("OSIRIS_USERNAME", "cdco"))
    password: Optional[str] = field(default_factory=lambda: _get_clean_env("OSIRIS_PASSWORD"))
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("OSIRIS_CACHE_TTL", "900"))
    )
    timeout_seconds: int = field(default_factory=lambda: int(os.getenv("OSIRIS_TIMEOUT", "10")))


@dataclass(frozen=True)
class OTRSToolConfig:
    """OTRS ticket system API configuration.

    OTRS provides ticket data via GenericInterface REST API with session-based authentication.

    Environment Variables:
        OTRS_SERVER_URL: OTRS REST API base URL (required)
            Example: "https://otrs.example.com/otrs/nph-genericinterface.pl/Webservice/GenericTicketConnectorREST"
        OTRS_USERNAME: API username (required)
        OTRS_PASSWORD: API password (required)
        OTRS_CACHE_TTL: Cache TTL for ticket details in seconds (default: 900 = 15 minutes)
        OTRS_SEARCH_CACHE_TTL: Cache TTL for search results in seconds (default: 300 = 5 minutes)
        OTRS_TIMEOUT: API request timeout in seconds (default: 30)
        OTRS_VERIFY_SSL: Whether to verify SSL certificates (default: "true")
        OTRS_WEB_URL: Web interface URL for iframe viewing (optional, defaults to server base URL)
            Example: "https://otrs.example.com"
    """

    server_url: Optional[str] = field(default_factory=lambda: _get_clean_env("OTRS_SERVER_URL"))
    username: Optional[str] = field(default_factory=lambda: _get_clean_env("OTRS_USERNAME"))
    password: Optional[str] = field(default_factory=lambda: _get_clean_env("OTRS_PASSWORD"))
    cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("OTRS_CACHE_TTL", "900")))
    search_cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("OTRS_SEARCH_CACHE_TTL", "300"))
    )
    timeout_seconds: int = field(default_factory=lambda: int(os.getenv("OTRS_TIMEOUT", "30")))
    verify_ssl: bool = field(
        default_factory=lambda: os.getenv("OTRS_VERIFY_SSL", "true").lower() == "true"
    )
    web_url: Optional[str] = field(default_factory=lambda: _get_clean_env("OTRS_WEB_URL"))

    @property
    def is_configured(self) -> bool:
        """Check if OTRS is properly configured with required credentials."""
        return bool(self.server_url and self.username and self.password)

    @property
    def effective_web_url(self) -> Optional[str]:
        """Get the web URL for iframe, falling back to server URL base."""
        if self.web_url:
            return self.web_url.rstrip("/")
        if self.server_url:
            # Extract base URL from REST API URL
            # e.g., "https://otrs.example.com/otrs/nph-genericinterface.pl/..." -> "https://otrs.example.com"
            from urllib.parse import urlparse

            parsed = urlparse(self.server_url)
            return f"{parsed.scheme}://{parsed.netloc}"
        return None


__all__ = ["WeatherToolConfig", "OsirisWorksiteConfig", "OTRSToolConfig"]
