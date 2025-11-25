"""
Osiris Web Scraper Module

Generic, extensible web scraper using Crawl4AI for markdown generation.
Integrates with existing document ingestion pipeline.
"""

from .config import CrawlerConfig, SourceConfig, load_sources_config
from .crawler import WebCrawler
from .errors import (
    ConfigError,
    CrawlError,
    OutputError,
    RateLimitError,
    ScraperError,
)
from .models import BatchCrawlResult, CrawlMetadata, CrawlResult
from .output import MarkdownWriter

__all__ = [
    # Config
    "SourceConfig",
    "CrawlerConfig",
    "load_sources_config",
    # Models
    "CrawlResult",
    "CrawlMetadata",
    "BatchCrawlResult",
    # Crawler
    "WebCrawler",
    # Output
    "MarkdownWriter",
    # Errors
    "ScraperError",
    "CrawlError",
    "ConfigError",
    "OutputError",
    "RateLimitError",
]
