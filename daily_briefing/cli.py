"""CLI entry point for Daily Briefing.

Usage:
  daily-briefing                     # Full briefing (default)
  daily-briefing --source weather    # Single source
  daily-briefing setup               # Interactive setup wizard
  daily-briefing doctor              # Config diagnostics
  daily-briefing --help              # All options
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

import click

from daily_briefing.config import load_config
from daily_briefing.delivery import deliver
from daily_briefing.doctor import run_doctor
from daily_briefing.orchestrator import fetch_all, fetch_single
from daily_briefing.setup_wizard import run_setup
from daily_briefing.sources.base import SourceResult
from daily_briefing.storage.history import diff, load, save
from daily_briefing.summarizer import get_summarizer
from daily_briefing.summarizer.prompts import build_prompt


@click.group(invoke_without_command=True)
@click.option("--config", "-c", "config_path", default=None, help="Path to brief.yaml")
@click.option("--source", "-s", default=None, help="Fetch a single source (e.g. 'weather')")
@click.option("--json", "json_output", is_flag=True, help="Output raw JSON instead of formatted text")
@click.option("--verbose", "-v", is_flag=True, help="Print debug information")
@click.option("--list-sources", is_flag=True, help="List all installed data sources")
@click.option("--lang", default=None, help="Override output language (en/de)")
@click.option("--variant", default=None, help="Briefing variant (morning/evening/weekly)")
@click.option("--dry-run", is_flag=True, help="Fetch sources but skip summarize + deliver")
@click.option("--log-level", default="WARNING",
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
              help="Set logging level")
@click.pass_context
def cli(ctx: click.Context, config_path: str | None, source: str | None,
        json_output: bool, verbose: bool, list_sources: bool,
        lang: str | None, variant: str | None, dry_run: bool,
        log_level: str) -> None:
    """Fetch and display your daily briefing."""
    ctx.ensure_object(dict)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    # Store shared state in context
    ctx.obj["config_path"] = config_path
    ctx.obj["source"] = source
    ctx.obj["json_output"] = json_output
    ctx.obj["verbose"] = verbose
    ctx.obj["list_sources"] = list_sources
    ctx.obj["lang"] = lang
    ctx.obj["variant"] = variant
    ctx.obj["dry_run"] = dry_run

    # If no subcommand is invoked, run the briefing
    if ctx.invoked_subcommand is None:
        _run_briefing(ctx)


@cli.command()
@click.pass_context
def setup(ctx: click.Context) -> None:
    """Interactive setup wizard — creates brief.yaml and .env."""
    config_path = ctx.obj.get("config_path")
    run_setup(config_path=config_path)


@cli.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Check configuration and credentials."""
    config_path = ctx.obj.get("config_path")
    run_doctor(config_path=config_path)


@cli.command()
@click.option("--at", "at_time", default="07:00", help="Trigger time in HH:MM (24h)")
@click.option("--once", is_flag=True, help="Run once immediately then exit")
@click.pass_context
def daemon(ctx: click.Context, at_time: str, once: bool) -> None:
    """Run daily-briefing as a persistent daemon.

    Triggers the briefing once daily at the configured time.
    Default: once every day at 07:00 (configurable via --at or BRIEFING_SCHEDULE env var).
    """
    import zoneinfo
    from datetime import datetime

    from daily_briefing.scheduler import seconds_until_next_run

    config_path = ctx.obj.get("config_path")
    configuration = load_config(config_path)
    tz_name = configuration.output.timezone
    tz = zoneinfo.ZoneInfo(tz_name)

    # Allow env override
    at_time = os.environ.get("BRIEFING_SCHEDULE", at_time)

    if once:
        click.echo("Running briefing once (--once)...")
        _run_briefing_standalone(config_path)
        return

    click.echo(f"🕐 Daily Briefing daemon — next trigger at {at_time} ({tz_name})")
    click.echo("Press Ctrl+C to stop.")
    click.echo("")

    while True:
        now = datetime.now(tz)
        wait = seconds_until_next_run(now, at_time, tz)
        next_dt = datetime.fromtimestamp(now.timestamp() + wait, tz=tz)
        click.echo(
            f"  [sleeping {wait/3600:.1f}h until {next_dt.strftime('%H:%M %Z')}]",
            err=True,
        )
        import time as time_module
        time_module.sleep(wait)
        _run_briefing_standalone(config_path)


# ── Core briefing logic ──────────────────────────────────────────────


def _run_briefing(ctx: click.Context) -> None:
    """Execute the full briefing pipeline."""
    config_path = ctx.obj["config_path"]
    source = ctx.obj["source"]
    json_output = ctx.obj["json_output"]
    verbose = ctx.obj["verbose"]
    list_sources = ctx.obj["list_sources"]
    lang_override = ctx.obj["lang"]
    variant_override = ctx.obj["variant"]
    dry_run = ctx.obj["dry_run"]

    # List sources mode
    if list_sources:
        _list_sources()
        return

    configuration = load_config(config_path)

    # Resolve lang override
    if lang_override:
        configuration.output.lang = lang_override

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
    prompt = build_prompt(
        results,
        yesterday_diff,
        configuration.output,
        lang=lang_override or configuration.output.lang,
        variant=variant_override or "morning",
    )

    if verbose:
        click.echo("=== LLM PROMPT ===")
        click.echo(prompt)
        click.echo("=== END PROMPT ===")
        click.echo("")

    # Dry-run: stop before summarizer + delivery
    if dry_run:
        click.echo("── Dry Run ──")
        click.echo(f"Sources: {len(results)} fetched, {sum(1 for r in results if r.is_success())} OK")
        click.echo("Skipping summarization + delivery (--dry-run)")
        return

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


def _run_briefing_standalone(config_path: str | None = None) -> None:
    """Run the briefing pipeline without a click context (for daemon)."""
    from daily_briefing.orchestrator import fetch_all

    try:
        configuration = load_config(config_path)
        results = fetch_all(configuration)
        prompt = build_prompt(
            results,
            None,
            configuration.output,
            lang=configuration.output.lang,
            variant="morning",
        )
        provider_name = configuration.raw.get("summarizer", {}).get(
            "provider", "prompt-only"
        )
        summarizer = get_summarizer(provider_name)
        summary = summarizer.summarize(prompt)
        if summary.is_success():
            delivery_configs = configuration.raw.get(
                "delivery", [{"method": "stdout"}]
            )
            deliver(summary.text, delivery_configs)
        else:
            click.echo(f"Summarizer error: {summary.error}", err=True)
    except Exception as e:
        click.echo(f"Briefing failed: {e}", err=True)


def _list_sources() -> None:
    """List all installed sources via entry-point discovery."""
    from daily_briefing.orchestrator import discover_sources
    eps = discover_sources()
    builtin = {"weather", "github", "calendar", "bahn", "reddit", "news", "email"}
    click.echo("Installed sources:")
    for name in sorted(eps.keys()):
        ep = eps[name]
        try:
            cls = ep.load()
            cls()
            click.echo(f"  {name:15} {'(built-in)' if name in builtin else '(third-party)'}")
        except Exception:
            click.echo(f"  {name:15} (failed to load)")


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
    output: dict[str, Any] = {"data": data}
    if diff_data:
        output["yesterday_diff"] = diff_data
    click.echo(json.dumps(output, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    cli()
