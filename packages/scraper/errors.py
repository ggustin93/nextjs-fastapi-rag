"""Custom exceptions for the scraper module."""


class ScraperError(Exception):
    """Base exception for all scraper errors."""

    def __init__(self, message: str, url: str | None = None):
        self.url = url
        super().__init__(message)


class CrawlError(ScraperError):
    """Error during crawling operation."""

    def __init__(self, message: str, url: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message, url)


class ConfigError(ScraperError):
    """Error in configuration."""

    pass


class OutputError(ScraperError):
    """Error writing output files."""

    def __init__(self, message: str, path: str | None = None):
        self.path = path
        super().__init__(message)


class RateLimitError(CrawlError):
    """Rate limit exceeded."""

    def __init__(self, url: str, retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {url}", url, status_code=429)
