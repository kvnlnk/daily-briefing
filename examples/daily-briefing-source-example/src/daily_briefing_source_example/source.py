"""Quote of the Day source — example third-party package for Daily Briefing.

This source fetches a random quote from a free public API.
It demonstrates how to write an external source package that
auto-registers via setuptools entry points.

To install:
    pip install -e examples/daily-briefing-source-example

Then run:
    daily-briefing --list-sources    # "quote" should appear
    daily-briefing --source quote    # Test single source
"""

from __future__ import annotations

from typing import Any

import requests

from daily_briefing.sources.base import SourceProtocol, SourceResult


QUOTE_API = "https://api.quotable.io/random"


class QuoteSource(SourceProtocol):
    """Fetches a random quote from quotable.io."""

    name = "quote"

    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch a random quote."""
        try:
            resp = requests.get(
                QUOTE_API,
                params={"maxLength": 200},
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            return SourceResult(
                name=self.name,
                priority=80,
                data={
                    "content": body.get("content", ""),
                    "author": body.get("author", "Unknown"),
                    "tags": body.get("tags", []),
                },
            )
        except requests.RequestException as e:
            return SourceResult(
                name=self.name,
                priority=80,
                error=f"Quote API error: {e}",
            )
