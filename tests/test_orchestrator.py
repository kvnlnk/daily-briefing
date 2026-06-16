"""Tests for orchestrator — parallel fetch, timeout, error handling."""
import pytest
from daily_briefing.orchestrator import fetch_all, fetch_single
from daily_briefing.config import BriefingConfig, SourceConfig


class TestOrchestrator:
    def test_no_enabled_sources_returns_empty(self):
        cfg = BriefingConfig(sources={}, raw={"sources": {}})
        results = fetch_all(cfg)
        assert results == []

    def test_unknown_source_returns_error(self):
        cfg = BriefingConfig(
            sources={"nonexistent": SourceConfig("nonexistent", enabled=True)},
            raw={"sources": {"nonexistent": {"enabled": True}}},
        )
        results = fetch_all(cfg)
        assert len(results) == 1
        assert "Unknown" in results[0].error

    def test_results_sorted_by_priority(self):
        cfg = BriefingConfig(
            sources={
                "weather": SourceConfig("weather", enabled=True, priority=10),
                "news": SourceConfig("news", enabled=True, priority=60),
            },
            raw={"sources": {"weather": {"enabled": True}, "news": {"enabled": True}}},
        )
        results = fetch_all(cfg)
        assert results[0].name == "weather"
        assert results[1].name == "news"

    def test_fetch_single_known_source(self):
        cfg = BriefingConfig(
            sources={"weather": SourceConfig("weather", enabled=True)},
            raw={},
        )
        result = fetch_single("weather", cfg)
        assert result.name == "weather"
