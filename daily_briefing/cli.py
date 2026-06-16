"""CLI entry point for Daily Briefing.

Usage:
  python -m daily_briefing              # Full briefing
  python -m daily_briefing --source weather  # Single source
  python -m daily_briefing --json       # Raw JSON output
  python -m daily_briefing --verbose    # Debug output
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

import click

from daily_briefing.config import load_config
from daily_briefing.delivery import deliver
from daily_briefing.orchestrator import fetch_all, fetch_single
from daily_briefing.sources.base import SourceResult
from daily_briefing.storage.history import diff, load, save
from daily_briefing.summarizer import get_summarizer
from daily_briefing.summarizer.prompts import build_prompt


@click.command()
@click.option("--source", "-s", default=None, help="Fetch a single source (e.g. 'weather', 'github')")
@click.option("--config", "-c", "config_path", default=None, help="Path to brief.yaml")
@click.option("--json", "json_output", is_flag=True, help="Output raw JSON instead of formatted text")
@click.option("--verbose", "-v", is_flag=True, help="Print debug information")
@click.option("--list-sources", is_flag=True, help="List all installed data sources")
@click.option("--log-level", default="WARNING", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]), help="Set logging level")
def main(source: str | None, config_path: str | None, json_output: bool, verbose: bool, log_level: str, list_sources: bool = False) -> None:
    """Fetch and display your daily briefing."""

    logging.basicConfig(level=getattr(logging, log_level.upper()), format="%(levelname)s:%(name)s:%(message)s")

    # List sources mode
    if list_sources:
        from daily_briefing.orchestrator import discover_sources
        eps = discover_sources()
        click.echo("Installed sources:")
        for name in sorted(eps.keys()):
            ep = eps[name]
            try:
                cls = ep.load()
                src = cls()
                click.echo(f"  {name:15} {'(built-in)' if name in ('weather','github','calendar','bahn','reddit','news','email') else '(third-party)'}")
            except Exception:
                click.echo(f"  {name:15} (failed to load)")
        return

    configuration = load_config(config_path)

    # Single source mode (for testing)
    if source:
        result = fetch_single(source, configuration)
        if json_output:
            _print_json(result)
        else:
            _print_source_result(result, verbose)
        return

    # Full briefing mode
    results = fetch_all(configuration)

    if verbose:
        click.echo(f"Fetched {len(results)} sources:", err=True)
        for r in results:
            status = "[ok]" if r.is_success() else "[err]"
            click.echo(f"  {status} {r.name}", err=True)

    # Save to history
    save(results)

    # Load yesterday for comparison
    from datetime import date, timedelta
    yesterday_diff = None
    if configuration.output.include_diff:
        today_data = load()
        yesterday_data = load((date.today() - timedelta(days=1)).isoformat())
        yesterday_diff = diff(today_data, yesterday_data) if yesterday_data else None

    if json_output:
        _print_json(results, yesterday_diff)
        return

    # Build LLM prompt
    prompt = build_prompt(results, yesterday_diff, configuration.output, lang=configuration.output.lang)

    if verbose:
        click.echo("=== LLM PROMPT ===")
        click.echo(prompt)
        click.echo("=== END PROMPT ===")
        click.echo("")

    # Summarize via configured provider
    provider_name = configuration.raw.get("summarizer", {}).get("provider", "prompt-only")
    try:
        summarizer = get_summarizer(provider_name)
        summary = summarizer.summarize(prompt)

        if summary.is_success():
            delivery_configs = configuration.raw.get("delivery", [{"method": "stdout"}])
            if not delivery_configs:
                delivery_configs = [{"method": "stdout"}]  # always fall back
            results = deliver(summary.text, delivery_configs)
            for r in results:
                if not r.success:
                    click.echo(f"Delivery failed ({r.channel}): {r.error}", err=True)
        else:
            click.echo(f"Summarizer error ({provider_name}): {summary.error}", err=True)
            click.echo("")  # Fallback: print the raw prompt
            click.echo(prompt)
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        click.echo(prompt)


def _print_source_result(result: SourceResult, verbose: bool) -> None:
    """Pretty-print a single source result."""
    if verbose:
        if result.is_success():
            click.echo(json.dumps(result.data, ensure_ascii=False, indent=2, default=str))
        else:
            click.echo(f"ERROR: {result.error}", err=True)
        return

    if result.is_success():
        click.echo(json.dumps(result.data, ensure_ascii=False, default=str))
    else:
        click.echo(f"ERROR: {result.error}", err=True)
        sys.exit(1)


def _print_json(data: Any, diff_data: Any = None) -> None:
    """Print results as JSON for programmatic consumption."""
    output = {"data": data}
    if diff_data:
        output["yesterday_diff"] = diff_data
    click.echo(json.dumps(output, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
