# Authoring a Daily Briefing Source

This guide walks you through creating a **third-party data source** for Daily Briefing. Sources are pip-installable packages that auto-register via Python entry points — no changes to the core project needed.

---

## Table of Contents

1. [The SourceProtocol](#the-sourceprotocol)
2. [Handling Errors Gracefully](#handling-errors-gracefully)
3. [Reading Config](#reading-config)
4. [Registering the Entry Point](#registering-the-entry-point)
5. [Making It Pip-Installable](#making-it-pip-installable)
6. [Full Example: Quote of the Day](#full-example-quote-of-the-day)
7. [Testing Your Source](#testing-your-source)
8. [Best Practices](#best-practices)

---

## The SourceProtocol

Every source implements the `SourceProtocol` ABC from `daily_briefing.sources.base`:

```python
from daily_briefing.sources.base import SourceProtocol, SourceResult

class MySource(SourceProtocol):
    name = "my_source"

    def fetch(self, config: dict) -> SourceResult:
        # Fetch data, return SourceResult
        ...
```

### SourceResult

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Machine-readable source name (matches `self.name`) |
| `priority` | `int` | Display order — lower numbers appear first |
| `data` | `dict \| None` | Parsed result data on success |
| `error` | `str \| None` | Human-readable error message on failure |

### What `fetch()` should return

**On success:**

```python
return SourceResult(
    name=self.name,
    priority=50,
    data={
        "temperature": 22.5,
        "condition": "Sunny",
        "humidity": 45,
    },
)
```

**On failure:**

```python
return SourceResult(
    name=self.name,
    priority=50,
    error="API returned 503 — service unavailable",
)
```

---

## Handling Errors Gracefully

**Never raise exceptions from `fetch()`.** The orchestrator wraps each source in a timeout, but unhandled exceptions from your code produce a generic error message. Instead, catch expected failures and return a `SourceResult` with an informative `error` field.

```python
def fetch(self, config: dict) -> SourceResult:
    try:
        resp = requests.get("https://api.example.com/data", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return SourceResult(
            name=self.name,
            priority=50,
            data={"value": data["value"]},
        )
    except requests.RequestException as e:
        return SourceResult(
            name=self.name,
            priority=50,
            error=f"Example API error: {e}",
        )
```

This is the contract: **always return a SourceResult, never raise.** The orchestrator collects all results (successes and failures) and the summarizer handles errors gracefully, producing a useful briefing even when some sources are down.

---

## Reading Config

Your source receives the **full parsed YAML config** as the `config` dict. Read your source's section from `config['sources'][self.name]`, plus any environment variables.

```python
def fetch(self, config: dict) -> SourceResult:
    # Source-specific config from brief.yaml
    my_config = config.get("sources", {}).get(self.name, {})
    api_key = my_config.get("api_key", "")

    # Or read from environment
    import os
    api_key = os.environ.get("MY_SOURCE_API_KEY", "")

    # User settings
    city = my_config.get("city", "London")
    ...
```

The config dict is always the full parsed YAML, so you can also read global sections if needed:

```python
timezone = config.get("output", {}).get("timezone", "UTC")
```

---

## Registering the Entry Point

Add an entry point to your package's `pyproject.toml` under the group `daily_briefing.sources`:

```toml
[project.entry-points."daily_briefing.sources"]
my_source = "my_package.module:MySource"
```

The entry point name (`my_source`) becomes the source name used in `brief.yaml` and on the CLI:

```yaml
sources:
  my_source:
    enabled: true
    priority: 80
```

After installing your package, the source appears in `daily-briefing --list-sources` automatically — no registration code needed in the core project.

---

## Making It Pip-Installable

A minimal `pyproject.toml` for a source package:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "daily-briefing-source-my-source"
version = "0.1.0"
description = "Daily Briefing source — My Source"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31",
]

[tool.setuptools.packages.find]
where = ["src"]

[project.entry-points."daily_briefing.sources"]
my_source = "my_package.module:MySource"
```

Install locally:

```bash
pip install -e .
```

Or publish to PyPI and your users install normally:

```bash
pip install daily-briefing-source-my-source
```

---

## Full Example: Quote of the Day

This is a complete, working third-party source package. It's also available at `examples/daily-briefing-source-example/` in the repo.

### Project structure

```
daily-briefing-source-example/
├── pyproject.toml
└── src/
    └── daily_briefing_source_example/
        ├── __init__.py
        └── source.py
```

### `src/daily_briefing_source_example/source.py`

```python
"""Quote of the Day source — example third-party package for Daily Briefing."""

from __future__ import annotations

from typing import Any

import requests

from daily_briefing.sources.base import SourceProtocol, SourceResult


QUOTE_API = "https://api.quotable.io/random"


class QuoteSource(SourceProtocol):
    """Fetches a random quote from quotable.io."""

    name = "quote"

    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch a random quote."""
        try:
            resp = requests.get(
                QUOTE_API,
                params={"maxLength": 200},
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()

            return SourceResult(
                name=self.name,
                priority=80,
                data={
                    "content": body.get("content", ""),
                    "author": body.get("author", "Unknown"),
                    "tags": body.get("tags", []),
                },
            )
        except requests.RequestException as e:
            return SourceResult(
                name=self.name,
                priority=80,
                error=f"Quote API error: {e}",
            )
```

### `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "daily-briefing-source-example"
version = "0.1.0"
description = "Daily Briefing source — Quote of the Day (example third-party package)"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31",
]

[tool.setuptools.packages.find]
where = ["src"]

[project.entry-points."daily_briefing.sources"]
quote = "daily_briefing_source_example.source:QuoteSource"
```

### Install and test

```bash
pip install -e examples/daily-briefing-source-example

# Verify it's discovered
daily-briefing --list-sources

# Test single source
daily-briefing --source quote

# Enable it in brief.yaml
```

---

## Testing Your Source

Add tests in your own package:

```python
# tests/test_quote_source.py
from daily_briefing_source_example.source import QuoteSource

def test_quote_source_returns_result():
    source = QuoteSource()
    result = source.fetch({"sources": {"quote": {}}})
    assert result.name == "quote"
    assert result.is_success() or result.error is not None
```

Run with pytest:

```bash
python -m pytest tests/
```

---

## Best Practices

1. **Be a good citizen.** Respect API rate limits — cache responses where appropriate.
2. **Handle timeouts.** Pass `timeout` to all HTTP calls (10 seconds is a good default).
3. **Return clean data.** Avoid deeply nested structures. The prompt builder simplifies data for the LLM, but you can also implement `_simplify_data` customisation.
4. **Use env vars for secrets.** Don't hardcode API keys. Let users set them in `.env`.
5. **Document source-specific config.** Add comments in your source example config so users know what to set.
6. **Name your entry point consistently.** Use the same name in the entry point and `self.name`.
7. **Don't depend on `daily_briefing` internals.** Only import `SourceProtocol` and `SourceResult` from `daily_briefing.sources.base` — everything else is an implementation detail that may change.
