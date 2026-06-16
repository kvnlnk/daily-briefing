"""Setup wizard for Daily Briefing.

Interactive CLI wizard that helps users configure brief.yaml
and .env for the first time.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import click
import yaml


DEFAULT_CONFIG_PATH = "brief.yaml"
DEFAULT_ENV_PATH = ".env"


def run_setup(config_path: str | None = None, env_path: str | None = None) -> None:
    """Run the interactive setup wizard.

    Args:
        config_path: Path to write brief.yaml.
        env_path: Path to write .env.
    """
    config_path = config_path or DEFAULT_CONFIG_PATH
    env_path = env_path or DEFAULT_ENV_PATH

    click.echo("")
    click.echo("🌅 Daily Briefing — Setup Wizard")
    click.echo("=" * 40)
    click.echo("")

    # 1. Create brief.yaml from example
    _setup_config(config_path)

    # 2. Create .env from example (if it exists)
    _setup_env(env_path)

    # 3. Interactive questions
    config = _load_config_or_empty(config_path)

    click.echo("")
    _ask_weather(config, config_path)
    _ask_language(config, config_path)
    _ask_delivery(config, config_path)
    _ask_summarizer(config, config_path)

    click.echo("")
    click.echo("✅ Setup complete!")
    click.echo(f"   Config: {config_path}")
    click.echo(f"   Env:    {env_path}")
    click.echo("")
    click.echo("Next steps:")
    click.echo(f"  1. Edit {env_path} with your API keys (if needed)")
    click.echo(f"  2. Run 'daily-briefing doctor' to verify")
    click.echo(f"  3. Run 'daily-briefing' to get your first briefing")


def _setup_config(config_path: str) -> None:
    """Create brief.yaml from example if it doesn't exist."""
    example_path = Path.cwd() / "brief.example.yaml"
    target = Path(config_path)

    if not example_path.exists():
        click.echo("  ⚠️  brief.example.yaml not found — creating minimal config.")
        _write_minimal_config(config_path)
        return

    if target.exists():
        click.echo(f"  📄 {config_path} exists — keeping existing config.")
        return

    shutil.copy(str(example_path), str(target))
    click.echo(f"  ✅ Created {config_path} from example.")


def _setup_env(env_path: str) -> None:
    """Create .env from example if it doesn't exist."""
    example_path = Path.cwd() / ".env.example"
    target = Path(env_path)

    if not example_path.exists():
        click.echo("  ⚠️  .env.example not found — skipping.")
        return

    if target.exists():
        click.echo(f"  📄 {env_path} exists — keeping existing.")
        return

    shutil.copy(str(example_path), str(target))
    click.echo(f"  ✅ Created {env_path} from example.")


def _load_config_or_empty(config_path: str) -> dict:
    """Load existing config or return empty dict."""
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}


def _write_config(config: dict, config_path: str) -> None:
    """Write config back to YAML file."""
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def _write_minimal_config(config_path: str) -> bool:
    """Write a minimal working config."""
    config = {
        "sources": {
            "weather": {"enabled": True, "priority": 10},
            "calendar": {"enabled": False, "priority": 20},
            "github": {"enabled": False, "priority": 30},
            "bahn": {"enabled": False, "priority": 40},
            "reddit": {"enabled": False, "priority": 50},
            "news": {"enabled": False, "priority": 60},
            "email": {"enabled": False, "priority": 70},
        },
        "output": {
            "max_length": 800,
            "tone": "friendly",
            "emoji": True,
            "lang": "en",
            "timezone": "Europe/Berlin",
        },
    }
    _write_config(config, config_path)
    return True


def _ask_weather(config: dict, config_path: str) -> None:
    """Ask about weather location."""
    click.echo("🌤️  Weather Configuration")

    current = config.get("sources", {}).get("weather", {})
    current_locs = current.get("locations", [])

    if current_locs:
        click.echo(f"  Already configured: {', '.join(l.get('name', '?') for l in current_locs)}")
        if not click.confirm("  Add another location?", default=False):
            return

    city = click.prompt("  City name", default="London")
    lat = click.prompt("  Latitude", default="51.5074")
    lon = click.prompt("  Longitude", default="-0.1278")

    config.setdefault("sources", {}).setdefault("weather", {})
    config["sources"]["weather"].setdefault("locations", [])
    config["sources"]["weather"]["locations"].append({
        "name": city,
        "lat": float(lat),
        "lon": float(lon),
    })
    config["sources"]["weather"]["enabled"] = True

    _write_config(config, config_path)
    click.echo(f"  ✅ Added {city} to weather locations.")


def _ask_language(config: dict, config_path: str) -> None:
    """Ask about output language if not already configured."""
    current = config.get("output", {}).get("lang")
    if current:
        click.echo(f"  Language: {current} (already configured)")
        return
    lang = click.prompt("  Language (en/de)", default="en")
    config.setdefault("output", {})["lang"] = lang
    _write_config(config, config_path)
    click.echo(f"  ✅ Language set to {lang}.")


def _ask_delivery(config: dict, config_path: str) -> None:
    """Ask about delivery method."""
    if click.confirm("  Set up ntfy push notification?", default=False):
        topic = click.prompt("  ntfy topic name")
        config.setdefault("delivery", []).append({
            "method": "ntfy",
            "topic": topic,
        })
        _write_config(config, config_path)
        click.echo(f"  ✅ ntfy configured for topic '{topic}'.")


def _ask_summarizer(config: dict, config_path: str) -> None:
    """Ask about LLM summarizer."""
    if click.confirm("  Configure an LLM summarizer?", default=False):
        provider = click.prompt(
            "  Provider (ollama/openai/anthropic)",
            default="ollama",
        )
        config.setdefault("summarizer", {})["provider"] = provider
        _write_config(config, config_path)
        click.echo(f"  ✅ Summarizer set to {provider}.")
