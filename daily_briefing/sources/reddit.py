"""Reddit source — fetches top posts from configured subreddits via RSS.

Reddit offers public RSS feeds with no authentication required:
  https://www.reddit.com/r/{subreddit}/top/.rss?t=day

Uses `feedparser` for RSS parsing (the same library handles
all RSS/Atom quirks across different feed sources).

Configured subreddits come from the REDDIT_SUBREDDITS env var
(comma-separated) or brief.yaml sources.reddit.subreddits list.
"""

from __future__ import annotations

import os
from typing import Any

import feedparser
import requests

from daily_briefing.sources.base import SourceProtocol, SourceResult

# DEFAULT_SUBREDDITS removed — subreddits are exclusively from brief.yaml or ENV
MAX_POSTS_PER_SUB = 3


class RedditSource(SourceProtocol):
    """Fetches top Reddit posts via public RSS feeds."""

    name = "reddit"

    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch top posts from all configured subreddits."""
        source_config = config.get("sources", {}).get("reddit", {})
        subreddits_raw = source_config.get("subreddits", None)
        if not subreddits_raw:
            return SourceResult(
                name=self.name,
                priority=50,
                error="No subreddits configured. Add sources.reddit.subreddits to brief.yaml",
            )
        if isinstance(subreddits_raw, str):
            subreddits = [s.strip() for s in subreddits_raw.split(",") if s.strip()]
        else:
            subreddits = subreddits_raw

        results = {}
        errors = []

        for sub in subreddits:
            try:
                posts = self._fetch_subreddit(sub)
                results[sub] = posts
            except Exception as e:
                errors.append(f"r/{sub}: {e}")
                results[sub] = []

        # Don't fail if some subreddits work and others don't
        total_posts = sum(len(posts) for posts in results.values())
        if total_posts == 0 and errors:
            return SourceResult(
                name=self.name,
                priority=50,
                error="; ".join(errors),
            )

        return SourceResult(
            name=self.name,
            priority=50,
            data={
                "subreddits": results,
                "total_posts": total_posts,
            },
        )

    def _fetch_subreddit(self, subreddit: str) -> list[dict[str, Any]]:
        """Fetch top posts from a single subreddit."""
        url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day&limit={MAX_POSTS_PER_SUB}"
        headers = {"User-Agent": "DailyBriefing/1.0 (Hermes Agent; +https://github.com/kvnlnk/daily-briefing)"}
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        if feed.bozo and not feed.entries:
            raise RuntimeError(f"Feed parse error: {feed.bozo_exception}")

        posts = []
        for entry in feed.entries[:MAX_POSTS_PER_SUB]:
            posts.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "score": self._extract_score(entry),
                "author": entry.get("author", ""),
            })

        return posts

    @staticmethod
    def _extract_score(entry: Any) -> int | None:
        """Extract score from Reddit RSS entry.

        Reddit RSS sometimes includes score in the description field
        or a custom namespace. We try a few heuristics.
        """
        # Try to find "score" in the content
        desc = entry.get("description", entry.get("summary", ""))
        if desc and "score" in desc.lower():
            import re
            match = re.search(r"score[:\s]+(\d+)", desc, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
