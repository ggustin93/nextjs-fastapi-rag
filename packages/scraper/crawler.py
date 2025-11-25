"""Web crawler using Crawl4AI for markdown generation."""

import asyncio
import re
from urllib.parse import urljoin, urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from .config import CrawlerConfig, SourceConfig
from .errors import CrawlError, RateLimitError
from .models import BatchCrawlResult, CrawlMetadata, CrawlResult
from .output import MarkdownWriter


class WebCrawler:
    """Async web crawler with rate limiting and retry support."""

    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.writer = MarkdownWriter(config.output_dir)
        self._visited_urls: set[str] = set()
        self._semaphore: asyncio.Semaphore | None = None

    async def crawl_source(
        self,
        source: SourceConfig,
        *,
        write_files: bool = True,
    ) -> BatchCrawlResult:
        """Crawl all URLs from a source configuration."""
        batch_result = BatchCrawlResult(
            source_name=source.name,
            total_urls=0,
        )

        # Reset visited URLs for this source
        self._visited_urls.clear()

        # Setup rate limiting
        max_concurrent = source.rate_limit.max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Collect URLs to crawl
        urls_to_crawl = list(source.start_urls)
        if not urls_to_crawl:
            urls_to_crawl = [str(source.base_url)]

        batch_result.total_urls = len(urls_to_crawl)

        # Browser configuration
        browser_kwargs = {"headless": self.config.headless}
        if self.config.user_agent:
            browser_kwargs["user_agent"] = self.config.user_agent
        browser_config = BrowserConfig(**browser_kwargs)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Process URLs with depth tracking
            pending = [(url, 0) for url in urls_to_crawl]  # (url, depth)

            while pending:
                url, depth = pending.pop(0)

                if url in self._visited_urls:
                    continue

                if depth > source.max_depth:
                    continue

                if len(self._visited_urls) >= source.max_pages:
                    break

                self._visited_urls.add(url)

                # Respect rate limiting
                async with self._semaphore:
                    result = await self._crawl_url(crawler, url, source, depth)

                    batch_result.add_result(result)

                    # Write file if successful
                    if write_files and result.success and result.markdown:
                        subdir = source.output_subdir or source.name.lower().replace(" ", "_")
                        self.writer.write(result, subdir=subdir)

                    # Add discovered links
                    if source.follow_links and result.success and result.links:
                        for link in result.links:
                            if self._should_follow_link(link, source):
                                pending.append((link, depth + 1))

                    # Rate limit delay
                    await asyncio.sleep(source.rate_limit.delay_between_pages)

        batch_result.total_urls = len(self._visited_urls)
        batch_result.finalize()

        # Write summary
        if write_files:
            subdir = source.output_subdir or source.name.lower().replace(" ", "_")
            self.writer.write_batch_summary(source.name, batch_result.results, subdir=subdir)

        return batch_result

    async def _crawl_url(
        self,
        crawler: AsyncWebCrawler,
        url: str,
        source: SourceConfig,
        depth: int,
    ) -> CrawlResult:
        """Crawl a single URL with retry logic."""
        retries = 0
        last_error = None

        while retries <= self.config.retry.max_retries:
            try:
                run_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    excluded_tags=source.selectors.exclude if source.selectors.exclude else None,
                )

                result = await crawler.arun(url=url, config=run_config)

                if not result.success:
                    raise CrawlError(
                        f"Crawl failed: {result.error_message}",
                        url,
                        status_code=result.status_code,
                    )

                # Check for rate limiting
                if result.status_code == 429:
                    raise RateLimitError(url)

                # Extract metadata
                metadata = CrawlMetadata(
                    url=url,
                    title=self._extract_title(result),
                    source_name=source.name,
                    category=source.category,
                    language=source.language,
                    depth=depth,
                    extra=source.extra_metadata,
                )

                # Extract links
                links = self._extract_links(result, url)

                return CrawlResult(
                    url=url,
                    success=True,
                    content=result.html,
                    markdown=result.markdown,
                    metadata=metadata,
                    links=links,
                    status_code=result.status_code,
                )

            except RateLimitError as e:
                # Exponential backoff for rate limits
                wait_time = e.retry_after or (self.config.retry.backoff_factor**retries * 10)
                await asyncio.sleep(wait_time)
                retries += 1
                last_error = str(e)

            except CrawlError as e:
                if e.status_code in self.config.retry.retry_statuses:
                    wait_time = self.config.retry.backoff_factor**retries
                    await asyncio.sleep(wait_time)
                    retries += 1
                    last_error = str(e)
                else:
                    return CrawlResult(
                        url=url,
                        success=False,
                        error=str(e),
                        status_code=e.status_code,
                    )

            except Exception as e:
                return CrawlResult(
                    url=url,
                    success=False,
                    error=str(e),
                )

        # Max retries exceeded
        return CrawlResult(
            url=url,
            success=False,
            error=f"Max retries exceeded. Last error: {last_error}",
        )

    def _extract_title(self, result) -> str | None:
        """Extract title from crawl result."""
        if hasattr(result, "metadata") and result.metadata:
            if hasattr(result.metadata, "title"):
                return result.metadata.title
        # Fallback: extract from markdown
        if result.markdown:
            match = re.search(r"^#\s+(.+)$", result.markdown, re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_links(self, result, base_url: str) -> list[str]:
        """Extract and normalize links from crawl result."""
        links = []
        if hasattr(result, "links") and result.links:
            for link in result.links.get("internal", []):
                href = link.get("href", "")
                if href:
                    absolute_url = urljoin(base_url, href)
                    links.append(absolute_url)
        return links

    def _should_follow_link(self, url: str, source: SourceConfig) -> bool:
        """Check if a link should be followed based on source config."""
        if url in self._visited_urls:
            return False

        parsed = urlparse(url)
        base_parsed = urlparse(str(source.base_url))

        # Must be same domain
        if parsed.netloc != base_parsed.netloc:
            return False

        # Check exclude patterns
        for pattern in source.exclude_patterns:
            if re.search(pattern, url):
                return False

        # Check include patterns if specified
        if source.url_patterns:
            for pattern in source.url_patterns:
                if re.search(pattern, url):
                    return True
            return False

        return True

    async def crawl_url(self, url: str, source_name: str = "manual") -> CrawlResult:
        """Crawl a single URL without source configuration."""
        browser_kwargs = {"headless": self.config.headless}
        if self.config.user_agent:
            browser_kwargs["user_agent"] = self.config.user_agent
        browser_config = BrowserConfig(**browser_kwargs)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

            try:
                result = await crawler.arun(url=url, config=run_config)

                if not result.success:
                    return CrawlResult(
                        url=url,
                        success=False,
                        error=result.error_message,
                        status_code=result.status_code,
                    )

                metadata = CrawlMetadata(
                    url=url,
                    title=self._extract_title(result),
                    source_name=source_name,
                )

                return CrawlResult(
                    url=url,
                    success=True,
                    content=result.html,
                    markdown=result.markdown,
                    metadata=metadata,
                    links=self._extract_links(result, url),
                    status_code=result.status_code,
                )

            except Exception as e:
                return CrawlResult(
                    url=url,
                    success=False,
                    error=str(e),
                )
