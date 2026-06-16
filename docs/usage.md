# Usage & Integrations

> **How to run Daily Briefing in production — cron, systemd, Docker, GitHub Actions, and more.**

---

## A Real Morning at 7 AM

Your alarm goes off at 06:45. Coffee is brewing. By 07:00 the briefing is already waiting.

Behind the scenes, Daily Briefing fires seven source plugins in parallel: Open-Meteo returns today's forecast (14 °C, light drizzle), Google Calendar pulls two meetings and a lunch reservation, the GitHub source checks for open review requests on your repos, DB Fahrplan lists the next three ICE departures from Frankfurt Hbf, Reddit surfaces the top thread from r/programming, the RSS news feed collects headlines from three tech publications, and your IMAP inbox reports 4 unread emails — two of which are newsletters you'll skim later.

All seven results land in the orchestrator within about three seconds (the slowest is usually the weather API). The summarizer — configured for `prompt-only` mode so there's zero cost — assembles them into a single, readable message. Delivery is stdout **and** ntfy, so the message appears both in your terminal log and as a push notification on your phone.

You scroll it while waiting for the elevator. No app-switching. No missed context. Just one message, seven sources, done.

---

## 1. Standalone: cron

**When to use:** simplest option, works everywhere cron does. Every Unix system has it.

### Prerequisites

- Daily Briefing installed: `pip install git+https://github.com/kvnlnk/daily-briefing.git`
- `brief.yaml` and `.env` exist (run `daily-briefing setup` once)
- `daily-briefing` is on your PATH (confirm with `which daily-briefing`)

### Crontab entry

```crontab
# ── Morning briefing at 7:00 ──
0 7 * * * cd /home/user/daily-briefing && daily-briefing --variant morning

# ── Evening briefing at 18:00 ──
0 18 * * * cd /home/user/daily-briefing && daily-briefing --variant evening

# ── Weekly summary every Monday at 8:00 ──
0 8 * * 1 cd /home/user/daily-briefing && daily-briefing --variant weekly --lang en
```

### Install the crontab

```bash
crontab -e
# paste the lines above, save, exit

# Verify
crontab -l
```

### Tips

- Use absolute paths to `daily-briefing` if PATH isn't set in cron's environment:
  ```crontab
  0 7 * * * /home/user/.local/bin/daily-briefing --variant morning
  ```
- Pipe to a log file if you want a record:
  ```crontab
  0 7 * * * /home/user/.local/bin/daily-briefing --variant morning >> /home/user/logs/briefing.log 2>&1
  ```
- If your `.env` isn't automatically sourced, either run `daily-briefing setup` from the working directory or export variables explicitly in crontab:
  ```crontab
  0 7 * * * export $(cat /home/user/.config/daily-briefing/.env | xargs) && /home/user/.local/bin/daily-briefing
  ```

---

## 2. systemd user timer

**When to use:** more reliable than cron — survives sleep/wake cycles, has dependency ordering, and runs without root. Best for laptops and workstations that suspend overnight.

### Prerequisites

- Daily Briefing installed with `pip install ...`
- `brief.yaml` and `.env` configured
- systemd user instance available (all modern Linux distributions)

### Service unit

Create **`~/.config/systemd/user/daily-briefing.service`**:

```ini
[Unit]
Description=Daily Briefing — morning fetch & summarize
Documentation=https://github.com/kvnlnk/daily-briefing

[Service]
Type=oneshot
ExecStart=%h/.local/bin/daily-briefing --variant morning
WorkingDirectory=%h/.config/daily-briefing
EnvironmentFile=%h/.config/daily-briefing/.env

# Restart only on failure, with back-off
Restart=on-failure
RestartSec=30

# Hardening
NoNewPrivileges=true
ProtectHome=read-only
PrivateTmp=true
```

### Timer unit

Create **`~/.config/systemd/user/daily-briefing.timer`**:

```ini
[Unit]
Description=Daily Briefing timer — 07:00 every day
Documentation=https://github.com/kvnlnk/daily-briefing

[Timer]
# Fire at 07:00 every day
OnCalendar=*-*-* 07:00:00

# If the machine was off, fire immediately on next boot
Persistent=true

# Randomize by up to 5 minutes to avoid thundering-herd on API endpoints
RandomizedDelaySec=5min

[Install]
WantedBy=timers.target
```

### Enable and start

```bash
# Reload systemd user manager
systemctl --user daemon-reload

# Verify the units parse correctly
systemctl --user status daily-briefing.service

# Enable and start the timer
systemctl --user enable --now daily-briefing.timer

# Confirm it's active
systemctl --user list-timers --all | grep daily-briefing
```

### Checking logs

```bash
# See the last run
journalctl --user -u daily-briefing.service --since today

# Follow future runs in real-time
journalctl --user -u daily-briefing.service -f
```

---

## 3. Docker

**When to use:** containerized, portable, dependency-isolated. Ideal for NAS appliances, homelab servers, or any environment where you don't want to install Python directly.

