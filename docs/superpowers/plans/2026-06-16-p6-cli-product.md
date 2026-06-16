# P6 — CLI as Real Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Turn the CLI into a proper product with console_scripts entrypoint, `daily-briefing setup` wizard, `daily-briefing doctor` diagnostics, and sensible flags.

---

### Task 1: Add console_scripts entrypoint

**Files:**
- Modify: `pyproject.toml`

```toml
[project.scripts]
daily-briefing = "daily_briefing.cli:main"
```

**Also rename `__main__.py`** to avoid confusion:
```python
"""Allow `python -m daily_briefing` to run the CLI."""
from daily_briefing.cli import main
main()
```

- [ ] Step 1: Add [project.scripts] to pyproject.toml
- [ ] Step 2: pip install -e .
- [ ] Step 3: `daily-briefing --help` must work
- [ ] Step 4: `python -m daily_briefing` must still work
- [ ] Step 5: Commit

---

### Task 2: Create `daily-briefing setup` command

**Files:**
- Create: `daily_briefing/setup_wizard.py`
- Modify: `daily_briefing/cli.py` (add click group)

**CLI structure becomes a click group:**
```python
@click.group()
@click.version_option("0.1.0")
@click.option("--config", "-c", default=None)
@click.option("--lang", default=None)
@click.option("--variant", default="morning")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def cli(ctx, config, lang, variant, dry_run):
    """Daily Briefing — your morning, summarized."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ...

@cli.command()
@click.pass_context
def setup(ctx):
    """Interactive setup wizard."""
    from daily_briefing.setup_wizard import run_setup
    run_setup()

@cli.command()
@click.pass_context
def doctor(ctx):
    """Check configuration and credentials."""
    ...

@cli.command()
@click.option("--source", "-s")
@click.option("--json", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
def run(ctx, source, json, verbose):
    """Run the briefing (default command)."""
    ...

# Default: if no subcommand, run 'run'
cli.add_command(run, name=None)
```

Wait — Click doesn't support unnamed default commands well. Better approach: keep the existing flat CLI but add subcommands:

```python
@click.group(invoke_without_command=True)
@click.option(...)
@click.pass_context
def cli(ctx, ...):
    """..."""
    ctx.ensure_object(dict)
    ...
    if ctx.invoked_subcommand is None:
        # Run briefing by default
        ...

cli.add_command(setup)
cli.add_command(doctor)
```

**setup_wizard.py:**
```python
import click, os, shutil, yaml

def run_setup(config_path: str = "brief.yaml", env_path: str = ".env"):
    click.echo("🌅 Daily Briefing Setup")
    click.echo("======================")

    # 1. Copy brief.example.yaml → brief.yaml
    if os.path.exists(config_path):
        if not click.confirm(f"{config_path} exists. Overwrite?"):
            # Just ensure it's valid
            pass
    else:
        shutil.copy("brief.example.yaml", config_path)
        click.echo(f"  Created {config_path}")

    # 2. Copy .env.example → .env
    if os.path.exists(env_path):
        click.echo(f"  {env_path} exists — modify manually")
    else:
        shutil.copy(".env.example", env_path)
        click.echo(f"  Created {env_path}")

    # 3. Interactive questions
    click.echo("\nLet's configure your first location:")
    city = click.prompt("City name", default="London")
    lat = click.prompt("Latitude", default="51.5074")
    lon = click.prompt("Longitude", default="-0.1278")

    # Update brief.yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)
    config.setdefault("sources", {}).setdefault("weather", {})["locations"] = [
        {"name": city, "lat": float(lat), "lon": float(lon)}
    ]
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    click.echo(f"  Added {city} to weather locations")

    # 4. Language
    lang = click.prompt("Language (en/de)", default="en")
    config.setdefault("output", {})["lang"] = lang
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # 5. Ntfy topic (optional)
    if click.confirm("Set up ntfy push notification?", default=False):
        topic = click.prompt("ntfy topic name")
        config.setdefault("delivery", []).append({"method": "ntfy", "topic": topic})
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        click.echo(f"  ntfy configured for topic '{topic}'")

    # 6. LLM provider (optional)
    if click.confirm("Configure an LLM summarizer?", default=False):
        provider = click.prompt("Provider (ollama/openai/anthropic)", default="ollama")
        config.setdefault("summarizer", {})["provider"] = provider
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    click.echo("\n✅ Setup complete! Run 'daily-briefing doctor' to verify.")
```

- [ ] Step 1: Write test for setup wizard (mocked)

- [ ] Step 2: Refactor CLI to click group

- [ ] Step 3: Implement setup_wizard

- [ ] Step 4: Test: `daily-briefing setup` creates config files

- [ ] Step 5: Commit

---

### Task 3: Create `daily-briefing doctor` command

**Files:**
- Create: `daily_briefing/doctor.py`
- Modify: `daily_briefing/cli.py` (add doctor subcommand)

```python
# daily_briefing/doctor.py
def run_doctor(config_path: str | None = None) -> bool:
    """Run diagnostics and return True if everything is OK."""
    ...
```

Doctor output:
```
Daily Briefing — Config Health Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Config: /home/user/brief.yaml ✅
Output:
  Language: en
  Timezone: Europe/Berlin
  Variant: morning

Sources (7 installed, 3 enabled):
  weather   ✅ (2 locations)
  calendar  ⚠️  disabled
  github    ⚠️  disabled
  bahn      ⚠️  disabled
  reddit    ⚠️  disabled
  news      ⚠️  disabled
  email     ⚠️  disabled

Summarizer: prompt-only ✅ (no API key required)
Delivery:
  stdout    ✅
  ntfy      ⚠️  NTFY_TOPIC not set

── Dry Run ──
Skipping — use --dry-run to test sources
```

Also implement `--dry-run` which actually fetches each configured source.

- [ ] Step 1: Write test

- [ ] Step 2: Implement doctor

- [ ] Step 3: Test with various configs

- [ ] Step 4: Commit

---

### Task 4: Add all CLI flags

- `--list-sources` (from P5)
- `--source NAME` / `-s` (single source debug — already exists)
- `--json` (already exists)
- `--verbose` / `-v` (already exists)
- `--variant morning|evening|weekly` (for P8)
- `--lang de|en` (override output.lang)
- `--dry-run` (fetch + report only, no summarize/ deliver)

- [ ] Step 1: Implement new flags in click group

- [ ] Step 2: Test each flag

- [ ] Step 3: Commit
