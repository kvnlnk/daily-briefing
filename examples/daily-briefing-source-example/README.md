# Daily Briefing — Example Source Package

This is an example third-party data source for [Daily Briefing](https://github.com/kvnlnk/daily-briefing).

It adds a **Quote of the Day** source that fetches random quotes from quotable.io.

## Install

```bash
pip install -e examples/daily-briefing-source-example
```

## Verify

```bash
daily-briefing --list-sources
# → quote should appear

daily-briefing --source quote
# → returns a random quote
```

## Add to your briefing

Add to `brief.yaml`:

```yaml
sources:
  quote:
    enabled: true
    priority: 80
```

## How it works

This package registers itself via a setuptools entry point in `pyproject.toml`:

```toml
[project.entry-points."daily_briefing.sources"]
quote = "daily_briefing_source_quote.source:QuoteSource"
```

Daily Briefing discovers it at runtime — no fork, no edit of core code.
