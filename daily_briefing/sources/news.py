"""News source — fetches latest headlines from configured RSS/Atom feeds.

Uses `feedparser` for universal RSS/Atom parsing. Configure feeds
via the NEWS_FEEDS env var (comma-separated URLs) or brief.yaml.

Default feeds are kept minimal — the user adds what they want.
"""

from __future__ import annotations

import os
from collections import OrderedDict
from typing import Any

import feedparser

from daily_briefing.sources.base import SourceProtocol, SourceResult

# Default feeds (user overrides in .env or brief.yaml)
# heise.de: German tech news | dev.to: developer community
DEFAULT_FEEDS = os.environ.get(
    "NEWS_FEEDS",
    "https://www.heise.de/rss/heise-atom.xml,https://dev.to/feed",
)
MAX_ITEMS_PER_FEED = 3


class NewsSource(SourceProtocol):
    """Fetches latest headlines from RSS/Atom feeds."""

    name = "news"

    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch headlines from all configured feeds."""
        source_config = config.get("sources", {}).get("news", {})
        feeds_raw = source_config.get("feeds", DEFAULT_FEEDS)
        if isinstance(feeds_raw, str):
            feed_urls = [u.strip() for u in feeds_raw.split(",") if u.strip()]
        else:
            feed_urls = feeds_raw

        all_items = []
        errors = []
        seen_titles: OrderedDict[str, bool] = OrderedDict()  # Dedup by title

        for url in feed_urls:
            try:
                items = self._fetch_feed(url)
                for item in items:
                    title = item.get("title", "")
                    # Simple dedup: first 80 chars of title, lowercase
                    dedup_key = title[:80].lower().strip()
                    if dedup_key and dedup_key not in seen_titles:
                        seen_titles[dedup_key] = True
                        all_items.append(item)
            except Exception as e:
                errors.append(f"{url[:50]}: {e}")

        if not all_items and errors:
            return SourceResult(
                name=self.name,
                priority=60,
                error="; ".join(errors),
            )

        return SourceResult(
            name=self.name,
            priority=60,
            data={
                "headlines": all_items[:10],  # Max 10 total headlines across all feeds
                "total": len(all_items),
                "feeds_checked": len(feed_urls),
            },
        )

    def _fetch_feed(self, url: str) -> list[dict[str, Any]]:
        """Fetch and parse a single RSS/Atom feed."""
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            raise RuntimeError(f"Feed parse error: {feed.bozo_exception}")

        items = []
        for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
            # Extract source name from feed title
            source = feed.feed.get("title", url.split("/")[2])

            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "source": source,
                "published": entry.get("published", entry.get("updated", "")),
                "summary": (entry.get("summary", entry.get("description", ""))[:200] if entry.get("summary") or entry.get("description") else ""),
            })

        return items
