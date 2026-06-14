# 🌅 Daily Briefing

**AI-powered morning briefing — weather, GitHub, calendar, news, and Reddit in one WhatsApp message.**

---

## 🤖 Fully Vibecoded with Hermes Agent

This project was built entirely through natural language conversations with [Hermes Agent](https://hermes-agent.nousresearch.com) — an autonomous AI coding assistant. From research and architecture to parallel source fetching and LLM prompt assembly, every line of code was generated, tested, and shipped via chat prompts using the [agent-skills](https://github.com/addyosmani/agent-skills) methodology (plan → incremental build → atomic commits → ship).

---

## ✨ Features

- **🌤️ Weather** — Current conditions + today's forecast from Open-Meteo (free, no API key)
- **📅 Calendar** — Today's Google Calendar events with busy-hours count
- **🐙 GitHub** — Assigned issues, review-requested PRs, and recently pushed repos via `gh` CLI
- **🚆 Bahn** — Upcoming departures at your station with delay information via DB Fahrplan API
- **📰 News** — Headlines from RSS/Atom feeds (heise, dev.to by default)
- **🔴 Reddit** — Top posts from configured subreddits via public RSS (no auth)
- **📬 Email** — Unread count + recent subjects via IMAP (stdlib, zero deps)
- **⚡ Parallel fetching** — All sources fetched concurrently with `ThreadPoolExecutor`
- **🔌 Source registry** — Add a new source: one file + one config line
- **📊 Yesterday comparison** — SQLite-backed diff so the LLM says "3° wärmer als gestern"

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| CLI framework | `click` 8.3 |
| Terminal output | `rich` 14.3 |
| HTTP client | `requests` 2.33 |
| Config | YAML via `PyYAML` 6.0 |
| Calendar SDK | `google-api-python-client` |
| RSS parsing | `feedparser` 6.0 |
| GitHub access | `gh` CLI via `subprocess` |
| Storage | SQLite via `sqlite3` stdlib |
| Concurrency | `concurrent.futures` |

---

## 🚀 Install & Usage

### Quick Start

```bash
# Clone and install
git clone https://github.com/kvnlnk/daily-briefing
cd daily-briefing
pip install -e .

# Edit brief.yaml to configure which sources are enabled
# Copy .env.example to .env and fill in your credentials
cp .env.example .env

# Run the full briefing
python -m daily_briefing
```

### Test a Single Source

```bash
python -m daily_briefing --source weather
```

Output:
```json
{
  "location": "Frankfurt",
  "temperature": 17.8,
  "condition": "Partly cloudy",
  "high": 20.0,
  "low": 12.7,
  "rain_chance": 60
}
```

### See the Raw LLM Prompt

```bash
python -m daily_briefing --verbose
```

### JSON Output (for scripting)

```bash
python -m daily_briefing --json
```

---

## 📋 Configuration

All sources are enabled/disabled in `brief.yaml`:

```yaml
sources:
  weather:
    enabled: true
    priority: 10
  calendar:
    enabled: true
    priority: 20
  # ...
```

Credentials go in `.env` (never committed):

```bash
# GitHub
GITHUB_TOKEN=ghp_xxx

# Google Calendar (via google-workspace Hermes skill)
# OAuth token auto-loaded from ~/.hermes/google_token.json

# Bahn stations
BAHN_DEPARTURE_STATION=8000105   # Frankfurt Hbf
BAHN_TIME=07:30

# Reddit subreddits
REDDIT_SUBREDDITS=programming,de

# Email (optional, disabled by default)
EMAIL_USER=you@gmail.com
EMAIL_PASSWORD=app_password
```

---

## 📁 Project Structure

```
daily-briefing/
├── daily_briefing/
│   ├── sources/           # One module per data source
│   │   ├── base.py        # SourceProtocol ABC + SourceResult
│   │   ├── weather.py     # Open-Meteo API
│   │   ├── github.py      # gh CLI subprocess
│   │   ├── calendar.py    # Google Calendar SDK
│   │   ├── bahn.py        # DB Fahrplan API
│   │   ├── reddit.py      # Reddit RSS
│   │   ├── news.py        # RSS/Atom feeds
│   │   └── email.py       # IMAP via imaplib
│   ├── orchestrator.py    # Parallel fetch + source registry
│   ├── summarizer/
│   │   └── prompts.py     # LLM prompt builder + data simplifier
│   ├── storage/
│   │   └── history.py     # SQLite yesterday-vs-today diff
│   └── cli.py             # Click-based CLI
├── brief.yaml             # Source configuration
├── .env.example           # Credential template
├── ARCHITECTURE.md        # Design decisions + data flow
├── PLAN.md                # Task breakdown + checkpoints
└── SKILL.md               # Hermes Agent skill definition
```

---

## 🧪 Adding a New Source

1. Create `daily_briefing/sources/my_source.py`:
```python
class MySource(SourceProtocol):
    name = "my_source"
    def fetch(self, config: dict) -> SourceResult:
        ...
```

2. Register in `orchestrator.py`:
```python
SOURCE_REGISTRY["my_source"] = ("daily_briefing.sources.my_source", "MySource")
```

3. Add to `brief.yaml`:
```yaml
sources:
  my_source:
    enabled: true
    priority: 80
```

No other files need to change. The orchestrator discovers it automatically.

---

## 📄 License

MIT

---

<p align="center">Made with ❤️ by <a href="https://github.com/kvnlnk">kvnlnk</a></p>
