---
name: daily-briefing
description: "Fetch and summarize morning briefing from weather, GitHub, calendar, Reddit, news, and more — delivered as one WhatsApp message."
version: 0.1.0
---

# Daily Briefing Skill for Hermes

Runs the daily-briefing pipeline and delivers the result to your messaging
platform of choice.

## Prerequisites

1. The `daily-briefing` Python package installed:
   ```bash
   cd /path/to/daily-briefing && pip install -e .
   ```

2. `brief.yaml` configured with your enabled sources.

3. `.env` file with any required credentials (GitHub token, calendar OAuth, IMAP).

## Cron Setup

Create a Hermes cron job to run every morning at 06:30:

```
hermes cron create --name "Daily Briefing" --schedule "30 6 * * *" \
  --prompt "Run: cd /path/to/daily-briefing && python -m daily_briefing. Using the output, summarize into one WhatsApp message in German with emoji. Keep it under 800 characters. Deliver to the user." \
  --skills daily-briefing
```

## Manual Run

```bash
cd /path/to/daily-briefing
python -m daily_briefing --verbose
```

## Developing

All source modules live in `daily_briefing/sources/`. To add a new source:

1. Create `daily_briefing/sources/my_source.py`
2. Implement `class MySource(SourceProtocol)` with `fetch(config) -> SourceResult`
3. Register it in `orchestrator.py` → `SOURCE_REGISTRY`
4. Add config to `brief.yaml`

See `ARCHITECTURE.md` and `PLAN.md` for full design docs.
