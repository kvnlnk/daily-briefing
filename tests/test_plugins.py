"""Tests for entry-point plugin discovery — third-party sources must work."""

from __future__ import annotations

import importlib.metadata
from unittest.mock import MagicMock, patch


from daily_briefing.config import BriefingConfig, SourceConfig
from daily_briefing.orchestrator import fetch_all, fetch_single
from daily_briefing.sources.base import SourceResult


class TestThirdPartySource:
    """Third-party plugin sources must be fetchable via fetch_all."""

    def test_plugin_not_rejected_as_unknown(self):
        """A source registered only via entry point must pass fetch_all's guard.

        This tests the critical bug: fetch_all rejects sources not in
        hardcoded SOURCE_REGISTRY even when they're registered via entry point.
        """
        # Create an entry-point-style source result
        fake_result = SourceResult(name="quote", priority=50, data={"text": "Hello!"})

        fake_entry_point = MagicMock(spec=importlib.metadata.EntryPoint)
        fake_entry_point.name = "quote"
        fake_entry_point.load.return_value = lambda: MagicMock(
            fetch=lambda cfg: fake_result,
            name="quote",
        )

        config = BriefingConfig(
            sources={"quote": SourceConfig(name="quote", priority=50, enabled=True)},
            raw={"sources": {"quote": {"enabled": True, "priority": 50}}},
        )

        with patch("daily_briefing.orchestrator._ENTRY_POINTS", {"quote": fake_entry_point}):
            results = fetch_all(config)

        # Must include the entry-point source — NOT with "Unknown source" error
        names = {r.name for r in results}
        assert "quote" in names, (
            f"Entry-point source 'quote' was rejected. "
            f"Available results: {names}. "
            f"Bug: fetch_all guards against SOURCE_REGISTRY only, not _ENTRY_POINTS."
        )

        # Verify it was NOT rejected with "Unknown source" error
        quote_result = next(r for r in results if r.name == "quote")
        assert quote_result.is_success(), (
            f"Entry-point source was rejected with: {quote_result.error}. "
            f"Bug: the guard in fetch_all must also accept _ENTRY_POINTS sources."
        )

    def test_plugin_actually_fetches_data(self):
        """Entry-point source must produce data, not just pass the guard."""
        fake_result = SourceResult(name="quote", priority=50, data={"text": "Hello world!"})

        fake_source = MagicMock()
        fake_source.fetch.return_value = fake_result
        fake_source.name = "quote"

        fake_entry_point = MagicMock(spec=importlib.metadata.EntryPoint)
        fake_entry_point.name = "quote"
        fake_entry_point.load.return_value = lambda: fake_source

        config = BriefingConfig(
            sources={"quote": SourceConfig(name="quote", priority=50, enabled=True)},
            raw={"sources": {"quote": {"enabled": True, "priority": 50}}},
        )

        with patch("daily_briefing.orchestrator._ENTRY_POINTS", {"quote": fake_entry_point}):
            results = fetch_all(config)

        quote = next((r for r in results if r.name == "quote"), None)
        assert quote is not None
        assert quote.is_success()
        assert quote.data["text"] == "Hello world!"

    def test_fetch_single_works_for_entry_point_source(self):
        """fetch_single must also work via entry points."""
        fake_result = SourceResult(name="quote", priority=50, data={"text": "Hello!"})

        fake_entry_point = MagicMock(spec=importlib.metadata.EntryPoint)
        fake_entry_point.name = "quote"
        fake_entry_point.load.return_value = lambda: MagicMock(
            fetch=lambda cfg: fake_result,
            name="quote",
        )

        config = BriefingConfig(
            sources={"quote": SourceConfig(name="quote", priority=50, enabled=True)},
            raw={"sources": {"quote": {"enabled": True, "priority": 50}}},
        )

        with patch("daily_briefing.orchestrator._ENTRY_POINTS", {"quote": fake_entry_point}):
            result = fetch_single("quote", config)

        assert result.is_success()
        assert result.data["text"] == "Hello!"
