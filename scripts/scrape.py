#!/usr/bin/env python3
"""
CLI for web scraping using Crawl4AI.

Usage:
    # Crawl a configured source
    python scripts/scrape.py --source belgian_legal

    # Crawl a single URL
    python scripts/scrape.py --url https://example.com/page

    # List available sources
    python scripts/scrape.py --list

    # Use custom config file
    python scripts/scrape.py --source belgian_legal --config custom_sources.yaml
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from packages.scraper import (
    CrawlerConfig,
    WebCrawler,
    load_sources_config,
)


def get_default_config_path() -> Path:
    """Get the default sources.yaml path."""
    return project_root / "packages" / "scraper" / "sources.yaml"


async def crawl_source(config: CrawlerConfig, source_name: str) -> None:
    """Crawl a configured source."""
    if source_name not in config.sources:
        print(f"Error: Source '{source_name}' not found in configuration.")
        print(f"Available sources: {', '.join(config.sources.keys())}")
        sys.exit(1)

    source = config.sources[source_name]
    print(f"Starting crawl for: {source.name}")
    print(f"  Base URL: {source.base_url}")
    print(f"  Max pages: {source.max_pages}")
    print(f"  Max depth: {source.max_depth}")
    print()

    crawler = WebCrawler(config)
    result = await crawler.crawl_source(source)

    print()
    print("=" * 50)
    print(f"Crawl completed: {source.name}")
    print(f"  Total URLs: {result.total_urls}")
    print(f"  Successful: {result.successful}")
    print(f"  Failed: {result.failed}")
    print(f"  Success rate: {result.success_rate:.1f}%")
    print(f"  Duration: {result.duration_seconds:.1f}s")
    print(f"  Output: {config.output_dir}")


async def crawl_url(config: CrawlerConfig, url: str, output_name: str | None = None) -> None:
    """Crawl a single URL."""
    print(f"Crawling: {url}")
    print()

    crawler = WebCrawler(config)
    result = await crawler.crawl_url(url, source_name=output_name or "manual")

    if result.success:
        # Write the result
        from packages.scraper import MarkdownWriter

        writer = MarkdownWriter(config.output_dir)
        output_path = writer.write(result, subdir=output_name or "manual")

        print("Crawl successful!")
        print(f"  Title: {result.metadata.title if result.metadata else 'N/A'}")
        print(f"  Output: {output_path}")
    else:
        print(f"Crawl failed: {result.error}")
        sys.exit(1)


def list_sources(config: CrawlerConfig) -> None:
    """List all configured sources."""
    print("Available sources:")
    print()
    for name, source in config.sources.items():
        print(f"  {name}:")
        print(f"    Name: {source.name}")
        print(f"    URL: {source.base_url}")
        print(f"    Category: {source.category}")
        print(f"    Max pages: {source.max_pages}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Web scraper using Crawl4AI for markdown generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--source",
        "-s",
        help="Name of configured source to crawl",
    )
    parser.add_argument(
        "--url",
        "-u",
        help="Single URL to crawl",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        help="Path to sources.yaml config file",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output subdirectory name (for single URL mode)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available sources",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory",
    )

    args = parser.parse_args()

    # Load configuration
    config_path = args.config or get_default_config_path()

    if config_path.exists():
        config = load_sources_config(config_path)
    else:
        # Use default config if no file exists
        config = CrawlerConfig()

    # Override output dir if specified
    if args.output_dir:
        config.output_dir = args.output_dir

    # Execute command
    if args.list:
        list_sources(config)
    elif args.source:
        asyncio.run(crawl_source(config, args.source))
    elif args.url:
        asyncio.run(crawl_url(config, args.url, args.output))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
