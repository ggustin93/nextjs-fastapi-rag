"""Weather tool for RAG agent using Open-Meteo API.

This module provides real-time weather data for any location worldwide.
Uses Open-Meteo API (unlimited, no API key required) with:
- Geocoding support (city name → lat/lon)
- In-memory caching (15-minute TTL)
- Comprehensive error handling
- PydanticAI RunContext[RAGContext] pattern
"""

import logging
from datetime import datetime, timedelta

import httpx
from pydantic_ai import RunContext

from packages.core.types import RAGContext, WeatherConfig

logger = logging.getLogger(__name__)

# In-memory cache (use Redis for production)
_weather_cache: dict[str, tuple[dict, datetime]] = {}


async def get_weather(
    ctx: RunContext[RAGContext],
    location: str,
    include_forecast: bool = False,
) -> str:
    """Get current weather for a location using Open-Meteo API.

    This tool provides real-time weather information for any location worldwide.
    Use it when users ask about weather, temperature, or climate conditions.

    Args:
        ctx: RAG context with agent dependencies
        location: City name or "latitude,longitude" (e.g., "Paris" or "48.8566,2.3522")
        include_forecast: If True, include 24-hour forecast (default: False)

    Returns:
        Formatted weather information with temperature, conditions, and optional forecast

    Example:
        User: "What's the weather like in Brussels?"
        Tool: get_weather(location="Brussels")
        Response: "Brussels: 12°C, partly cloudy, humidity 65%"
    """
    try:
        # Check cache first
        cache_key = f"{location}:{include_forecast}"
        if cache_key in _weather_cache:
            cached_data, cached_time = _weather_cache[cache_key]
            config = WeatherConfig()
            if datetime.now() - cached_time < timedelta(seconds=config.cache_ttl_seconds):
                logger.info(f"Weather cache hit for {location}")
                return cached_data["formatted"]

        config = WeatherConfig()

        # Parse location (city name or lat,lon)
        if "," in location and all(
            part.replace(".", "").replace("-", "").isdigit() for part in location.split(",")
        ):
            # Direct lat,lon provided
            lat, lon = map(float, location.split(","))
            location_name = f"{lat:.2f}°, {lon:.2f}°"
        else:
            # Geocode city name to lat,lon
            lat, lon, location_name = await _geocode_location(location, config)

        # Fetch weather data
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "temperature_unit": config.temperature_unit,
            "wind_speed_unit": "kmh",
        }

        if include_forecast:
            params["hourly"] = "temperature_2m,weather_code"
            params["forecast_hours"] = "24"

        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.get(config.base_url, params=params)
            response.raise_for_status()
            data = response.json()

        # Format response
        current = data["current"]
        temp_unit = "°C" if config.temperature_unit == "celsius" else "°F"
        weather_desc = _get_weather_description(current["weather_code"])

        formatted = (
            f"{location_name}: {current['temperature_2m']}{temp_unit}, {weather_desc}, "
            f"humidity {current['relative_humidity_2m']}%, wind {current['wind_speed_10m']} km/h"
        )

        if include_forecast:
            hourly = data["hourly"]
            forecast_temps = hourly["temperature_2m"][:24]
            forecast_desc = (
                f"\n24h forecast: High {max(forecast_temps)}{temp_unit}, "
                f"Low {min(forecast_temps)}{temp_unit}"
            )
            formatted += forecast_desc

        # Cache result
        _weather_cache[cache_key] = ({"formatted": formatted, "raw": data}, datetime.now())

        logger.info(f"Weather fetched for {location}: {formatted}")
        return formatted

    except httpx.TimeoutException:
        logger.error(f"Weather API timeout for {location}")
        return f"Unable to fetch weather for {location} (timeout)"
    except Exception as e:
        logger.error(f"Weather tool error for {location}: {e}", exc_info=True)
        return f"Unable to fetch weather for {location}: {str(e)}"


async def _geocode_location(city_name: str, config: WeatherConfig) -> tuple[float, float, str]:
    """Geocode city name to coordinates using Open-Meteo Geocoding API."""
    params = {
        "name": city_name,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
        response = await client.get(config.geocode_url, params=params)
        response.raise_for_status()
        data = response.json()

    if not data.get("results"):
        raise ValueError(f"Location not found: {city_name}")

    result = data["results"][0]
    return result["latitude"], result["longitude"], result["name"]


def _get_weather_description(weather_code: int) -> str:
    """Map WMO weather code to description."""
    codes = {
        0: "clear sky",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "foggy",
        48: "depositing rime fog",
        51: "light drizzle",
        53: "moderate drizzle",
        55: "dense drizzle",
        61: "slight rain",
        63: "moderate rain",
        65: "heavy rain",
        71: "slight snow",
        73: "moderate snow",
        75: "heavy snow",
        80: "slight rain showers",
        81: "moderate rain showers",
        82: "violent rain showers",
        95: "thunderstorm",
        96: "thunderstorm with slight hail",
        99: "thunderstorm with heavy hail",
    }
    return codes.get(weather_code, f"weather code {weather_code}")
