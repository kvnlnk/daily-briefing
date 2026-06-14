# Daily Briefing — Handoff

## What Was Built

A modular, source-pluggable morning briefing engine that fetches data from 7
independent sources in parallel and produces an LLM-ready prompt for a single
WhatsApp message.

**Status:** Core complete. 14 incremental commits following agent-skills
methodology (plan → vertical slices → atomic commits).

## How to Run Locally

```bash
cd /path/to/daily-briefing
pip install -e .    # Install the package (adds feedparser)
cp .env.example .env   # Fill in your credentials
# Edit brief.yaml to enable desired sources
python -m daily_briefing --verbose
```

## Live Test Results (2026-06-15)

```
✅ Weather — 17.8°C, partly cloudy, Frankfurt
❌ Calendar — OAuth not set up yet
✅ GitHub — 0 issues, 0 PRs (quiet day)
❌ Bahn — API unreachable from this server (works on user VPS)
✅ Reddit — 3 top posts from r/programming
✅ News — 6 headlines from heise.de + dev.to
```

6 sources fetched in 10.2 seconds (parallel).

## Required Secrets

| Secret | Where | How to get |
|---|---|---|
| `GITHUB_TOKEN` | `.env` | https://github.com/settings/tokens (classic, `repo` scope) |
| Google OAuth | `~/.hermes/google_token.json` | Hermes `google-workspace` skill setup |
| `EMAIL_USER` + `EMAIL_PASSWORD` | `.env` | Gmail App Password (optional, disabled by default) |

All APIs without keys: Open-Meteo (weather), DB Fahrplan (bahn), Reddit RSS, RSS/Atom feeds (news).

## What's Missing / Next Steps

1. **Google Calendar OAuth setup** — Run the Hermes `google-workspace` skill setup to authenticate Google Calendar. The code is ready; it just needs the token.
2. **DB Fahrplan API reachability** — The `v6.db.transport.rest` API is blocked from some hosting environments. Test from your VPS. If blocked there too, switch to the official Deutsche Bahn API (requires free registration at developers.deutschebahn.com).
3. **Hermes cron job** — Create a cron to run every morning at 6:30, pipe the prompt to the LLM, and deliver via WhatsApp:
   ```
   hermes cron create --name "Daily Briefing" --schedule "30 6 * * *" \
     --prompt "Run daily-briefing, summarize into one German WhatsApp message with emoji (max 800 chars), deliver to user." \
     --skills daily-briefing
   ```
4. **LLM tuning** — The prompt template in `summarizer/prompts.py` may need tweaking based on your LLM's output style. The data is correct; the LLM's phrasing is what you'll iterate on.
5. **Custom news feeds** — Add your favorite RSS feeds to `.env` or `brief.yaml`.
6. **Tests** — No test suite yet. Consider adding pytest for each source module (mock the HTTP calls).

## Architecture Decisions (Surprising)

- **`gh` CLI over GitHub REST API.** Simpler than managing tokens in code. The REST API `/notifications` endpoint requires the `notifications` scope which many personal tokens don't have. The `gh` CLI uses GraphQL internally and works with just `repo` scope.
- **`feedparser` over `praw` for Reddit.** Reddit's official API requires app registration and API keys. The public RSS endpoint (`reddit.com/r/{sub}/top/.rss`) has zero auth and covers our use case perfectly.
- **One SQLite table.** No ORM, no migrations, no complexity. `sqlite3` stdlib handles yesterday-vs-today comparison in 50 lines.
- **Sources fail independently.** The orchestrator collects errors alongside successes. A broken Bahn API doesn't block the weather from appearing in your briefing.
- **`click` over `argparse`.** Already installed, better help text, composable subcommands.
- **Email via `imaplib` stdlib, not `himalaya`.** Zero additional deps. `himalaya` can be added later if you want richer email features.

## File Inventory

```
daily-briefing/
├── ARCHITECTURE.md      # Full design doc with dependency graph
├── PLAN.md              # 14-task breakdown with checkpoints
├── README.md            # User-facing docs (emojis, Vibecoded badge, MIT)
├── HANDOFF.md           # This file
├── SKILL.md             # Hermes Agent skill definition
├── brief.yaml           # Per-source config (enabled, priority)
├── .env.example         # Secrets template
├── .gitignore
├── pyproject.toml
├── daily_briefing/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py        # YAML loader + typed dataclasses
│   ├── orchestrator.py  # Parallel fetch + SOURCE_REGISTRY
│   ├── cli.py           # Click-based CLI (--source, --verbose, --json)
│   ├── sources/
│   │   ├── base.py      # SourceProtocol ABC + SourceResult
│   │   ├── weather.py   # Open-Meteo
│   │   ├── github.py    # gh CLI
│   │   ├── calendar.py  # Google Calendar
│   │   ├── bahn.py      # DB Fahrplan
│   │   ├── reddit.py    # Reddit RSS
│   │   ├── news.py      # RSS/Atom
│   │   └── email.py     # IMAP
│   ├── summarizer/
│   │   └── prompts.py   # LLM prompt builder
│   └── storage/
│       └── history.py   # SQLite history + diff
```

## Commit History (14 commits)

```
6a2d51e feat(core): add LLM prompt builder and CLI entry point
c63f926 feat(core): add SQLite storage with yesterday-vs-today diff
87c2275 feat(core): add orchestrator with parallel source fetching
7e276de feat(source): add email source via imaplib
8fe9ac8 feat(source): add bahn source via DB transport.rest API
ae3a6c0 feat(source): add calendar source via Google Calendar API
b0ea04d feat(source): add news source via RSS/Atom feeds
018063d feat(source): add reddit source via public RSS feeds
22cf970 feat(source): add github source via gh CLI
26a22cf feat(source): add weather source via Open-Meteo free API
4ab2e9c feat(base): add SourceProtocol ABC and config loader
ab1928b docs: add ARCHITECTURE and PLAN
6fcda0f chore: initial project scaffold
```
