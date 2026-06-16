"""Configuration loader and types for Daily Briefing.

Reads brief.yaml and .env into typed dataclasses.
Per-source config is passed to each source's fetch() method unmodified —
the source module is responsible for reading its own section.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SourceConfig:
    """Per-source configuration section from brief.yaml."""

    name: str
    enabled: bool = True
    priority: int = 99

    @classmethod
    def from_dict(cls, name: str, data: dict) -> SourceConfig:
        return cls(
            name=name,
            enabled=data.get("enabled", True),
            priority=data.get("priority", 99),
        )


@dataclass
class OutputConfig:
    """Output formatting preferences."""

    max_length: int = 800
    include_diff: bool = True
    tone: str = "friendly"
    emoji: bool = True
    timezone: str = "Europe/Berlin"
    lang: str = "en"


@dataclass
class BriefingConfig:
    """Top-level configuration for a Daily Briefing run."""

    sources: dict[str, SourceConfig] = field(default_factory=dict)
    output: OutputConfig = field(default_factory=OutputConfig)
    # Raw YAML dict preserved for source modules to read their sections
    raw: dict = field(default_factory=dict)

    def enabled_sources(self) -> list[SourceConfig]:
        """Return enabled sources sorted by priority (lowest first).

        If a variant is configured in output.variant and the variants.*.sources
        list exists, only sources listed for that variant are returned.
        """
        enabled = [s for s in self.sources.values() if s.enabled]

        # Apply variant filtering
        variant_name = self.raw.get("output", {}).get("variant", "morning")
        variants = self.raw.get("variants", {})
        variant_sources = variants.get(variant_name, {}).get("sources") if variants else None

        if variant_sources is not None:
            enabled = [s for s in enabled if s.name in variant_sources]

        return sorted(enabled, key=lambda s: s.priority)


def load_config(path: Path | str | None = None) -> BriefingConfig:
    """Load briefing configuration from YAML file.

    Searches in order:
    1. Explicit `path` argument
    2. `BRIEF_CONFIG` env var
    3. `brief.yaml` in current directory
    4. `~/.config/daily-briefing/brief.yaml`
    """
    if path is None:
        path = os.environ.get("BRIEF_CONFIG", "")
        if not path:
            for candidate in (Path.cwd() / "brief.yaml", Path.home() / ".config" / "daily-briefing" / "brief.yaml"):
                if candidate.exists():
                    path = str(candidate)
                    break

    if not path or not Path(path).exists():
        raise FileNotFoundError(
            "No brief.yaml found. Create one from the example in the repo root, "
            "or set BRIEF_CONFIG=/path/to/brief.yaml"
        )

    with open(path) as f:
        raw = yaml.safe_load(f)

    sources_raw = raw.get("sources", {})
    sources = {}
    for name, data in sources_raw.items():
        sources[name] = SourceConfig.from_dict(name, data)

    output_raw = raw.get("output", {})
    output = OutputConfig(
        max_length=output_raw.get("max_length", 800),
        include_diff=output_raw.get("include_diff", True),
        tone=output_raw.get("tone", "friendly"),
        emoji=output_raw.get("emoji", True),
        timezone=output_raw.get("timezone", "Europe/Berlin"),
        lang=output_raw.get("lang", "en"),
    )

    return BriefingConfig(sources=sources, output=output, raw=raw)
