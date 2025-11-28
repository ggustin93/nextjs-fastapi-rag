"""
EXAMPLE: How to add optional external API tools to the RAG agent.

This is a TEMPLATE showing the pattern - users can copy and adapt for their own APIs.
Uses weather API as a simple, generic example that demonstrates best practices.

KEY POINTS:
- This is OPTIONAL - the RAG system works perfectly without external API tools
- This shows the PATTERN for adding ANY external API (weather, CRM, ERP, etc.)
- Uses type-safe Pydantic models for API responses
- Uses dependency injection via RunContext for configuration
- Includes error handling and retry logic

To use this pattern for your own API:
1. Copy this file and rename it (e.g., external_api_myservice.py)
2. Replace WeatherData with your API's response model
3. Replace ExternalAPIConfig with your API's configuration
4. Replace fetch_weather with your API's fetch function
5. Register the tool in services/api/app/core/rag_wrapper.py (see pattern below)
"""

from typing import Optional

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import RunContext


# Step 1: Define type-safe response model for the external API
class WeatherData(BaseModel):
    """
    Weather API response model (example).

    Replace this with your API's response structure.
    Use Pydantic for type safety and validation.
    """

    temperature: float = Field(description="Temperature in Celsius")
    condition: str = Field(description="Weather condition")
    humidity: int = Field(description="Humidity percentage")
    location: str = Field(description="Location name")


# Step 2: Define configuration for the external API integration
class ExternalAPIConfig(BaseModel):
    """
    Configuration for external API integration (example).

    Replace with your API's configuration needs:
    - API keys, base URLs, timeouts
    - Feature flags (enabled/disabled)
    - Rate limits, retry policies
    """

    enabled: bool = True
    api_key: Optional[str] = None
    api_url: str = "https://api.openweathermap.org/data/2.5/weather"
    timeout: int = 30
    max_retries: int = 3


# Step 3: Create the tool function (the actual API integration)
async def fetch_weather(ctx: RunContext, city: str, country_code: str = "BE") -> WeatherData:
    """
    EXAMPLE: Fetch weather data for a city.

    This demonstrates the pattern for external API integration:
    - Type-safe with Pydantic models
    - Async/await for performance
    - Error handling with specific messages
    - Configuration via RunContext deps (dependency injection)
    - Proper HTTP client lifecycle management

    Args:
        ctx: PydanticAI context with dependencies (contains config)
        city: City name
        country_code: ISO country code (default: BE for Belgium)

    Returns:
        WeatherData model with current weather

    Raises:
        ValueError: If external API is disabled or configuration is invalid
        httpx.HTTPError: If API request fails
    """
    # Get config from context (dependency injection pattern)
    # In your implementation, replace ExternalAPIConfig with your config class
    config: ExternalAPIConfig = ctx.deps.external_api_config

    if not config.enabled:
        raise ValueError("External API integration is disabled in configuration")

    if not config.api_key:
        raise ValueError(
            "External API key not configured - set WEATHER_API_KEY environment variable"
        )

    # Make API call with proper error handling
    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.get(
                config.api_url,
                params={
                    "q": f"{city},{country_code}",
                    "appid": config.api_key,
                    "units": "metric",  # Celsius
                },
            )
            response.raise_for_status()
            data = response.json()

        # Return type-safe model
        # Replace this with your API's response parsing
        return WeatherData(
            temperature=data["main"]["temp"],
            condition=data["weather"][0]["description"],
            humidity=data["main"]["humidity"],
            location=f"{city}, {country_code}",
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"City '{city}' not found in weather database")
        elif e.response.status_code == 401:
            raise ValueError("Invalid API key - check WEATHER_API_KEY configuration")
        else:
            raise ValueError(f"Weather API error: HTTP {e.response.status_code}")

    except httpx.TimeoutException:
        raise ValueError(f"Weather API timeout after {config.timeout}s")

    except Exception as e:
        raise ValueError(f"Failed to fetch weather data: {str(e)}")


"""
HOW TO REGISTER THIS TOOL (Optional Pattern):

In services/api/app/core/rag_wrapper.py:

```python
from packages.core.tools.external_api_example import fetch_weather, ExternalAPIConfig
import os

# OPTIONAL: Only add if you need external API integration
external_api_config = ExternalAPIConfig(
    enabled=os.getenv("ENABLE_WEATHER_API", "false").lower() == "true",
    api_key=os.getenv("WEATHER_API_KEY"),
)

# Create RAG context with optional external API config
class RAGContext:
    db_client: SupabaseRestClient
    reranker: Optional[Any] = None
    domain_config: Optional[DomainConfig] = None
    external_api_config: Optional[ExternalAPIConfig] = None  # OPTIONAL

rag_context = RAGContext(
    db_client=db_client,
    reranker=reranker,
    domain_config=domain_config,
    external_api_config=external_api_config if external_api_config.enabled else None,
)

# Register tool ONLY if enabled (conditional tool registration)
if external_api_config.enabled:
    agent = Agent(
        model="openai:gpt-4o",
        deps_type=RAGContext,
        deps=rag_context,
        tools=[search_knowledge_base, fetch_weather],  # Add optional tool
    )
else:
    # Default: No external tools
    agent = Agent(
        model="openai:gpt-4o",
        deps_type=RAGContext,
        deps=rag_context,
        tools=[search_knowledge_base],  # Just core RAG
    )
```

In .env:
```
# Optional: Enable weather API integration
ENABLE_WEATHER_API=true
WEATHER_API_KEY=your_openweathermap_api_key_here
```
"""


"""
KEY PRINCIPLES DEMONSTRATED:

1. **Type Safety**: Use Pydantic models for API responses and configuration
2. **Dependency Injection**: Config via RunContext.deps, not global variables
3. **Optional by Default**: External tools are opt-in via environment variables
4. **Generic Pattern**: Easy to adapt for ANY external API (CRM, ERP, custom services)
5. **Environment-Driven**: Enable/disable via ENABLE_* environment variables
6. **Error Handling**: Specific, actionable error messages for debugging
7. **Resource Management**: Proper async context managers for HTTP clients
8. **Documentation**: Clear docstrings explaining purpose and usage

ANTI-PATTERNS TO AVOID:
❌ Hardcoding API keys in source code
❌ Using global variables for configuration
❌ Mixing business logic into the core agent
❌ Making external tools required (always optional!)
❌ Poor error messages ("API failed" vs "Invalid API key - check WEATHER_API_KEY")
"""
