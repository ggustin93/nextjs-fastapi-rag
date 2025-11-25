"""Data models for crawl results."""

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class CrawlMetadata(BaseModel):
    """Metadata extracted from a crawled page."""

    url: str
    title: str | None = None
    description: str | None = None
    date: datetime | None = None
    language: str = "fr"
    source_name: str = ""
    category: str = "general"
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
    depth: int = 0
    parent_url: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_frontmatter(self) -> dict[str, Any]:
        """Convert to YAML frontmatter dict."""
        data = {
            "url": self.url,
            "source": self.source_name,
            "category": self.category,
            "language": self.language,
            "crawled_at": self.crawled_at.isoformat(),
        }
        if self.title:
            data["title"] = self.title
        if self.description:
            data["description"] = self.description
        if self.date:
            data["date"] = self.date.isoformat()
        if self.parent_url:
            data["parent_url"] = self.parent_url
        if self.extra:
            data.update(self.extra)
        return data


class CrawlResult(BaseModel):
    """Result of crawling a single page."""

    url: str
    success: bool
    content: str | None = None
    markdown: str | None = None
    metadata: CrawlMetadata | None = None
    links: list[str] = Field(default_factory=list)
    error: str | None = None
    status_code: int | None = None
    output_path: Path | None = None


class BatchCrawlResult(BaseModel):
    """Result of crawling multiple pages."""

    source_name: str
    total_urls: int
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[CrawlResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_seconds: float | None = None

    def add_result(self, result: CrawlResult) -> None:
        """Add a crawl result and update counters."""
        self.results.append(result)
        if result.success:
            self.successful += 1
        elif result.error:
            self.failed += 1
        else:
            self.skipped += 1

    def finalize(self) -> None:
        """Mark batch as complete and calculate duration."""
        self.completed_at = datetime.utcnow()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_urls == 0:
            return 0.0
        return (self.successful / self.total_urls) * 100
