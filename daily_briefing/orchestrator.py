"""Orchestrator — runs all enabled sources in parallel and collects results.

Loads config, discovers enabled sources, fetches them concurrently via
ThreadPoolExecutor, and returns results sorted by priority.

Each source is wrapped in a timeout + error handler so one slow or
broken source cannot block the entire briefing.
"""

from __future__ import annotations

import concurrent.futures
import importlib
import logging
from typing import Any

from daily_briefing.config import BriefingConfig, load_config
from daily_briefing.sources.base import SourceResult

# Source module → class name mapping.
# Add new sources here when creating additional modules.
# Key = source name (matches brief.yaml key), Value = (module, class)
SOURCE_REGISTRY: dict[str, tuple[str, str]] = {
    "weather": ("daily_briefing.sources.weather", "WeatherSource"),
    "github": ("daily_briefing.sources.github", "GitHubSource"),
    "calendar": ("daily_briefing.sources.calendar", "CalendarSource"),
    "bahn": ("daily_briefing.sources.bahn", "BahnSource"),
    "reddit": ("daily_briefing.sources.reddit", "RedditSource"),
    "news": ("daily_briefing.sources.news", "NewsSource"),
    "email": ("daily_briefing.sources.email", "EmailSource"),
}

# Per-source timeout in seconds.
# Some sources (DB API, IMAP) may be slow; keep it generous.
SOURCE_TIMEOUT = 20

logger = logging.getLogger(__name__)


def fetch_all(config: BriefingConfig | None = None) -> list[SourceResult]:
    """Fetch data from all enabled sources in parallel.

    Args:
        config: Parsed configuration. If None, loads from brief.yaml.

    Returns:
        List of SourceResults sorted by priority (lowest first).
        Failed sources are included with their error field populated.
    """
    if config is None:
        config = load_config()

    enabled = config.enabled_sources()
    if not enabled:
        logger.warning("No sources enabled in config — nothing to fetch")
        return []

    results: list[SourceResult] = []

    # Fetch all sources in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(enabled)) as executor:
        future_map: dict[concurrent.futures.Future, str] = {}

        for src_cfg in enabled:
            if src_cfg.name not in SOURCE_REGISTRY:
                results.append(SourceResult(
                    name=src_cfg.name,
                    priority=src_cfg.priority,
                    error=f"Unknown source '{src_cfg.name}' — not in SOURCE_REGISTRY",
                ))
                continue

            future = executor.submit(
                _fetch_one,
                src_cfg.name,
                config.raw,
            )
            future_map[future] = src_cfg.name

        for future in concurrent.futures.as_completed(future_map, timeout=SOURCE_TIMEOUT + 5):
            src_name = future_map[future]
            try:
                result = future.result(timeout=SOURCE_TIMEOUT)
                results.append(result)
            except concurrent.futures.TimeoutError:
                results.append(SourceResult(
                    name=src_name,
                    priority=config.sources[src_name].priority,
                    error=f"Timed out after {SOURCE_TIMEOUT}s",
                ))
            except Exception as e:
                results.append(SourceResult(
                    name=src_name,
                    priority=config.sources[src_name].priority,
                    error=f"Unexpected error: {e}",
                ))

    # Sort by priority (lowest first = most important)
    results.sort(key=lambda r: r.priority)
    return results


def fetch_single(source_name: str, config: BriefingConfig | None = None) -> SourceResult:
    """Fetch a single source (for testing/debugging).

    Args:
        source_name: e.g. 'weather', 'github'
        config: Parsed configuration.

    Returns:
        SourceResult from that source only.
    """
    if config is None:
        config = load_config()

    return _fetch_one(source_name, config.raw)


def _fetch_one(source_name: str, raw_config: dict[str, Any]) -> SourceResult:
    """Instantiate and call a single source module by name."""
    if source_name not in SOURCE_REGISTRY:
        return SourceResult(
            name=source_name,
            priority=99,
            error=f"Unknown source '{source_name}'",
        )

    module_path, class_name = SOURCE_REGISTRY[source_name]
    try:
        module = importlib.import_module(module_path)
        source_class = getattr(module, class_name)
        source = source_class()
        return source.fetch(raw_config)
    except ImportError as e:
        return SourceResult(
            name=source_name,
            priority=99,
            error=f"Cannot import {module_path}: {e}",
        )
    except Exception as e:
        return SourceResult(
            name=source_name,
            priority=99,
            error=f"Error instantiating {class_name}: {e}",
        )
