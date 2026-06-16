# Contributing to Daily Briefing

Thanks for your interest! Daily Briefing is an open-source project built with a focus on clean architecture, testability, and extensibility. Below are the conventions and workflows we follow.

---

## Code Style

- **Linter:** [ruff](https://docs.astral.sh/ruff/) (configured in `pyproject.toml`)
- **Line length:** 100 characters
- **Target Python:** 3.11+
- **Formatting:** ruff's default rules — run before committing:

```bash
ruff check . && ruff format . --check
```

---

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Purpose |
|--------|---------|
| `feat:` | A new feature or source |
| `fix:` | A bug fix |
| `chore:` | Build, CI, dependencies, tooling |
| `docs:` | Documentation changes |
| `refactor:` | Code change that neither fixes nor adds |
| `test:` | Adding or updating tests |
| `i18n:` | Locale / translation changes |

Examples:

```
feat(sources): add hackernews RSS source
fix(scheduler): handle timezone-aware datetime comparison
docs: update source-authoring guide with example
```

---

## Development Workflow

### 1. Set up a development environment

```bash
git clone https://github.com/kvnlnk/daily-briefing.git
cd daily-briefing
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

This installs the package in editable mode plus dev dependencies (pytest, ruff).

### 2. TDD: RED → GREEN → REFACTOR

We follow test-driven development for non-trivial changes:

1. **RED** — Write a failing test for the new behaviour
2. **GREEN** — Implement the minimal code to make it pass
3. **REFACTOR** — Clean up while keeping tests green

### 3. Run tests

```bash
python -m pytest          # All tests
python -m pytest -v       # Verbose
python -m pytest --cov    # With coverage
python -m pytest tests/test_sources/  # Source tests only
```

### 4. Run the project locally

```bash
cp brief.example.yaml brief.yaml   # Customize as needed
daily-briefing setup               # Interactive config
daily-briefing doctor              # Verify config
daily-briefing --source weather    # Test a single source
daily-briefing --dry-run           # Full fetch, no LLM
daily-briefing --verbose           # Full run with debug output
```

---

## Adding a Source

See the full guide at [docs/source-authoring.md](docs/source-authoring.md).

In short:

1. Create a class implementing `SourceProtocol` with a `fetch()` method
2. Return `SourceResult` with `data` on success or `error` on failure
3. Register the entry point in `pyproject.toml` under `[project.entry-points."daily_briefing.sources"]`
4. Add tests in `tests/test_sources/`
5. Add locale strings in `daily_briefing/summarizer/locales/{en,de}.yaml`

For a working example, see `examples/daily-briefing-source-example/`.

### Built-in sources

These are registered in `pyproject.toml` and also have a fallback in the hardcoded `SOURCE_REGISTRY` in `orchestrator.py`. New sources should **only** use entry points — the hardcoded registry is deprecated.

---

## Adding a Locale

1. Create `daily_briefing/summarizer/locales/{lang}.yaml` (copy `en.yaml` as a template)
2. Translate all strings
3. The locale is auto-discovered — no registration needed beyond dropping the file

Supported locales: `en` (default), `de`. More welcome!

---

## Adding a Summarizer Provider

1. Create `daily_briefing/summarizer/providers/{provider_name}.py`
2. Implement `SummarizerProtocol` (a single `summarize(prompt)` method)
3. Register in `daily_briefing/summarizer/__init__.py` by adding to the `PROVIDERS` dict

---

## Adding a Delivery Method

1. Create `daily_briefing/delivery/senders/{name}.py`
2. Implement `DeliveryProtocol` (a single `send(message, **kwargs)` method)
3. Register in `daily_briefing/delivery/__init__.py` by adding to the `_SENDERS` dict

---

## Project Structure

```
daily-briefing/
├── daily_briefing/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                # Click-based CLI entry point
│   ├── config.py             # YAML config loader + dataclasses
│   ├── doctor.py             # Diagnostics / health check
│   ├── setup_wizard.py       # Interactive setup wizard
│   ├── orchestrator.py       # Parallel fetch + entry-point discovery
│   ├── sources/              # Data source modules
│   │   ├── base.py           # SourceProtocol ABC + SourceResult
│   │   ├── weather.py
│   │   ├── github.py
│   │   ├── calendar.py
│   │   ├── bahn.py
│   │   ├── reddit.py
│   │   ├── news.py
│   │   └── email.py
│   ├── summarizer/
│   │   ├── base.py           # SummarizerProtocol ABC + SummarizerResult
│   │   ├── __init__.py       # Provider registry
│   │   ├── prompts.py        # Prompt builder (locale-aware)
│   │   ├── locales/          # i18n YAML files
│   │   │   ├── en.yaml
│   │   │   └── de.yaml
│   │   └── providers/        # LLM backends
│   │       ├── prompt_only.py
│   │       ├── ollama_.py
│   │       ├── openai_.py
│   │       └── anthropic.py
│   ├── delivery/
│   │   ├── base.py           # DeliveryProtocol ABC + DeliveryResult
│   │   ├── __init__.py       # Sender registry
│   │   └── senders/
│   │       ├── stdout.py
│   │       └── ntfy.py
│   └── storage/
│       └── history.py        # SQLite yesterday comparison
├── tests/                    # Test suite
├── examples/                 # Third-party source example
├── docs/                     # Documentation
├── brief.yaml                # User configuration (gitignored)
├── brief.example.yaml        # Configuration template
├── .env.example              # Credential template
└── pyproject.toml            # Package metadata + entry points
```

---

## Need Help?

Open a [GitHub Issue](https://github.com/kvnlnk/daily-briefing/issues) or start a Discussion. We're friendly!
