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

Combine with a Hermes cron job:

```
hermes cron create --schedule "30 6 * * *" \
  --prompt "Fetch the daily briefing using briefing_skill.run_full_briefing() and deliver the summary to me." \
  --skills briefing_skill
```

## Manual Run

```bash
cd /path/to/daily-briefing
daily-briefing --json --dry-run --variant morning
```

## Developing

All source modules live in `daily_briefing/sources/`. To add a new source:

1. Create `daily_briefing/sources/my_source.py`
2. Implement `class MySource(SourceProtocol)` with `fetch(config) -> SourceResult`
3. Register in `pyproject.toml` under `[project.entry-points."daily_briefing.sources"]`
4. Add config to `brief.yaml`

See `ARCHITECTURE.md` for full design docs.
