"""Tests for daily_briefing.config — YAML config loading."""

from pathlib import Path

import pytest
import yaml

from daily_briefing.config import BriefingConfig, OutputConfig, SourceConfig, load_config


class TestSourceConfig:
    def test_from_dict_enabled(self):
        cfg = SourceConfig.from_dict("weather", {"enabled": True, "priority": 10})
        assert cfg.name == "weather"
        assert cfg.enabled is True
        assert cfg.priority == 10

    def test_from_dict_disabled(self):
        cfg = SourceConfig.from_dict("email", {"enabled": False})
        assert cfg.enabled is False
        assert cfg.priority == 99  # default

    def test_from_dict_defaults(self):
        cfg = SourceConfig.from_dict("test", {})
        assert cfg.enabled is True
        assert cfg.priority == 99


class TestOutputConfig:
    def test_defaults(self):
        cfg = OutputConfig()
        assert cfg.max_length == 800
        assert cfg.include_diff is True
        assert cfg.tone == "friendly"
        assert cfg.emoji is True
        assert cfg.timezone == "Europe/Berlin"

    def test_custom_values(self):
        cfg = OutputConfig(max_length=500, tone="concise", emoji=False)
        assert cfg.max_length == 500
        assert cfg.tone == "concise"
        assert cfg.emoji is False


class TestBriefingConfig:
    def test_enabled_sources_filters_disabled(self):
        cfg = BriefingConfig(
            sources={
                "a": SourceConfig("a", enabled=True, priority=10),
                "b": SourceConfig("b", enabled=False, priority=20),
                "c": SourceConfig("c", enabled=True, priority=30),
            },
        )
        enabled = cfg.enabled_sources()
        assert len(enabled) == 2
        assert all(s.enabled for s in enabled)

    def test_enabled_sources_sorted_by_priority(self):
        cfg = BriefingConfig(
            sources={
                "a": SourceConfig("a", enabled=True, priority=30),
                "b": SourceConfig("b", enabled=True, priority=10),
                "c": SourceConfig("c", enabled=True, priority=20),
            },
        )
        assert [s.name for s in cfg.enabled_sources()] == ["b", "c", "a"]


class TestLoadConfig:
    def test_loads_brief_yaml(self, tmp_path: Path):
        """Load a minimal brief.yaml and verify structure."""
        config_data = {
            "sources": {
                "weather": {"enabled": True, "priority": 10},
                "news": {"enabled": True, "priority": 60},
            },
            "output": {
                "max_length": 500,
                "tone": "concise",
            },
        }
        config_path = tmp_path / "brief.yaml"
        config_path.write_text(yaml.dump(config_data))

        cfg = load_config(str(config_path))
        assert "weather" in cfg.sources
        assert "news" in cfg.sources
        assert cfg.sources["weather"].priority == 10
        assert cfg.output.max_length == 500
        assert cfg.output.tone == "concise"

    def test_raw_config_preserved(self, tmp_path: Path):
        """The raw YAML dict should be passed through for source modules."""
        config_data = {
            "sources": {
                "weather": {
                    "enabled": True,
                    "locations": [{"name": "Berlin", "lat": 52.52, "lon": 13.40}],
                },
            },
        }
        config_path = tmp_path / "brief.yaml"
        config_path.write_text(yaml.dump(config_data))

        cfg = load_config(str(config_path))
        weather_raw = cfg.raw["sources"]["weather"]
        assert weather_raw["locations"][0]["name"] == "Berlin"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/brief.yaml")
