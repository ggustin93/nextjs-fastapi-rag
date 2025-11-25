"""Output handling for scraped content."""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .errors import OutputError
from .models import CrawlResult


class MarkdownWriter:
    """Writes crawled content to markdown files with YAML frontmatter."""

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, result: CrawlResult, subdir: str | None = None) -> Path:
        """Write a crawl result to a markdown file."""
        if not result.success or not result.markdown:
            raise OutputError("Cannot write unsuccessful or empty result", result.url)

        # Determine output directory
        target_dir = self.output_dir
        if subdir:
            target_dir = target_dir / subdir
            target_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename from URL
        filename = self._url_to_filename(result.url)
        output_path = target_dir / filename

        # Build content with frontmatter
        content = self._build_markdown(result)

        # Write file
        try:
            output_path.write_text(content, encoding="utf-8")
            result.output_path = output_path
            return output_path
        except IOError as e:
            raise OutputError(f"Failed to write file: {e}", str(output_path))

    def _build_markdown(self, result: CrawlResult) -> str:
        """Build markdown content with YAML frontmatter."""
        parts = []

        # Add frontmatter if metadata exists
        if result.metadata:
            frontmatter = result.metadata.to_frontmatter()
            parts.append("---")
            parts.append(
                yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False).strip()
            )
            parts.append("---")
            parts.append("")

        # Add markdown content
        if result.markdown:
            parts.append(result.markdown)

        return "\n".join(parts)

    def _url_to_filename(self, url: str) -> str:
        """Convert URL to a safe filename."""
        parsed = urlparse(url)

        # Extract meaningful parts
        path_parts = [p for p in parsed.path.split("/") if p]

        if path_parts:
            # Use last meaningful path segment
            base = path_parts[-1]
            # Remove common extensions
            base = re.sub(r"\.(html?|php|aspx?)$", "", base, flags=re.IGNORECASE)
        else:
            # Use domain if no path
            base = parsed.netloc.replace(".", "_")

        # Clean up the name
        base = re.sub(r"[^\w\-]", "_", base)
        base = re.sub(r"_+", "_", base).strip("_")

        # Add hash suffix for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        # Ensure reasonable length
        if len(base) > 50:
            base = base[:50]

        return f"{base}_{url_hash}.md"

    def write_batch_summary(
        self,
        source_name: str,
        results: list[CrawlResult],
        subdir: str | None = None,
    ) -> Path:
        """Write a summary file for a batch crawl."""
        target_dir = self.output_dir
        if subdir:
            target_dir = target_dir / subdir

        summary_path = target_dir / "_crawl_summary.md"

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        lines = [
            f"# Crawl Summary: {source_name}",
            "",
            f"**Date**: {datetime.utcnow().isoformat()}",
            f"**Total URLs**: {len(results)}",
            f"**Successful**: {len(successful)}",
            f"**Failed**: {len(failed)}",
            "",
        ]

        if successful:
            lines.extend(["## Successful Crawls", ""])
            for r in successful:
                title = r.metadata.title if r.metadata else "Untitled"
                lines.append(f"- [{title}]({r.url})")
            lines.append("")

        if failed:
            lines.extend(["## Failed Crawls", ""])
            for r in failed:
                lines.append(f"- {r.url}: {r.error}")
            lines.append("")

        summary_path.write_text("\n".join(lines), encoding="utf-8")
        return summary_path
