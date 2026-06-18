"""Daily Briefing skill for Hermes Agent.

Install:
    cp integrations/hermes/briefing_skill.py ~/.hermes/profiles/default/skills/

Then in Hermes:
    /skill briefing_skill
    run_briefing()
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


def run_briefing(
    config_path: str | None = None,
    variant: str = "morning",
    lang: str = "en",
    timeout: int = 30,
) -> dict[str, Any]:
    """Fetch today's briefing data and return structured JSON.

    This function is designed to be called from Hermes Agent skills.
    It invokes the installed ``daily-briefing`` CLI with ``--json --dry-run``
    to fetch all source data without an LLM summarization pass.

    Args:
        config_path: Path to brief.yaml (optional, uses auto-discovery).
        variant: Briefing variant (morning/evening/weekly).
        lang: Output language (en/de).
        timeout: Max seconds to wait for the CLI.

    Returns:
        Dict with ``data`` (list of source results) and optionally
        ``error`` if the CLI failed.
    """
    cmd = ["daily-briefing", "--json", "--dry-run", "--variant", variant, "--lang", lang]
    if config_path:
        cmd.extend(["--config", config_path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"daily-briefing timed out after {timeout}s"}
    except FileNotFoundError:
        return {
            "error": (
                "daily-briefing CLI not found. "
                "Install it with: pip install git+https://github.com/kvnlnk/daily-briefing"
            )
        }

    if result.returncode != 0:
        return {
            "error": (
                f"daily-briefing exited with code {result.returncode}: "
                f"{result.stderr.strip()}"
            ),
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON output: {e}"}


def run_full_briefing(
    config_path: str | None = None,
    variant: str = "morning",
    lang: str = "en",
    timeout: int = 60,
) -> dict[str, Any]:
    """Run the full briefing including LLM summarization and delivery.

    Unlike ``run_briefing()``, this does *not* use --dry-run, so the
    configured summarizer and delivery channels are invoked.
    """
    cmd = ["daily-briefing", "--json", "--variant", variant, "--lang", lang]
    if config_path:
        cmd.extend(["--config", config_path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Full briefing timed out after {timeout}s"}
    except FileNotFoundError:
        return {"error": "daily-briefing CLI not found"}

    if result.returncode != 0:
        return {
            "error": (
                f"Full briefing failed (exit {result.returncode}): "
                f"{result.stderr.strip()}"
            ),
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON output: {e}"}
