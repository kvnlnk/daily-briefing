"""Tests for variant support — config filtering and variant prompts."""

from __future__ import annotations

from daily_briefing.config import BriefingConfig, OutputConfig, SourceConfig
from daily_briefing.sources.base import SourceResult
from daily_briefing.summarizer.prompts import build_prompt


class TestVariantConfigFiltering:
    """Variant-based source filtering in BriefingConfig."""

    def make_config(self, variant: str = "morning", variants_config: dict | None = None) -> BriefingConfig:
        raw = {
            "output": {"variant": variant},
            "variants": variants_config or {},
        }
        sources = {
            "weather": SourceConfig(name="weather", priority=10, enabled=True),
            "calendar": SourceConfig(name="calendar", priority=20, enabled=True),
            "github": SourceConfig(name="github", priority=30, enabled=True),
            "bahn": SourceConfig(name="bahn", priority=40, enabled=True),
            "reddit": SourceConfig(name="reddit", priority=50, enabled=True),
            "news": SourceConfig(name="news", priority=60, enabled=True),
        }
        return BriefingConfig(sources=sources, raw=raw)

    def test_morning_includes_all(self):
        config = self.make_config(variant="morning", variants_config={
            "morning": {"sources": ["weather", "calendar", "github", "bahn", "reddit", "news"]},
        })
        enabled = config.enabled_sources()
        names = {s.name for s in enabled}
        assert names == {"weather", "calendar", "github", "bahn", "reddit", "news"}

    def test_evening_filters_sources(self):
        config = self.make_config(variant="evening", variants_config={
            "evening": {"sources": ["weather", "calendar", "news"]},
        })
        enabled = config.enabled_sources()
        names = {s.name for s in enabled}
        assert names == {"weather", "calendar", "news"}
        assert "github" not in names
        assert "bahn" not in names

    def test_weekly_includes_different_set(self):
        config = self.make_config(variant="weekly", variants_config={
            "weekly": {"sources": ["weather", "calendar", "github", "news"]},
        })
        enabled = config.enabled_sources()
        names = {s.name for s in enabled}
        assert names == {"weather", "calendar", "github", "news"}

    def test_no_variants_config_returns_all(self):
        config = self.make_config(variant="morning", variants_config=None)
        enabled = config.enabled_sources()
        assert len(enabled) == 6  # all sources

    def test_variant_with_unknown_source_name(self):
        config = self.make_config(variant="morning", variants_config={
            "morning": {"sources": ["weather", "nonexistent_source"]},
        })
        enabled = config.enabled_sources()
        names = {s.name for s in enabled}
        assert names == {"weather"}  # nonexistent is filtered out


class TestVariantPrompts:
    """Variant-specific prompt templates."""

    def make_result(self) -> list[SourceResult]:
        return [SourceResult(name="weather", priority=10, data={"location": "Berlin", "condition": "Sunny"})]

    def test_morning_prompt(self):
        prompt = build_prompt(self.make_result(), config=OutputConfig(max_length=100), lang="en", variant="morning")
        assert "Daily Briefing Bot" in prompt
        assert "5 seconds" in prompt
        assert "Sign-off" in prompt

    def test_evening_prompt(self):
        prompt = build_prompt(self.make_result(), config=OutputConfig(max_length=100), lang="en", variant="evening")
        assert "Evening Briefing Bot" in prompt
        assert "evening recap" in prompt
        assert "tomorrow" in prompt

    def test_weekly_prompt(self):
        prompt = build_prompt(self.make_result(), config=OutputConfig(max_length=100), lang="en", variant="weekly")
        assert "Weekly Briefing Bot" in prompt
        assert "week" in prompt.lower()

    def test_morning_vs_evening_differ(self):
        morning = build_prompt(self.make_result(), config=OutputConfig(), lang="en", variant="morning")
        evening = build_prompt(self.make_result(), config=OutputConfig(), lang="en", variant="evening")
        assert morning != evening

    def test_de_variant_prompts(self):
        morning = build_prompt(self.make_result(), config=OutputConfig(), lang="de", variant="morning")
        assert "Daily Briefing Bot" in morning

        evening = build_prompt(self.make_result(), config=OutputConfig(), lang="de", variant="evening")
        assert "Abend" in evening

        weekly = build_prompt(self.make_result(), config=OutputConfig(), lang="de", variant="weekly")
        assert "Wochen" in weekly
