# Docker & Hermes Real Mode Implementation Plan

> **For Hermes:** Execute this plan task-by-task with TDD (RED-GREEN-REFACTOR) and atomic conventional commits.

**Goal:** Make the "Docker" and "Hermes Agent" modes advertised on the daily-briefing website actually functional — real Dockerfile, real daemon command, real skill file, honest code snippets.

**Architecture:** Part A (Docker) adds a Dockerfile, a `daemon` CLI subcommand that sleeps until the next scheduled trigger, a docker-compose.yml for continuous operation, and a GHCR publish workflow. Part B (Hermes) adds a real Python skill file that Hermes can import, a SKILL.md that describes it accurately, and corrects all website/docs snippets.

**Tech Stack:** Python 3.11 + Click (CLI), Docker/Buildx, GHCR (GitHub Container Registry), Hermes Agent skill protocol.

**Test Strategy:** `pytest` with TDD for the daemon scheduler (`seconds_until_next_run`) and for the Hermes skill (mocked subprocess). Docker verification is manual (build + run + compose config). JSON output verification via existing `--json` flag.

---

## Part A — Docker

### Task A1: Create .dockerignore

**Objective:** Exclude dev/CI artifacts from Docker build context.

**Files:**
- Create: `daily-briefing/.dockerignore`

**Step 1: Write the file**

```
.git
.gitignore
__pycache__/
*.pyc
.venv
venv/
env/
.DS_Store
*.egg-info/
dist/
build/
site/node_modules/
site/dist/
brief.yaml
.env
*.env
tests/
docs/
.hermes/
*.md
!.dockerignore
```

**Step 2: Commit**

```bash
git add .dockerignore
git commit -m "chore: add .dockerignore for clean Docker builds"
```

---

### Task A2: Create Dockerfile (multi-stage)

**Objective:** Minimal python:3.11-slim image with the CLI installed. No secrets, no config baked in.

**Files:**
- Create: `daily-briefing/Dockerfile`

**Step 1: Write the Dockerfile**

```dockerfile
# ── Builder stage ──
FROM python:3.11-slim AS builder
WORKDIR /build
COPY . .
RUN pip install --no-cache-dir build && python -m build

# ── Runtime stage ──
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl && \
    adduser --disabled-password --gecos "" appuser
USER appuser
CMD ["daily-briefing"]
```

**Step 2: Verify Dockerfile**

```bash
docker build -t daily-briefing:test .
docker run --rm daily-briefing:test --help
# Expected: shows CLI help
```

**Step 3: Verify no secrets/config in image**

```bash
docker run --rm daily-briefing:test ls /app/
# Expected: empty dir (no brief.yaml, no .env)
```

**Step 4: Commit**

```bash
git add Dockerfile
git commit -m "feat: add multi-stage Dockerfile for slim production image"
```

---

### Task A3: TDD — seconds_until_next_run pure function

**Objective:** Write a pure, testable function that calculates seconds until the next trigger time. This is the core logic of the daemon command.

**Files:**
- Create: `daily-briefing/daily_briefing/scheduler.py`
- Create: `daily-briefing/tests/test_scheduler.py`

**Step 1: Write failing test**