### Prerequisites

- Docker installed (see [docs.docker.com](https://docs.docker.com))
- A `brief.yaml` configuration file
- A `.env` file with your secrets

### Dockerfile

Create a `Dockerfile` in your project directory:

```dockerfile
FROM python:3.11-slim

RUN pip install --no-cache-dir git+https://github.com/kvnlnk/daily-briefing.git

WORKDIR /app
COPY brief.yaml .env ./

CMD ["daily-briefing", "--variant", "morning"]
```

Build and run:

```bash
docker build -t daily-briefing .
docker run --rm daily-briefing
```

### docker-compose.yml (recommended)

For cron scheduling inside Docker, use `docker-compose.yml` with environment variables and a cron container:

```yaml
version: "3.8"

services:
  briefing:
    build: .
    image: daily-briefing
    container_name: daily-briefing
    env_file: .env
    volumes:
      - ./brief.yaml:/app/brief.yaml:ro
      - ./data:/app/data        # persists history SQLite DB
    command: ["daily-briefing", "--variant", "morning"]
    restart: "no"

  # Optional: run on a schedule using ofelia (https://github.com/mcuadros/ofelia)
  scheduler:
    image: mcuadros/ofelia:latest
    depends_on:
      - briefing
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: daemon --docker
    restart: unless-stopped
    labels:
      ofelia.job-run.briefing.schedule: "0 7 * * *"
      ofelia.job-run.briefing.container: "daily-briefing"
```

### Run once manually

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/brief.yaml:/app/brief.yaml:ro \
  daily-briefing \
  daily-briefing --variant morning
```

### Using a pre-built image

If you push to a registry, the run command becomes:

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/brief.yaml:/brief.yaml:ro \
  -e BRIEF_CONFIG=/brief.yaml \
  ghcr.io/youruser/daily-briefing:latest
```

---

## 4. GitHub Actions

**When to use:** you live in GitHub. Your repos, issues, and PRs are already there — running the briefing as a CI workflow keeps everything in one place. Also free for public repositories.

### Prerequisites

- Repository with Daily Briefing installed as a GitHub Action
- Secrets configured in **Settings → Secrets and variables → Actions**

### Workflow file

Create **`.github/workflows/daily-briefing.yml`**:

```yaml
name: Daily Briefing

on:
  schedule:
    # Every morning at 07:00 UTC — adjust for your timezone
    - cron: '0 7 * * *'
  workflow_dispatch:   # allows manual trigger from GitHub UI

jobs:
  briefing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Daily Briefing
        run: pip install git+https://github.com/kvnlnk/daily-briefing.git

      - name: Create config
        run: |
          mkdir -p ~/.config/daily-briefing
          cat > ~/.config/daily-briefing/brief.yaml << 'EOF'
          sources:
            weather:
              enabled: true
              priority: 10
              locations:
                - name: Home
                  lat: 51.5074
                  lon: -0.1278
            news:
              enabled: true
              priority: 80
            reddit:
              enabled: true
              priority: 70

          output:
            lang: en
            variant: morning
            tone: friendly
            emoji: true
            max_length: 800

          summarizer:
            provider: prompt-only

          delivery:
            - method: stdout
          EOF

      - name: Run briefing
        run: daily-briefing --variant morning
        env:
          # Secrets set in GitHub repo Settings → Secrets and variables → Actions
          NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}
          NTFY_URL: ${{ secrets.NTFY_URL || 'https://ntfy.sh' }}
          REDDIT_SUBREDDITS: ${{ secrets.REDDIT_SUBREDDITS || 'programming' }}
```

### Setting up secrets

1. Go to your repo on GitHub: **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Add each secret (e.g. `NTFY_TOPIC`, `NTFY_URL`)
4. Reference them in the workflow as `${{ secrets.NTFY_TOPIC }}`

### Sending the result to you

If you configure `delivery` with ntfy in `brief.yaml`, the GitHub Action runner will push the briefing to your phone. For pure stdout, the output is captured in the Actions log — you'd need a separate notification step (e.g., `actions/github-script` to send a repository notification).

### Weekly or evening variants

Change the `cron` expression and add `--variant`:

```yaml
on:
  schedule:
    - cron: '0 18 * * 5'   # Friday 18:00 — weekend preview
```

And in the run step:

```yaml
- run: daily-briefing --variant evening
```

---

## 5. Hermes Agent

**When to use:** you already run [Hermes Agent](https://hermes-agent.nousresearch.com) and want the briefing as part of your autonomous agent workflow. Daily Briefing output can be piped into a Hermes cron job or skill.

> **Note:** Hermes is one option among many. Daily Briefing does not require Hermes — it's a fully standalone CLI tool.

### Option A: Hermes cron job

Create a cron entry that runs `daily-briefing` and stores the output for Hermes to pick up:

```bash
# In your Hermes profile's cron/ directory
# Save as: ~/.hermes/profiles/default/cron/briefing.sh

#!/bin/bash
# /root/.hermes/profiles/default/cron/briefing.sh
daily-briefing --variant morning --json > /tmp/daily-briefing-latest.json
```

Make it executable and add a cron schedule:

```bash
chmod +x ~/.hermes/profiles/default/cron/briefing.sh
crontab -e
# 0 7 * * * /root/.hermes/profiles/default/cron/briefing.sh
```

### Option B: Trigger from a Hermes skill

A Hermes skill can invoke `daily-briefing` and use the JSON output as context:

```python
# ~/.hermes/profiles/default/skills/briefing.py
import json
import subprocess


def run_briefing():
    """Fetch today's briefing and return structured data."""
    result = subprocess.run(
        ["daily-briefing", "--json", "--dry-run"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return {"error": result.stderr}
    return json.loads(result.stdout)
```

### Option C: Webhook delivery

If you've implemented a custom Hermes webhook sender for Daily Briefing's delivery protocol, configure it in `brief.yaml`:

```yaml
delivery:
  - method: hermes_webhook
    url: http://localhost:8080/webhook
```

(This requires a `hermes_webhook` entry in the delivery registry — see [docs/source-authoring.md](source-authoring.md) for the pattern.)

---

## Delivery Options Summary

| Method | Config in `brief.yaml` | What happens | Best for |
|--------|------------------------|--------------|----------|
| **stdout** | `method: stdout` | Prints to terminal | Local cron / systemd / Docker logs |
| **ntfy** | `method: ntfy` / `topic: my-briefing` | Push notification via [ntfy.sh](https://ntfy.sh) | Phone notifications, always-on servers |
| **stdout + ntfy** | List both under `delivery:` | Both at once | Development + production notifications |
| **JSON** | `--json` CLI flag | Raw JSON output | Scripting, Hermes skills, other toolchains |
| **Custom sender** | `method: your_custom` | Implement `DeliveryProtocol` | Slack webhooks, email, Matrix, etc. |

### Example: dual delivery

```yaml
delivery:
  - method: stdout
  - method: ntfy
    topic: my-daily-briefing
    url: https://ntfy.sh
```

This prints the briefing to stdout **and** pushes it as a notification. If ntfy is down, the stdout output still works — failures are independent per delivery channel.

---

## Quick Reference: Running Daily Briefing

```bash
# Full briefing (default: morning, English)
daily-briefing

# Evening edition
daily-briefing --variant evening

# Weekly recap
daily-briefing --variant weekly

# German output
daily-briefing --lang de

# Fetch only — no LLM, no delivery
daily-briefing --dry-run

# Debug a single source
daily-briefing --source weather

# Raw JSON output (for scripting / Hermes)
daily-briefing --json

# List all installed sources
daily-briefing --list-sources

# Health check
daily-briefing doctor

# Interactive setup
daily-briefing setup

# Use a custom config path
daily-briefing --config /path/to/brief.yaml
```

---

## Environment Variables Reference

| Variable | Used by | Required? |
|----------|---------|-----------|
| `BRIEF_CONFIG` | Config loader | If config not at default path |
| `GITHUB_TOKEN` | GitHub source | For GitHub data |
| `BAHN_DEPARTURE_STATION` | Bahn source | For transit data |
| `BAHN_TIME` | Bahn source | Default departure time |
| `REDDIT_SUBREDDITS` | Reddit source | Comma-separated subreddits |
| `EMAIL_USER` / `EMAIL_PASSWORD` | Email source | IMAP credentials |
| `EMAIL_IMAP_SERVER` | Email source | IMAP server hostname |
| `NTFY_TOPIC` / `NTFY_URL` | ntfy delivery | For push notifications |
| `OPENAI_API_KEY` | OpenAI summarizer | If using OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic summarizer | If using Anthropic |
| `OLLAMA_HOST` | Ollama summarizer | Default: `http://localhost:11434` |

---

## Troubleshooting

### "daily-briefing: command not found"

```bash
# Ensure pip's bin directory is on PATH
export PATH="$HOME/.local/bin:$PATH"
# Verify
which daily-briefing
```

### "No brief.yaml found"

```bash
# Run the setup wizard
daily-briefing setup

# Or point to your config explicitly
daily-briefing --config /home/user/my-briefing.yaml
```

### systemd timer didn't fire

```bash
# Check timer status
systemctl --user list-timers --all | grep daily-briefing

# Check service logs
journalctl --user -u daily-briefing.service --since "1 hour ago"

# Manual trigger to test
systemctl --user start daily-briefing.service
```

### ntfy notification not arriving

```bash
# Test with curl
curl -d "test" https://ntfy.sh/YOUR_TOPIC

# Verify NTFY_TOPIC is set in .env
grep NTFY_TOPIC ~/.config/daily-briefing/.env
```

---

See [ARCHITECTURE.md](../ARCHITECTURE.md) for the full design, [docs/source-authoring.md](source-authoring.md) for creating custom sources, and [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup.
