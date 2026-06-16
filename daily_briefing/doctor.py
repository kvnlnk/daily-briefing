"""Doctor — configuration diagnostics for Daily Briefing.

Checks config, credentials, sources, and summarizer availability.
Acts as a health check before running the actual briefing.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
import yaml

from daily_briefing.config import load_config
from daily_briefing.orchestrator import SOURCE_REGISTRY
from daily_briefing.summarizer import PROVIDERS as SUMMARIZER_PROVIDERS


def run_doctor(config_path: str | None = None) -> bool:
    """Run diagnostics and return True if everything is OK.

    Args:
        config_path: Optional path to brief.yaml.

    Returns:
        True if all checks pass, False otherwise.
    """
    all_ok = True

    click.echo("")
    click.echo("Daily Briefing — Config Health Check")
    click.echo("━" * 40)

    # Step 1: Check config file
    click.echo("")
    click.echo("📁 Config:")

    if config_path and os.path.exists(config_path):
        click.echo(f"  {config_path}  ✅")
    else:
        # Try automatic discovery
        found = _find_config()
        if found:
            config_path = str(found)
            click.echo(f"  {found}  ✅")
        else:
            click.echo(f"  No brief.yaml found  ❌")
            click.echo("  Run 'daily-briefing setup' to create one.")
            all_ok = False

    # Step 2: Load and validate config
    click.echo("")
    click.echo("⚙️  Output:")
    config = None
    if config_path and os.path.exists(config_path):
        try:
            config = load_config(config_path)
            click.echo(f"  Language: {config.output.lang}")
            click.echo(f"  Timezone: {config.output.timezone}")
            click.echo(f"  Emoji:    {'on' if config.output.emoji else 'off'}")
            click.echo(f"  Variant:  {config.raw.get('output', {}).get('variant', 'morning')}")
        except Exception as e:
            click.echo(f"  Failed to parse config: {e}  ❌", err=True)
            all_ok = False

    # Step 3: Check sources
    click.echo("")
    click.echo("📡 Sources:")
    enabled_count = 0
    total_count = len(SOURCE_REGISTRY)

    if config:
        enabled = config.enabled_sources()
        enabled_count = len(enabled)
        enabled_names = {s.name for s in enabled}

        for name in sorted(SOURCE_REGISTRY):
            if name in enabled_names:
                click.echo(f"  {name:12} ✅ enabled")
            else:
                click.echo(f"  {name:12} ⚠️  disabled")
    else:
        for name in sorted(SOURCE_REGISTRY):
            click.echo(f"  {name:12} ⚠️  (no config loaded)")

    click.echo(f"  {'─' * 30}")
    click.echo(f"  {enabled_count}/{total_count} sources enabled")

    # Step 4: Check summarizer
    click.echo("")
    click.echo("🧠 Summarizer:")
    provider = "prompt-only"
    if config:
        provider = config.raw.get("summarizer", {}).get("provider", "prompt-only")

    provider_info = {"prompt-only": "no API key required"}.get(provider, "")
    if provider in SUMMARIZER_PROVIDERS:
        click.echo(f"  {provider:12} ✅ {provider_info}")
    else:
        click.echo(f"  {provider:12} ❌ unknown provider")
        all_ok = False

    # Step 5: Check delivery
    click.echo("")
    click.echo("📬 Delivery:")
    delivery_configs = [{"method": "stdout"}]
    if config:
        delivery_configs = config.raw.get("delivery", delivery_configs)
        if not delivery_configs:
            delivery_configs = [{"method": "stdout"}]

    for dc in delivery_configs:
        method = dc.get("method", "stdout")
        if method == "stdout":
            click.echo(f"  {method:12} ✅")
        elif method == "ntfy":
            topic = dc.get("topic", "") or os.environ.get("NTFY_TOPIC", "")
            if topic:
                click.echo(f"  ntfy        ✅ topic='{topic}'")
            else:
                click.echo(f"  ntfy        ⚠️  no topic configured")
                all_ok = False
        else:
            click.echo(f"  {method:12} ⚠️  unknown method")
            all_ok = False

    # Summary
    click.echo("")
    if all_ok:
        click.echo("✅ All checks passed.")
    else:
        click.echo("⚠️  Some checks failed — review above.")

    return all_ok


def _find_config() -> Path | None:
    """Find brief.yaml via automatic discovery."""
    for candidate in (Path.cwd() / "brief.yaml", Path.home() / ".config" / "daily-briefing" / "brief.yaml"):
        if candidate.exists():
            return candidate
    return None
