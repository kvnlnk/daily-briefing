# Daily Briefing 🌅

> **Your morning, summarized. 7 data sources, 1 message.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![PyPI](https://img.shields.io/badge/pypi-ready-brightgreen)](https://pypi.org)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen)](https://github.com/kvnlnk/daily-briefing)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

---

## Quick Start

```bash
pip install git+https://github.com/kvnlnk/daily-briefing.git
daily-briefing setup          # Interactive wizard — creates brief.yaml + .env
daily-briefing doctor         # Verify configuration and credentials
daily-briefing                # Run your first briefing!
```

No API keys are required to get started — weather, Reddit, and news work out of the box. Add credentials for GitHub, Calendar, Transit, and Email as you need them.

---

## Why Daily Briefing

Checking weather, calendar, GitHub notifications, train departures, news headlines, Reddit, and email every morning takes time. **Daily Briefing consolidates them all into one concise message.**

- **One unified message** instead of checking 7 apps
- **Self-hosted & open-source** — your data stays on your machine
- **7 built-in sources:** Weather ☀️, Calendar 📅, GitHub 🐙, Transit 🚆, News 📰, Reddit 💬, Email ✉️
- **Pluggable architecture** — add your own source as a pip-installable package
- **Multi-variant** — morning, evening, and weekly briefings
- **i18n** — English and German built-in, extensible to any language
- **Extensible summarization** — prompt-only (free), Ollama, OpenAI, or Anthropic
- **Flexible delivery** — stdout, ntfy.sh, or write your own sender

---

## Architecture

```
                        ┌──────────────┐
                        │  brief.yaml   │
                        │  configuration│
                        └──────┬───────┘
                               │
                    ┌──────────▼──────────┐
                    │    Orchestrator     │
                    │  (parallel fetch)   │
                    └──────┬──────────────┘
                           │
              ┌────────────┼────────────┬──────────────┬──────────────┐
              ▼            ▼            ▼              ▼              ▼
         Weather    Calendar     GitHub        Bahn         Reddit/News/Email
       (Open-Meteo) (Google API) (gh CLI)  (DB Fahrplan)   (RSS/IMAP)
              │            │            │              │              │
              └────────────┴────────────┴──────────────┴──────────────┘
                                       │
                              ┌────────▼────────┐
                              │   Summarizer    │
                              │  (prompt-only / │
                              │   ollama /      │
                              │   openai /      │
                              │   anthropic)    │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │    Delivery     │
                              │  (stdout / ntfy)│
                              └─────────────────┘
```

All sources run concurrently via `ThreadPoolExecutor`. Failed sources produce an error result — they never block the rest. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

---

## Usage

```bash
# Full briefing (default: morning, English)
daily-briefing

# Evening edition
daily-briefing --variant evening

# German output
daily-briefing --lang de

# Fetch only — no LLM summarization or delivery
daily-briefing --dry-run

# Debug a single source
daily-briefing --source weather

# Raw JSON output (for scripting)
daily-briefing --json

# List all installed sources
daily-briefing --list-sources

# Health check
daily-briefing doctor

# Interactive setup
daily-briefing setup
```

### Options

| Option | Description |
|--------|-------------|
| `--variant` | Briefing variant: `morning`, `evening`, `weekly` |
| `--lang` | Output language: `en`, `de` |
| `--source` | Fetch a single source by name |
| `--json` | Output raw JSON |
| `--dry-run` | Fetch sources but skip summarization + delivery |
| `--list-sources` | List all installed source plugins |
| `--verbose` | Print debug info and the LLM prompt |
| `--config` | Path to custom `brief.yaml` |
| `--log-level` | Logging verbosity |

---

## Configuration

Configuration lives in two files:

### `brief.yaml` — source settings and preferences

```yaml
sources:
  weather:
    enabled: true
    priority: 10
    locations:
      - name: London
        lat: 51.5074
        lon: -0.1278

output:
  lang: en                 # en | de
  variant: morning         # morning | evening | weekly
  tone: friendly           # friendly | concise | technical
  emoji: true
  max_length: 800

summarizer:
  provider: prompt-only    # prompt-only | ollama | openai | anthropic

delivery:
  - method: stdout
  # - method: ntfy
  #   topic: my-briefing
```

### `.env` — secrets and credentials (never committed)

```bash
# GitHub
GITHUB_TOKEN=ghp_xxx

# Calendar (Google Calendar OAuth)
# See docs for OAuth setup

# Bahn transit
BAHN_DEPARTURE_STATION=8000105  # Frankfurt Hbf
BAHN_TIME=07:30

# Reddit subreddits (comma-separated)
REDDIT_SUBREDDITS=programming,de

# Email (IMAP)
EMAIL_USER=you@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_IMAP_SERVER=imap.gmail.com

# ntfy delivery
NTFY_TOPIC=my-briefing
NTFY_URL=https://ntfy.sh
```

---

## Data Sources

| Source | What it provides | Auth needed | API |
|--------|-----------------|-------------|-----|
| **Weather** ☀️ | Current conditions + today's forecast | None | [Open-Meteo](https://open-meteo.com) (free) |
| **Calendar** 📅 | Today's Google Calendar events | OAuth | [Google Calendar API](https://developers.google.com/calendar) |
| **GitHub** 🐙 | Assigned issues, review-requested PRs | `gh` CLI auth | [GitHub REST API](https://docs.github.com/en/rest) |
| **Transit** 🚆 | Upcoming departures with delay info | None | [DB Fahrplan API](https://v6.db.transport.rest) |
| **Reddit** 💬 | Top posts from your subreddits | None | Public RSS |
| **News** 📰 | Headlines from RSS/Atom feeds | None | RSS feeds |
| **Email** ✉️ | Unread count + recent subjects | IMAP credentials | IMAP (stdlib) |

---

## Extending

### Add a custom source

Daily Briefing discovers third-party sources automatically via **Python entry points**. Create a pip-installable package that implements `SourceProtocol`:

```python
from daily_briefing.sources.base import SourceProtocol, SourceResult

class MySource(SourceProtocol):
    name = "my_source"

    def fetch(self, config: dict) -> SourceResult:
        # Your data-fetching logic here
        return SourceResult(name=self.name, priority=50, data={...})
```

Register it in your `pyproject.toml`:

```toml
[project.entry-points."daily_briefing.sources"]
my_source = "my_package.module:MySource"
```

Install it with `pip`, and it appears in `daily-briefing --list-sources` immediately.

**Full guide:** [docs/source-authoring.md](docs/source-authoring.md)

### Add a summarizer provider

Implement `SummarizerProtocol` and register it in `daily_briefing/summarizer/__init__.py`.

### Add a delivery method

Implement `DeliveryProtocol` and register it in `daily_briefing/delivery/__init__.py`.

### Add a locale

Create a `{lang}.yaml` file in `daily_briefing/summarizer/locales/`. It's auto-discovered.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| CLI framework | [click](https://click.palletsprojects.com/) |
| HTTP client | [requests](https://requests.readthedocs.io/) |
| Config | YAML via [PyYAML](https://pyyaml.org/) |
| Calendar | [google-api-python-client](https://github.com/googleapis/google-api-python-client) (optional) |
| RSS parsing | [feedparser](https://github.com/kurtmckee/feedparser/) |
| Concurrency | `concurrent.futures` (stdlib) |
| Storage | SQLite via `sqlite3` (stdlib) |
| LLM providers | Ollama / OpenAI / Anthropic (optional) |
| Delivery | stdout / [ntfy.sh](https://ntfy.sh) |

---

## License

MIT

---

<p align="center">Made by <a href="https://kevinlingk.com">kvnlnk</a></p>