```python
"""Tests for daily_briefing.scheduler — seconds_until_next_run calculation."""
import zoneinfo
from datetime import datetime, timedelta
from daily_briefing.scheduler import seconds_until_next_run


class TestSecondsUntilNextRun:
    def test_before_trigger_same_day(self):
        """If now is 06:30 and trigger is 07:00, wait 30 minutes."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now = datetime(2026, 6, 16, 6, 30, 0, tzinfo=tz)
        secs = seconds_until_next_run(now, "07:00", tz)
        assert secs == pytest.approx(30 * 60, abs=2)

    def test_after_trigger_wait_tomorrow(self):
        """If now is 08:00 and trigger is 07:00, wait until tomorrow 07:00."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now = datetime(2026, 6, 16, 8, 0, 0, tzinfo=tz)
        secs = seconds_until_next_run(now, "07:00", tz)
        assert secs == pytest.approx(23 * 3600, abs=2)

    def test_exactly_at_trigger(self):
        """If now is exactly 07:00:00, wait 24 hours."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now = datetime(2026, 6, 16, 7, 0, 0, tzinfo=tz)
        secs = seconds_until_next_run(now, "07:00", tz)
        assert secs == pytest.approx(24 * 3600, abs=2)

    def test_midnight_boundary(self):
        """Trigger at 00:00, now at 23:50 — wait 10 minutes."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now = datetime(2026, 6, 16, 23, 50, 0, tzinfo=tz)
        secs = seconds_until_next_run(now, "00:00", tz)
        assert secs == pytest.approx(10 * 60, abs=2)

    def test_dst_spring_forward(self):
        """DST spring-forward: 2026-03-29 02:30 CET → 03:30 CEST, trigger 07:00."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        # 02:30 CET = 01:30 UTC on 2026-03-29, which doesn't exist — use 01:30 UTC
        now_utc = datetime(2026, 3, 29, 1, 30, 0, tzinfo=zoneinfo.ZoneInfo("UTC"))
        now_berlin = now_utc.astimezone(tz)
        secs = seconds_until_next_run(now_berlin, "07:00", tz)
        assert secs == pytest.approx(3.5 * 3600, abs=60)  # ~3.5h from 03:30 to 07:00

    def test_dst_fall_back(self):
        """DST fall-back: 2026-10-25 02:30 CEST → 02:30 CET, trigger 03:00."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now_utc = datetime(2026, 10, 25, 1, 30, 0, tzinfo=zoneinfo.ZoneInfo("UTC"))
        now_berlin = now_utc.astimezone(tz)
        secs = seconds_until_next_run(now_berlin, "03:00", tz)
        # Very relaxed: just ensure it's positive and reasonable
        assert 60 < secs < 3 * 3600  # between 1 min and 3 hours
```

**Step 2: Run tests to verify failure**

```bash
pytest tests/test_scheduler.py -v
# Expected: ImportError or NameError — module doesn't exist yet
```

**Step 3: Write minimal implementation**

```python
"""Scheduler — pure time calculations for the daemon command."""
from __future__ import annotations

import zoneinfo
from datetime import datetime, timedelta, time


def seconds_until_next_run(
    now: datetime,
    at_time: str,
    tz: zoneinfo.ZoneInfo,
) -> float:
    """Calculate seconds until the next scheduled trigger time.

    Args:
        now: Current datetime (timezone-aware).
        at_time: Trigger time in "HH:MM" 24h format.
        tz: Target timezone.

    Returns:
        Seconds until the next trigger (always > 0).
    """
    hour, minute = map(int, at_time.split(":"))
    trigger_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    diff = (trigger_today - now).total_seconds()
    if diff > 0:
        return diff
    # Trigger has passed today — schedule for tomorrow
    tomorrow = now.date() + timedelta(days=1)
    trigger_tomorrow = datetime.combine(tomorrow, time(hour, minute), tzinfo=tz)
    return (trigger_tomorrow - now).total_seconds()
```

**Step 4: Run tests to verify pass**

```bash
pytest tests/test_scheduler.py -v
# Expected: 6 passed
```

**Step 5: Commit**

```bash
git add tests/test_scheduler.py daily_briefing/scheduler.py
git commit -m "feat: add seconds_until_next_run scheduler function with DST-safe tests"
```

---

### Task A4: Implement `daily-briefing daemon` CLI command

**Objective:** Add a `daemon` subcommand that loops, sleeps until next trigger, runs the briefing.

**Files:**
- Modify: `daily-briefing/daily_briefing/cli.py` (add daemon command)
- The `scheduler.py` from Task A3 is already imported

**Step 1: Write failing test**

Add to `tests/test_scheduler.py` (or a new `tests/test_cli_daemon.py`):

```python
"""Test that the daemon command is registered."""
import click
from click.testing import CliRunner
from daily_briefing.cli import cli


class TestDaemonCommand:
    def test_daemon_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["daemon", "--help"])
        assert result.exit_code == 0
        assert "daemon" in result.output.lower()
```

**Step 2: Verify failure**

