"""Storage module — SQLite-backed history for yesterday-vs-today comparison.

Schema:
  briefings(id INTEGER PRIMARY KEY, date TEXT, source_name TEXT,
            data_json TEXT, created_at TEXT)

The `diff()` function compares today's results with yesterday's so the
LLM can say things like "3° wärmer als gestern" or "2 mehr PRs als gestern".
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from daily_briefing.sources.base import SourceResult

# Default DB location — same dir as the package, gitignored
DEFAULT_DB_PATH = Path(os.environ.get(
    "BRIEFING_DB_PATH",
    str(Path.home() / ".daily_briefing.db"),
))


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database, creating it if needed."""
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DEFAULT_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS briefings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source_name TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_briefings_date
        ON briefings(date, source_name)
    """)
    return conn


def save(results: list[SourceResult]) -> None:
    """Save today's results to the database.

    Only saves successful results (data is not None).
    Replaces any existing entries for today (idempotent).
    """
    today = datetime.date.today().isoformat()
    conn = _get_connection()
    try:
        with conn:
            # Delete any existing entries for today (idempotent save)
            conn.execute("DELETE FROM briefings WHERE date = ?", (today,))
            for r in results:
                if r.is_success() and r.data:
                    conn.execute(
                        "INSERT INTO briefings (date, source_name, data_json) VALUES (?, ?, ?)",
                        (today, r.name, json.dumps(r.data, default=str)),
                    )
    finally:
        conn.close()


def load(date: str | None = None) -> dict[str, dict[str, Any]]:
    """Load results for a given date.

    Args:
        date: ISO date string (e.g. '2026-06-15'). Defaults to today.

    Returns:
        Dict mapping source_name → data dict.
    """
    if date is None:
        date = datetime.date.today().isoformat()

    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT source_name, data_json FROM briefings WHERE date = ?",
            (date,),
        )
        results: dict[str, dict[str, Any]] = {}
        for row in cursor:
            results[row["source_name"]] = json.loads(row["data_json"])
        return results
    finally:
        conn.close()


def diff(
    today: dict[str, dict[str, Any]],
    yesterday: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compute a human-readable diff between today and yesterday.

    Returns a dict with per-source comparisons that the LLM can use
    to generate natural-language "vs yesterday" notes.

    Example return:
      {
        "weather": {"temperature_diff": 3.2, "note": "3.2°C wärmer"},
        "github": {"issue_diff": 2, "note": "2 offene Issues mehr"},
      }
    """
    changes: dict[str, Any] = {}

    # Weather: compare temperature
    if "weather" in today and "weather" in yesterday:
        t_data = today["weather"]
        y_data = yesterday["weather"]

        # Multi-location mode: {"locations": {"City": {...}}}
        if "locations" in t_data and "locations" in y_data:
            loc_diffs = {}
            all_locations = set(t_data["locations"]) | set(y_data["locations"])
            for loc in sorted(all_locations):
                t_loc = t_data["locations"].get(loc, {})
                y_loc = y_data["locations"].get(loc, {})
                t_temp = t_loc.get("temperature")
                y_temp = y_loc.get("temperature")
                if t_temp is not None and y_temp is not None:
                    diff_val = round(t_temp - y_temp, 1)
                    direction = "warmer" if diff_val > 0 else "colder" if diff_val < 0 else "same"
                    loc_diffs[loc] = {
                        "temperature_diff": diff_val,
                        "note": f"{abs(diff_val)}C {direction} than yesterday" if diff_val != 0 else "Temperature unchanged",
                    }
            if loc_diffs:
                changes["weather"] = {"locations": loc_diffs}

        # Single-location mode: top-level "temperature"
        elif "temperature" in t_data and "temperature" in y_data:
            t_temp = t_data["temperature"]
            y_temp = y_data["temperature"]
            if t_temp is not None and y_temp is not None:
                diff_val = round(t_temp - y_temp, 1)
                direction = "wärmer" if diff_val > 0 else "kälter" if diff_val < 0 else "gleich"
                changes["weather"] = {
                    "temperature_diff": diff_val,
                    "note": f"{abs(diff_val)}°C {direction} als gestern" if diff_val != 0 else "Temperatur unverändert",
                }

    # GitHub: compare issue/PR counts
    if "github" in today and "github" in yesterday:
        t_issues = today["github"].get("total_issues", 0)
        y_issues = yesterday["github"].get("total_issues", 0)
        t_prs = today["github"].get("total_prs", 0)
        y_prs = yesterday["github"].get("total_prs", 0)
        changes["github"] = {
            "issue_diff": t_issues - y_issues,
            "pr_diff": t_prs - y_prs,
        }

    return changes
