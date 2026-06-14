# Daily Briefing — Architecture

## Overview

A modular, source-pluggable morning briefing engine that fetches data from 7
independent sources in parallel and uses an LLM to produce one concise WhatsApp
message. Designed as a Hermes Agent Skill Set — each source module is a
standalone `fetch()` function with a uniform interface, so adding or removing
sources requires zero changes to the orchestrator.

## Tech Stack

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.11 | Already on this system; pip-installable; readable for skill integration |
| CLI framework | `click` 8.3 (already installed) | Fast, composable subcommands; no new dep |
| Terminal output | `rich` 14.3 (already installed) | Beautiful tables/progress for `--verbose` mode |
| HTTP client | `requests` 2.33 (already installed) | All APIs are REST; no async needed |
| Config | YAML (`brief.yaml`) via `PyYAML` 6.0 (already installed) | Also `ruamel.yaml` available for round-trip edits |
| Concurrency | `concurrent.futures.ThreadPoolExecutor` | Sources are I/O-bound; threads are idiomatic Python |
| History | SQLite via `sqlite3` stdlib | Zero-dependency local storage for yesterday-vs-today diff |
| RSS parsing | `feedparser` (one new dep) | Battle-tested, handles malformed feeds; used for Reddit + News |
| Calendar SDK | `google-api-python-client` (already installed) | Hermes `google-workspace` skill has OAuth setup script |
| GitHub | `gh` CLI via `subprocess` (already installed) | Already authenticated; no token management in code |
| Package format | `pyproject.toml` (setuptools) | PEP 621 standard |
| LLM integration | External (Hermes manages this) | This project produces the *text*; Hermes cron + LLM handles summarization |
| Delivery | Hermes `send_message` | One function call from the SKILL.md, no delivery code in this repo |

### Existing tools leveraged (not rebuilt)

| Tool | Installed | Used for | How |
|---|---|---|---|
| `gh` CLI | ✅ | GitHub notifications + PRs | `subprocess.run(["gh", "api", ...])` |
| `google-api-python-client` | ✅ | Google Calendar events | Direct SDK usage, OAuth via `google-workspace` skill |
| `feedparser` | ⬜ `pip install` | Reddit RSS + News RSS | Universal RSS/Atom parser |
| `himalaya` | ⬜ `pip install` (or `imaplib`) | Email unread count | PIP-installable CLI or stdlib fallback |
| Open-Meteo | 🌐 Free REST API | Weather | Direct `requests.get()`, no wrapper needed |
| DB transport.rest | 🌐 Free REST API | Bahn departures | Direct `requests.get()` (tested: reachable from user VPS) |
| Reddit RSS | 🌐 Free, no auth | Reddit top posts | `reddit.com/r/{sub}/top/.rss` |

**Deliberate non-choices:**
- **No `openmeteo-requests` wrapper** — the REST API is 1 GET call; a wrapper adds a dep for zero benefit
- **No `praw` (Reddit SDK)** — requires API key + app registration; RSS is zero-auth and sufficient for top posts
- **No `blogwatcher-cli`** — overkill; `feedparser` handles our 2-3 feeds perfectly
- No FastAPI/Flask — this is a CLI tool, not a server
- No `asyncio` — added complexity without benefit for 7 I/O-bound sources
- No ORM for SQLite — `sqlite3` stdlib is 50 lines for our schema

## Dependency Graph

```
SourceProtocol (ABC)
    │
    ├── WeatherSource      (Open-Meteo API — no key needed)
    ├── GitHubSource       (GitHub REST API — needs GITHUB_TOKEN)
    ├── CalendarSource     (Google Calendar via gws CLI stdout — no code dep)
    ├── BahnSource         (DB Fahrplan API — no key needed)
    ├── RedditSource       (Reddit RSS feeds — no key needed)
    ├── NewsSource         (RSS/Atom feeds — no key needed)
    └── EmailSource        (IMAP — needs EMAIL_USER/PASSWORD)
         │
         └──→ Orchestrator
              │   config.yaml → which sources enabled
              │   concurrent.futures → parallel fetch
              │   collects List[SourceResult]
              │
              ├──→ Storage (optional)
              │     writes today's SourceResults to SQLite
              │     loads yesterday's for diff
              │
              └──→ Summarizer
                    builds LLM prompt from SourceResults + yesterday diff
                    formats for WhatsApp (~800 char max)
```

