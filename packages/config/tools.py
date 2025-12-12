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


__all__ = ["WeatherToolConfig", "OsirisWorksiteConfig"]
