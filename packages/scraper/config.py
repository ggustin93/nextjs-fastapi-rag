"""Configuration models for the scraper module."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, HttpUrl

from packages.config import PROJECT_ROOT


class SelectorConfig(BaseModel):
    """CSS selectors for content extraction."""

    content: str | None = None
    title: str | None = None
    date: str | None = None
    exclude: list[str] = Field(default_factory=list)


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    requests_per_second: float = 1.0
    delay_between_pages: float = 1.0
    max_concurrent: int = 3


class RetryConfig(BaseModel):
    """Retry configuration for failed requests."""

    max_retries: int = 3
    backoff_factor: float = 2.0
    retry_statuses: list[int] = Field(default_factory=lambda: [429, 500, 502, 503, 504])


class SourceConfig(BaseModel):
    """Configuration for a single crawl source."""

    name: str
    base_url: HttpUrl
    description: str = ""
    category: str = "general"
    language: str = "fr"

    # URL patterns
    start_urls: list[str] = Field(default_factory=list)
    url_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)

    # Content extraction
    selectors: SelectorConfig = Field(default_factory=SelectorConfig)

    # Crawl behavior
    max_depth: int = 2
    max_pages: int = 100
    follow_links: bool = True

    # Rate limiting
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # Output
    output_subdir: str | None = None

    # Custom metadata to include in all documents
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class CrawlerConfig(BaseModel):
    """Global crawler configuration."""

    # Output settings (absolute path for resilience when running from different directories)
    output_dir: Path = PROJECT_ROOT / "data" / "processed" / "scraped"

    # Default rate limiting
    default_rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # Retry settings
    retry: RetryConfig = Field(default_factory=RetryConfig)

    # Browser settings
    headless: bool = True
    user_agent: str | None = None

    # Content settings
    include_images: bool = False
    include_links: bool = True

    # Sources
    sources: dict[str, SourceConfig] = Field(default_factory=dict)


def load_sources_config(config_path: Path | str) -> CrawlerConfig:
    """Load crawler configuration from YAML file."""
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return CrawlerConfig(**data)
