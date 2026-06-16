"""Prompt templates and formatting for LLM summarization.

This module builds the prompt that the controlling LLM (Hermes) uses to
generate the final WhatsApp briefing message. The prompt includes:

1. Source data from all fetched modules
2. Yesterday's comparison (from storage diff)
3. Output format constraints (max chars, emoji, tone)
"""

from __future__ import annotations

from typing import Any

from daily_briefing.config import BriefingConfig, OutputConfig
from daily_briefing.sources.base import SourceResult


def build_prompt(
    results: list[SourceResult],
    yesterday_diff: dict[str, Any] | None = None,
    config: OutputConfig | None = None,
) -> str:
    """Build the LLM prompt from fetched data and config.

    The prompt is structured so the LLM can produce a concise,
    WhatsApp-friendly message.

    Args:
        results: All fetched SourceResults (including errors).
        yesterday_diff: Optional diff from storage.history.diff().
        config: Output preferences (max_length, emoji, tone).

    Returns:
        A prompt string ready for the LLM.
    """
    if config is None:
        config = OutputConfig()

    parts = [_SYSTEM_INSTRUCTION]

    # Add yesterday context if available
    if yesterday_diff:
        parts.append(format_diff_section(yesterday_diff))

    # Add source data
    parts.append("---")
    parts.append("HEUTIGE DATEN:")
    parts.append("")

    for i, result in enumerate(results, 1):
        parts.append(format_source_section(i, result))

    # Add output constraints
    parts.append("---")
    parts.append("AUSGABE-FORMAT:")
    parts.append(f"- Maximal {config.max_length} Zeichen (WhatsApp-kompatibel)")
    parts.append(f"- Ton: {config.tone}")
    if config.emoji:
        parts.append("- Verwende Emoji wo passend")
    else:
        parts.append("- Keine Emoji")
    parts.append("- Struktur: HEADER → Wetter → Termine → GitHub → Bahn → News → Reddit → SIGN-OFF")
    parts.append("- Keine Bullet-Points oder Aufzählungen — ein Fließtext")
    parts.append("- Erwähne fehlerhafte Quellen kurz (z.B. 'Bahn-Daten heute nicht verfügbar')")
    parts.append("")
    parts.append("Generiere JETZT die WhatsApp-Nachricht:")

    return "\n".join(parts)


def format_source_section(i: int, result: SourceResult) -> str:
    """Format a single source result for the prompt."""
    source_name = result.name.upper()
    if not result.is_success():
        return f"{i}. {source_name}: NICHT VERFÜGBAR — {result.error}\n"

    # Simplify the data for the prompt — exclude verbose fields
    data = result.data or {}
    simplified = _simplify_data(result.name, data)
    import json
    return f"{i}. {source_name}:\n{json.dumps(simplified, ensure_ascii=False, indent=2)}\n"


def format_diff_section(diff: dict[str, Any]) -> str:
    """Format the yesterday comparison for the prompt."""
    lines = ["VERGLEICH MIT GESTERN:"]
    for source, changes in diff.items():
        if isinstance(changes, dict):
            note = changes.get("note", str(changes))
            lines.append(f"  {source}: {note}")
    return "\n".join(lines)


def _simplify_data(source_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Remove verbose/irrelevant fields from source data before prompting.

    Keeps the essential fields the LLM needs — removes noise like URLs,
    raw IDs, and deeply nested structures.
    """
    simplified = {}

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


_SYSTEM_INSTRUCTION = """Du bist der Daily Briefing Bot. Fasse die folgenden Daten in EINE
WhatsApp-Nachricht zusammen. Die Nachricht soll informativ, freundlich
und auf den Punkt sein — so dass der Nutzer morgens in 5 Sekunden alles
Wichtige erfasst hat.

Priorität: Wetter > Termine > GitHub > Bahn > News > Reddit.
Erwähne fehlerhafte Quellen nur kurz (z.B. "Bahn heute nicht verfügbar").
"""
