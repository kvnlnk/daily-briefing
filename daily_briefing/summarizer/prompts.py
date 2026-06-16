"""Prompt templates and formatting for LLM summarization.

Builds prompts using locale files (en.yaml, de.yaml) so the output
language matches the user's configured output.lang setting.
"""

from __future__ import annotations

import json
from typing import Any

from daily_briefing.config import OutputConfig
from daily_briefing.sources.base import SourceResult
from daily_briefing.summarizer.locales import load_locale


def build_prompt(
    results: list[SourceResult],
    yesterday_diff: dict[str, Any] | None = None,
    config: OutputConfig | None = None,
    lang: str | None = None,
    variant: str = "morning",
) -> str:
    """Build the LLM prompt from fetched data and config.

    The prompt is constructed using locale strings so the output
    language matches the user's config.

    Args:
        results: All fetched SourceResults (including errors).
        yesterday_diff: Optional diff from storage.history.diff().
        config: Output preferences (max_length, emoji, tone, lang).
        lang: Language code ('en', 'de'). Overrides config.output.lang.
        variant: Prompt variant ('morning', 'evening', 'weekly').

    Returns:
        A prompt string ready for the LLM.
    """
    if config is None:
        config = OutputConfig()

    # Resolve language: explicit param > config > default
    resolved_lang = lang or getattr(config, "lang", "en") or "en"
    loc = load_locale(resolved_lang)

    # Use variant-specific template if available, else locale default
    variant_prompts = loc.get("prompts", {}).get(variant, {})
    system_instruction = variant_prompts.get("system_instruction", loc.get("system_instruction", ""))
    structure_line = variant_prompts.get("structure", loc["format"].get("structure", ""))

    parts = [system_instruction]

    # Add yesterday context if available
    if yesterday_diff:
        parts.append(_format_diff_section(yesterday_diff, loc))

    # Add source data
    parts.append("---")
    parts.append(loc["format"]["header"])
    parts.append("")

    for i, result in enumerate(results, 1):
        parts.append(_format_source_section(i, result, loc))

    # Add output constraints
    parts.append("---")
    parts.append(loc["format"]["output"])
    parts.append(f"- {loc['format']['max_chars'].format(max_length=config.max_length)}")
    parts.append(f"- {loc['format']['tone'].format(tone=config.tone)}")
    if config.emoji:
        parts.append(f"- {loc['format']['emoji_on']}")
    else:
        parts.append(f"- {loc['format']['emoji_off']}")
    parts.append(f"- {structure_line}")
    parts.append(f"- {loc['format']['no_bullets']}")
    parts.append(f"- {loc['format']['mention_errors']}")
    parts.append("")
    parts.append(loc["format"]["generate"])

    return "\n".join(parts)


def _format_source_section(i: int, result: SourceResult, loc: dict) -> str:
    """Format a single source result for the prompt using locale strings."""
    raw_name = result.name.lower()
    label = loc.get("source_labels", {}).get(raw_name, result.name.upper())

    if not result.is_success():
        return f"{i}. {label}: {loc['format']['error_prefix']} — {result.error}\n"

    data = result.data or {}
    simplified = _simplify_data(result.name, data)
    return f"{i}. {label}:\n{json.dumps(simplified, ensure_ascii=False, indent=2)}\n"


def _format_diff_section(diff: dict[str, Any], loc: dict) -> str:
    """Format the yesterday comparison for the prompt."""
    lines = [loc["format"]["yesterday"]]
    for source, changes in diff.items():
        if isinstance(changes, dict):
            note = changes.get("note", str(changes))
            lines.append(loc["diff"]["note_label"].format(source=source, note=note))
    return "\n".join(lines)


def _simplify_data(source_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Remove verbose/irrelevant fields from source data before prompting.

    Keeps the essential fields the LLM needs — removes noise like URLs,
    raw IDs, and deeply nested structures.
    """
    simplified: dict[str, Any] = {}

    if source_name == "weather":
        # Single location
        if "location" in data:
            for key in ("location", "temperature", "feels_like", "humidity",
                         "wind_speed", "precipitation", "condition",
                         "high", "low", "rain_chance"):
                if key in data:
                    simplified[key] = data[key]
        # Multiple locations
        elif "locations" in data:
            simplified["locations"] = data["locations"]

    elif source_name == "calendar":
        simplified["total_events"] = data.get("total", 0)
        simplified["busy_hours"] = data.get("busy_hours", 0)
        simplified["events"] = [
            {"title": e["title"], "start": e["start"], "location": e.get("location", "")}
            for e in data.get("events", [])
        ]

    elif source_name == "github":
        simplified["total_issues"] = data.get("total_issues", 0)
        simplified["total_prs"] = data.get("total_prs", 0)
        simplified["issues"] = [
            {"title": i["title"]} for i in data.get("open_issues", [])
        ]
        simplified["prs"] = [
            {"title": p["title"]} for p in data.get("open_prs", [])
        ]

    elif source_name == "bahn":
        simplified["station"] = data.get("station", "")
        simplified["departures"] = [
            {"time": d.get("time", ""), "line": d.get("line", ""),
             "direction": d.get("direction", ""), "delay_minutes": d.get("delay_minutes", 0)}
            for d in data.get("departures", [])[:4]
        ]

    elif source_name == "reddit":
        simplified["total_posts"] = data.get("total_posts", 0)
        posts_list = []
        for sub, posts in data.get("subreddits", {}).items():
            for p in posts[:2]:
                posts_list.append({"subreddit": sub, "title": p["title"]})
        simplified["posts"] = posts_list

    elif source_name == "news":
        simplified["headlines"] = [
            {"source": h.get("source", ""), "title": h["title"]}
            for h in data.get("headlines", [])[:5]
        ]

    elif source_name == "email":
        simplified["unread_count"] = data.get("unread_count", 0)
        simplified["subjects"] = data.get("recent_subjects", [])

    else:
        simplified = data  # Unknown source: pass through as-is

    return simplified