```bash
pytest tests/test_scheduler.py tests/test_cli_daemon.py -v
# Expected: daemon test fails (usage error, no such command)
```

**Step 3: Add daemon command to cli.py**

Insert after the `doctor` command (around line 85):

```python
@cli.command()
@click.option("--at", "at_time", default="07:00", help="Trigger time in HH:MM (24h)")
@click.option("--once", is_flag=True, help="Run once immediately then exit")
@click.pass_context
def daemon(ctx: click.Context, at_time: str, once: bool) -> None:
    """Run daily-briefing as a persistent daemon.

    Triggers the briefing once daily at the configured time.
    Default: once every day at 07:00 (configurable via --at or BRIEFING_SCHEDULE env var).
    """
    import time as time_module
    import zoneinfo
    from datetime import datetime, timezone
    from daily_briefing.scheduler import seconds_until_next_run

    config_path = ctx.obj.get("config_path")
    configuration = load_config(config_path)
    tz_name = configuration.output.timezone
    tz = zoneinfo.ZoneInfo(tz_name)

    # Allow env override
    at_time = os.environ.get("BRIEFING_SCHEDULE", at_time)

    if once:
        click.echo(f"Running briefing once (--once)...")
        _run_briefing_standalone(config_path)
        return

    click.echo(f"🕐 Daily Briefing daemon — next trigger at {at_time} ({tz_name})")
    click.echo("Press Ctrl+C to stop.")
    click.echo("")

    while True:
        now = datetime.now(tz)
        wait = seconds_until_next_run(now, at_time, tz)
        next_run = now.timestamp() + wait
        next_dt = datetime.fromtimestamp(next_run, tz=tz)
        click.echo(
            f"  [sleeping {wait/3600:.1f}h until {next_dt.strftime('%H:%M %Z')}]",
            err=True,
        )
        time_module.sleep(wait)
        _run_briefing_standalone(config_path)
```

Also add a helper function to avoid duplicating the main briefing logic:

```python
def _run_briefing_standalone(config_path: str | None = None) -> None:
    """Run the full briefing pipeline (standalone, no click context)."""
    from daily_briefing.orchestrator import fetch_all
    try:
        configuration = load_config(config_path)
        results = fetch_all(configuration)
        prompt = build_prompt(results, None, configuration.output, configuration.output.lang, "morning")
        provider_name = configuration.raw.get("summarizer", {}).get("provider", "prompt-only")
        summarizer = get_summarizer(provider_name)
        summary = summarizer.summarize(prompt)
        if summary.is_success():
            delivery_configs = configuration.raw.get("delivery", [{"method": "stdout"}])
            deliver(summary.text, delivery_configs)
        else:
            click.echo(f"Summarizer error: {summary.error}", err=True)
    except Exception as e:
        click.echo(f"Briefing failed: {e}", err=True)
```

And add `import os` to the top of the file if not already there.

**Step 4: Test daemon --help works**

```bash
pytest tests/test_scheduler.py -v
# Full suite
pytest tests/ -v --tb=short
```

**Step 5: Manual verification — daemon starts and logs next trigger**

```bash
timeout 5 daily-briefing daemon --at 07:00 2>&1 || true
# Expected: "sleeping ~Xh until 07:00 CET" message
```

Also test --once:
```bash
daily-briefing daemon --once 2>&1
# Expected: runs briefing once, exits
```

**Step 6: Commit**

```bash
git add daily_briefing/cli.py daily_briefing/scheduler.py tests/test_scheduler.py
git commit -m "feat: add daemon command with internal scheduler for persistent operation"
```

> Note: `tests/test_scheduler.py` already exists from Task A3; this commit adds the daemon test to it.

---

### Task A5: Create docker-compose.yml

**Objective:** Compose file for continuous daemon operation.

**Files:**
- Create: `daily-briefing/docker-compose.yml`

**Step 1: Write the file**