**Key property:** Every source is independently testable via `python -m daily_briefing --source weather`. The orchestrator only calls `source.fetch(config)` and collects results — zero coupling between sources.

## Data Flow

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Weather  │   │ GitHub   │   │ Calendar │   │  Bahn    │  ... (7 sources)
│ fetch()  │   │ fetch()  │   │ fetch()  │   │ fetch()  │
└────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │              │
     └──────────────┴──────┬───────┴──────────────┘
                           │  SourceResult(name, priority, data, error)
                           ▼
                    ┌──────────────┐
                    │ Orchestrator │  parallel via ThreadPoolExecutor
                    └──────┬───────┘
                           │  List[SourceResult]
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      ┌──────────────┐         ┌──────────────┐
      │   Storage    │         │  Summarizer  │
      │  write today │         │  build prompt│
      │  load yest.  │         │  for LLM     │
      └──────┬───────┘         └──────┬───────┘
             │ diff                   │ text
             └───────────┬────────────┘
                         ▼
                  ┌──────────────┐
                  │   Output     │  ≤800 char WhatsApp message
                  │   (stdout)   │
                  └──────────────┘
```

## Module Breakdown

### `daily_briefing/sources/base.py`
- `SourceResult` dataclass: `name`, `priority`, `data`, `error`
- `SourceProtocol` ABC: `def fetch(config: dict) -> SourceResult`
- Each source inherits and implements `fetch()`

### `daily_briefing/sources/{weather,github,calendar,bahn,reddit,news,email}.py`
- One module per data source
- External deps per source: `requests` (weather, github, bahn), `feedparser` (reddit, news), `subprocess` (calendar via `gws` CLI), `imaplib` + `email` stdlib (email)
- Each handles its own errors internally, returns `SourceResult(error=msg)` on failure

### `daily_briefing/orchestrator.py`
- Loads `brief.yaml` → list of enabled sources sorted by priority
- `concurrent.futures.ThreadPoolExecutor` fetches all in parallel
- Returns `List[SourceResult]`

### `daily_briefing/summarizer/prompts.py`
- Prompt templates for the LLM summarization step
- Templates: `morning_brief`, `compact` (for WhatsApp size limit)
- Injects source data + yesterday comparison

### `daily_briefing/summarizer/format.py`
- `format_for_whatsapp(results, yesterdays_results, config)` → `str`
- Applies `max_length`, emoji mode, tone from config
- Returns rendered text ready for delivery

### `daily_briefing/storage/history.py`
- SQLite schema: `briefings(id, date, source_name, data_json, created_at)`
- `save(results)`, `load(date)`, `diff(today, yesterday)`
- Yesterdays `data` field enables LLM to say "wärmer als gestern"

### `daily_briefing/cli.py`
- Argparse: `--source <name>` for single-source test, `--config <path>`, `--verbose`
- Main entry: load config → orchestrate → summarize → print

## Error Handling Strategy

Sources fail independently — one broken source does not block others:
```
SourceResult(name="github", priority=30, data=None, error="401 Unauthorized — check GITHUB_TOKEN")
```
The orchestrator collects all results including failures. The summarizer includes
error sources with a note like "(GitHub nicht verfügbar)" but still produces
a useful briefing from the remaining sources.

## Configuration (brief.yaml)

```yaml
sources:
  weather: {enabled: true, priority: 10}
  calendar: {enabled: true, priority: 20}
  # ...
output:
  max_length: 800
  tone: friendly
  emoji: true
  include_diff: true
```

## Deferred / Changed

*Deferred:* **OAuth flow for Google Calendar.** Current approach uses `gws` CLI
which the user has already authenticated. An in-code OAuth flow adds 200+ lines
and a dependency (google-auth) — deferred until needed.

*Deferred:* **Push notification delivery.** This module produces text. Hermes
cron + `send_message` handles delivery. Adding delivery logic here would violate
single-responsibility.

*Deferred:* **DB Fahrplan "Verspätungs-Alarm".** This source fetches the
scheduled departure at your configured time. The "Pendler-Alarm" (check every
2 min, alert on delays) is a separate cron job that would use this same source
module — but that intelligence lives in a different SKILL.md, not here.