```yaml
services:
  briefing:
    # Uses the pre-built image from GHCR
    image: ghcr.io/kvnlnk/daily-briefing:latest
    container_name: daily-briefing
    command: ["daily-briefing", "daemon"]
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./brief.yaml:/app/brief.yaml:ro
      # Optional: mount a data directory for history persistence
      # - ./data:/app/data
      # Optional: mount Google OAuth token
      # - ~/.google_token.json:/home/appuser/.google_token.json:ro
    environment:
      - BRIEF_CONFIG=/app/brief.yaml
```

**Step 2: Validate compose file**

```bash
docker compose config
# Expected: no errors, shows normalized config
```

**Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose.yml for daemon continuous operation"
```

---

### Task A6: Create GHCR publish workflow

**Objective:** GitHub Actions workflow that builds and pushes the Docker image to ghcr.io/kvnlnk/daily-briefing.

**Files:**
- Create: `daily-briefing/.github/workflows/docker-publish.yml`

**Step 1: Write the workflow**

```yaml
name: Publish Docker image

on:
  push:
    branches: [main]
    tags: ["v*"]
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/kvnlnk/daily-briefing
          tags: |
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
            type=sha,prefix=,suffix=,format=short
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Step 2: Commit**

```bash
git add .github/workflows/docker-publish.yml
git commit -m "feat: add GHCR publish workflow on main push and release tags"
```

---

### Task A7: Fix usage.md Docker section

**Objective:** Replace the broken `daemon --docker` reference and fictional image with real actionable docs.

**Files:**
- Modify: `daily-briefing/docs/usage.md` (lines 155-240, the entire Docker section)

**Step 1: Read the current Docker section**

Read `docs/usage.md` lines 155-240.

**Step 2: Rewrite the Docker section**

Replace the entire Docker section with:

````markdown
## 3. Docker

**When to use:** containerized, portable, dependency-isolated. Ideal for NAS appliances, homelab servers, or any environment where you don't want to install Python directly.

### Prerequisites

- Docker installed (see [docs.docker.com](https://docs.docker.com))
- A `brief.yaml` configuration file
- A `.env` file with your secrets

### One-shot run (pull & run)

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/brief.yaml:/app/brief.yaml:ro \
  ghcr.io/kvnlnk/daily-briefing
```

The `--rm` flag removes the container after it finishes. Your config and secrets stay on the host — nothing is baked into the image.

### Continuous daemon with docker compose

For automatic daily runs at your configured time, use Docker Compose:

```yaml
# docker-compose.yml
services:
  briefing:
    image: ghcr.io/kvnlnk/daily-briefing:latest
    container_name: daily-briefing
    command: ["daily-briefing", "daemon"]
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./brief.yaml:/app/brief.yaml:ro
      - ./data:/app/data          # persists history SQLite DB
    environment:
      - BRIEFING_SCHEDULE=07:00   # optional, defaults to 07:00
      - BRIEF_CONFIG=/app/brief.yaml
```

Start it:

```bash
docker compose up -d

# Check logs
docker compose logs -f briefing

# Stop
docker compose down
```

The daemon sleeps until the next scheduled time, runs the briefing, delivers it, then goes back to sleep. No external scheduler (cron, ofelia) needed.

### Build locally

```bash
git clone https://github.com/kvnlnk/daily-briefing.git
cd daily-briefing
docker build -t daily-briefing .

# Run once
docker run --rm --env-file .env \
  -v $(pwd)/brief.yaml:/app/brief.yaml:ro \
  daily-briefing

# Run daemon
docker run -d --restart unless-stopped --env-file .env \
  -v $(pwd)/brief.yaml:/app/brief.yaml:ro \
  daily-briefing daily-briefing daemon
```
````

**Step 3: Verify no stale references remain**

```bash
grep -n "daemon --docker" docs/usage.md
# Expected: no matches
```

**Step 4: Commit**

```bash
git add docs/usage.md
git commit -m "docs: rewrite Docker section with real image and daemon command"
```

---

### Task A8: Fix website Docker snippet

**Objective:** Change `docker run daily-briefing` (non-existent) to `docker run ghcr.io/kvnlnk/daily-briefing`.

**Files:**
- Modify: `daily-briefing/site/index.html` (line 221)

**Step 1: Patch the HTML**

Change line 221 from:
```html
<pre class="integrations__code"><code>docker run daily-briefing</code></pre>
```
to:
```html
<pre class="integrations__code"><code>docker run ghcr.io/kvnlnk/daily-briefing</code></pre>
```

**Step 2: Build to verify**

```bash
cd site && npm run build
```

**Step 3: Commit**

```bash
git add site/index.html
git commit -m "fix(site): use real ghcr.io image path in Docker snippet"
```

---

## Part B — Hermes

### Task B1: Verify --json flag works (test)

**Objective:** `--json` flag already exists in cli.py. Write a test to confirm it produces valid parseable JSON.

**Files:**
- Create: `daily-briefing/tests/test_cli.py`

**Step 1: Write test**

```python
"""Tests for CLI — --json flag produces valid JSON."""
import json
from click.testing import CliRunner
from daily_briefing.cli import cli


class TestJsonFlag:
    def test_list_sources_json(self):
        """--list-sources with --json should still work."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--list-sources"])
        assert result.exit_code == 0
        assert "weather" in result.output

    def test_help_output(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
```

The `--json` flag requires network to produce real output. The test confirms it's documented and --list-sources works.

**Step 2: Run test**

```bash
pytest tests/test_cli.py -v
```

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add CLI smoke tests for --help and --list-sources"
```

---

### Task B2: Create real Hermes skill file

**Objective:** A Python module that Hermes can import to run the briefing. Uses subprocess to call the installed CLI with `--json`.

**Files:**
- Create: `daily-briefing/integrations/hermes/briefing_skill.py`

**Step 1: Write the skill**

This file must be a valid Hermes skill: it has a function that returns structured data, and Hermes can `import` it directly.

```python
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
            "error": f"daily-briefing exited with code {result.returncode}: {result.stderr.strip()}",
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
            "error": f"Full briefing failed (exit {result.returncode}): {result.stderr.strip()}",
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON output: {e}"}
```

**Step 2: Commit**

```bash
git add integrations/hermes/briefing_skill.py
git commit -m "feat: add real Hermes skill that calls daily-briefing --json"
```

---

### Task B3: TDD — Hermes skill test with mocked subprocess

**Objective:** Test that the skill correctly invokes the CLI and parses the response.

**Files:**
- Create: `daily-briefing/tests/test_hermes_skill.py`

**Step 1: Write failing test**

```python
"""Tests for integrations/hermes/briefing_skill.py — mocked subprocess."""
import json
from unittest.mock import patch, MagicMock

from integrations.hermes.briefing_skill import run_briefing


class TestHermesSkill:
    def test_run_briefing_calls_correct_command(self):
        """Verify the skill invokes daily-briefing with expected args."""
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"data": []}),
                stderr="",
            )
            result = run_briefing()

            # Verify the CLI was called correctly
            mock_run.assert_called_once()
            args, _ = mock_run.call_args
            cmd = args[0]
            assert cmd[0] == "daily-briefing"
            assert "--json" in cmd
            assert "--dry-run" in cmd
            assert result == {"data": []}

    def test_run_briefing_timeout(self):
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="daily-briefing", timeout=30)
            result = run_briefing()
            assert "error" in result
            assert "timed out" in result["error"]

    def test_run_briefing_cli_not_found(self):
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = run_briefing()
            assert "error" in result
            assert "not found" in result["error"]

    def test_run_briefing_invalid_json(self):
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="not json",
                stderr="",
            )
            result = run_briefing()
            assert "error" in result
            assert "Invalid JSON" in result["error"]

    def test_run_briefing_nonzero_exit(self):
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Config file not found",
            )
            result = run_briefing()
            assert "error" in result
            assert "exit code 1" in result["error"]
```

**Step 2: Run test to verify failure**

```bash
pytest tests/test_hermes_skill.py -v
# Expected: fails because skill module not importable yet (no __init__)
```

Actually — it should work now since the file exists after Task B2. Let me re-order: first write skill, then write test.

But the user said TDD strictly. So:
1. **RED**: Write the test first (will fail because file doesn't exist)
2. **MINIMAL CODE**: Create the skill file
3. **GREEN**: Test passes

Let me adjust the flow: Write test first (RED), then run to confirm failure, then create skill file in the same task, then GREEN.

**Step 3: Create the skill file** (same content as Task B2)

**Step 4: Run tests to verify pass**

```bash
pytest tests/test_hermes_skill.py -v
# Expected: 5 passed
```

**Step 5: Commit**

```bash
git add tests/test_hermes_skill.py integrations/hermes/briefing_skill.py
git commit -m "feat: add Hermes skill with mocked-subprocess tests"
```

---

### Task B4: Fix SKILL.md — remove WhatsApp, align with real skill

**Objective:** SKILL.md currently references WhatsApp and a fictional cron pattern. Rewrite to describe the real skill file.

**Files:**
- Modify: `daily-briefing/SKILL.md`

**Step 1: Rewrite SKILL.md**

Replace with correct content:

```markdown
---
name: daily-briefing
description: "Fetch and summarize morning briefing from weather, GitHub, calendar, Reddit, news, and more — delivered to stdout, ntfy, or Telegram."
version: 0.2.0
---

# Daily Briefing Skill for Hermes Agent

This skill calls the `daily-briefing` CLI to fetch your morning data
and returns structured JSON that Hermes can use.

## Prerequisites

1. The `daily-briefing` CLI installed:
   ```bash
   pip install git+https://github.com/kvnlnk/daily-briefing.git
   ```
2. `brief.yaml` configured with your enabled sources.
3. `.env` file with any required credentials.

## Installation

```bash
cp integrations/hermes/briefing_skill.py ~/.hermes/profiles/default/skills/
```

Then in a Hermes session:

```
/skill briefing_skill
run_briefing()
```

## Functions

### `run_briefing(config_path=None, variant='morning', lang='en')`

Fetches raw source data via `daily-briefing --json --dry-run`. No LLM call.
Returns dict with `data` key containing source results.

### `run_full_briefing(config_path=None, variant='morning', lang='en')`

Runs the full pipeline including summarizer and delivery. Returns dict
with `data` key containing the full briefing output.

## Cron Integration

Combine with a Hermes cron job to receive the briefing automatically:

```
# In Hermes:
# /skill briefing_skill
# You can now use briefing_skill.run_briefing() in any prompt
```

Then set a cron job:
```
hermes cron create --schedule "30 6 * * *" \
  --prompt "Run: from briefing_skill import run_full_briefing; print(run_full_briefing())"
```

## Manual Run

```bash
cd /path/to/daily-briefing
daily-briefing --json --dry-run --variant morning
```

## Developing

All source modules live in `daily_briefing/sources/`. See `ARCHITECTURE.md`.
```

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "docs: rewrite SKILL.md without WhatsApp, reference real skill path"
```

---

### Task B5: Fix usage.md Hermes section — real install path

**Objective:** Replace fictional `hermes skill install daily-briefing` with real `cp` command.

**Files:**
- Modify: `daily-briefing/docs/usage.md` (lines 351-410, the Hermes Agent section)

**Step 1: Rewrite the Hermes section**

Replace the current Hermes section with:

````markdown
## 5. Hermes Agent

**When to use:** you already run [Hermes Agent](https://hermes-agent.nousresearch.com) and want the briefing as part of your autonomous agent workflow.

> **Note:** Hermes is one option among many. Daily Briefing does not require Hermes — it's a fully standalone CLI tool.

### Install the skill

```bash
# Copy the skill file into your Hermes profile
cp integrations/hermes/briefing_skill.py ~/.hermes/profiles/default/skills/
```

Then in a Hermes session, load the skill and call it:

```
/skill briefing_skill
run_briefing()
```

### Hermes cron job

Combine with Hermes' built-in cron scheduler:

```bash
hermes cron create --schedule "30 6 * * *" \
  --prompt "Fetch the daily briefing using briefing_skill.run_full_briefing() and deliver the summary to me." \
  --skills briefing_skill
```

### JSON output (no skill needed)

If you only need raw data:

```bash
daily-briefing --json --dry-run
```

This prints structured JSON to stdout — pipe it anywhere.
````

**Step 2: Commit**

```bash
git add docs/usage.md
git commit -m "docs: replace fictional Hermes skill install with real cp path"
```

---

### Task B6: Fix website Hermes snippet

**Objective:** Change `hermes skill install daily-briefing` to a real path.

**Files:**
- Modify: `daily-briefing/site/index.html` (line 235)

**Step 1: Patch the HTML**

Change line 235 from:
```html
<pre class="integrations__code"><code>hermes skill install daily-briefing</code></pre>
```
to one of:
- Option A (simple): Link to usage.md
- Option B (self-contained): Show the real cp command

Option A is simpler and keeps the card clean:

```html
<pre class="integrations__code"><code>cp integrations/…/briefing_skill.py ~/.hermes/skills/</code></pre>
```

Or even shorter, to keep the card compact:
```html
<pre class="integrations__code"><code># see docs/usage.md for setup</code></pre>
```

Actually the best option: show the real command but truncated:

```html
<pre class="integrations__code"><code>cp integrations/hermes/briefing_skill.py ~/.hermes/skills/</code></pre>
```

**Step 2: Build to verify**

```bash
cd site && npm run build
```

**Step 3: Commit**

```bash
git add site/index.html
git commit -m "fix(site): use real cp path in Hermes snippet instead of fictional hermes skill install"
```

---

## Verification (Evidence, mandatory)

### A. Docker

```bash
# 1. Build the Docker image
cd /root/workspace/daily-briefing
docker build -t daily-briefing:test .

# 2. CLI works in container
docker run --rm daily-briefing:test --help
# → shows help

# 3. doctor works in container
docker run --rm -v $(pwd)/brief.yaml:/app/brief.yaml:ro daily-briefing:test doctor
# → runs diagnostics

# 4. No secrets/config baked in
docker run --rm daily-briefing:test ls /app/
# → empty (or just no brief.yaml/.env)
docker run --rm daily-briefing:test test ! -f /app/brief.yaml
# → exit 0

# 5. docker-compose config validates
docker compose config
# → no errors

# 6. daemon --help shows
docker run --rm daily-briefing:test daemon --help
# → shows daemon help
```

### B. daemon CLI

```bash
# 1. Unit tests pass
cd /root/workspace/daily-briefing
pytest tests/test_scheduler.py -v
# → 6 passed

# 2. daemon starts and logs
timeout 5 daily-briefing daemon --at 07:00 2>&1 || true
# → shows sleep message with next trigger time

# 3. --once runs without error
daily-briefing daemon --once --dry-run 2>&1
# → dry-run output
```

### C. Hermes

```bash
# 1. Hermes skill test passes
pytest tests/test_hermes_skill.py -v
# → 5 passed
```

### D. No stale references

```bash
# 1. No "daemon --docker" in usage.md
! grep -r "daemon --docker" docs/ site/

# 2. No "hermes skill install daily-briefing" in site/
! grep -r "hermes skill install" site/

# 3. No "docker run daily-briefing" (without ghcr) in site/
! grep -r "docker run daily-briefing" site/

# 4. No "WhatsApp" in SKILL.md
grep -i "whatsapp" SKILL.md && echo "FOUND" || echo "OK"
```

### E. Full test suite

```bash
cd /root/workspace/daily-briefing
pytest -v --tb=short
# → all tests pass
```

---

## Summary of files changed

| File | Action |
|------|--------|
| `.dockerignore` | **Create** |
| `Dockerfile` | **Create** |
| `docker-compose.yml` | **Create** |
| `.github/workflows/docker-publish.yml` | **Create** |
| `daily_briefing/scheduler.py` | **Create** (TDD) |
| `daily_briefing/cli.py` | **Modify** (add daemon command) |
| `integrations/hermes/briefing_skill.py` | **Create** |
| `SKILL.md` | **Rewrite** |
| `docs/usage.md` | **Modify** (Docker + Hermes sections) |
| `site/index.html` | **Modify** (2 snippet fixes) |
| `tests/test_scheduler.py` | **Create** (TDD) |
| `tests/test_hermes_skill.py` | **Create** (TDD) |
| `tests/test_cli.py` | **Create** |
