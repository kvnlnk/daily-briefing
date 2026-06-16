# Daily Briefing — Architecture

## Overview

A modular, source-pluggable briefing engine that fetches data from 7 independent sources in parallel, summarizes the results with an LLM provider, and delivers the message through configurable channels. Built for extensibility — third-party sources auto-discover via Python entry points, summarizers and delivery methods are pluggable via protocol classes, and i18n is baked into the prompt layer.

## Tech Stack

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.11 | pip-installable; stdlib-first approach (SQLite, `concurrent.futures`, IMAP) |
| CLI framework | `click` 8.3 | Fast, composable subcommands; auto-help text |
| HTTP client | `requests` 2.31 | All APIs are REST; no async needed |
| Config | YAML (`brief.yaml`) via `PyYAML` 6.0 | Human-editable; .env for secrets |
| Concurrency | `concurrent.futures.ThreadPoolExecutor` | Sources are I/O-bound; threads are idiomatic Python |
| History | SQLite via `sqlite3` stdlib | Zero-dependency local storage for yesterday-vs-today diff |
| RSS parsing | `feedparser` 6.0 | Battle-tested, handles malformed feeds |
| Calendar SDK | `google-api-python-client` | Optional — Google Calendar OAuth |
| GitHub | `gh` CLI via `subprocess` | Already authenticated; no token management in code |
| LLM integration | Pluggable via SummarizerProtocol | prompt-only (default), ollama, openai, anthropic |
| Delivery | Pluggable via DeliveryProtocol | stdout (default), ntfy.sh |
| Package format | `pyproject.toml` (setuptools) | PEP 621 standard |

### What we don't do

- **No async/await** — `concurrent.futures` is simpler and sufficient for <20 I/O-bound sources
- **No web server** — this is a CLI tool, not a service (though it could be wrapped in one)
- **No ORM** — SQLite via stdlib is ~50 lines for our schema
- **No monolithic source registry** — entry points mean third-party packages register themselves

---

## Dependency Graph

```
SourceProtocol (ABC)                               Entry-Point Discovery
    │                                                   │
    ├── WeatherSource      (Open-Meteo - no key)        │
    ├── GitHubSource       (gh CLI - needs auth)        │
    ├── CalendarSource     (Google API - OAuth)         │
    ├── BahnSource         (DB Fahrplan - no key)       │
    ├── RedditSource       (RSS - no key)               │
    ├── NewsSource         (RSS/Atom - no key)          │
    └── EmailSource        (IMAP - needs creds)         │
         │                                              │
         └──→ Orchestrator ◄────────────────────────────┘
              │   brief.yaml → which sources enabled
              │   concurrent.futures → parallel fetch
              │   collects List[SourceResult]
              │
              ├──→ Storage (optional)
              │     writes today's SourceResults to SQLite
              │     loads yesterday's for diff
              │
              └──→ Summarizer ◄── Locale (en.yaml / de.yaml)
                    │   system_instruction + format strings
                    │   variant-aware prompts (morning/evening/weekly)
                    │
                    └──→ Delivery
                          stdout / ntfy / (extensible)
```

**Key property:** Every source is independently testable via `daily-briefing --source weather`. The orchestrator only calls `source.fetch(config)` and collects results — zero coupling between sources.

---

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
      ┌──────────────┐         ┌──────────────────┐
      │   Storage    │         │ Summarizer       │
      │  write today │         │  build_prompt()  │
      │  load yest.  │         │  + locale strings│
      └──────┬───────┘         │  + variant       │
             │ diff            │  + yesterday diff│
             └───────────┬─────┘                  │
                         │   prompt string        │
                         ▼                        │
                  ┌──────────────────┐            │
                  │ Summarizer       │◄───────────┘
                  │ (prompt-only /   │
                  │  ollama / openai │
                  │  / anthropic)    │
                  └────────┬─────────┘
                           │  summarized text
                           ▼
                  ┌──────────────────┐
                  │ Delivery         │
                  │ stdout / ntfy    │
                  └──────────────────┘
```

---

## Module Breakdown

### `daily_briefing/sources/base.py`

- `SourceResult` dataclass: `name`, `priority`, `data`, `error`
- `SourceProtocol` ABC: `def fetch(config: dict) -> SourceResult`
- The error field is the failure path — sources never raise exceptions

### `daily_briefing/sources/{weather,github,calendar,bahn,reddit,news,email}.py`

- One module per data source, each implementing `SourceProtocol`
- External deps vary per source: `requests` (weather, github, bahn), `feedparser` (reddit, news), `google-api-python-client` (calendar), `imaplib`+`email` stdlib (email)
- Each handles its own errors — returns `SourceResult(error=msg)` on failure

### `daily_briefing/orchestrator.py`

- Loads `brief.yaml` → list of enabled sources sorted by priority
- **Entry-Point Discovery:** Calls `importlib.metadata.entry_points(group="daily_briefing.sources")` to discover all installed source packages
- Falls back to hardcoded `SOURCE_REGISTRY` for built-in sources (deprecated)
- `concurrent.futures.ThreadPoolExecutor` fetches all in parallel with 20s timeout
- Returns `List[SourceResult]` sorted by priority

### `daily_briefing/summarizer/base.py`

- `SummarizerResult` dataclass: `text`, `provider`, `model`, `error`
- `SummarizerProtocol` ABC: `def summarize(prompt: str) -> SummarizerResult`
- Provider-agnostic — same interface for local LLMs and cloud APIs

### `daily_briefing/summarizer/__init__.py`

- Provider registry (`PROVIDERS` dict)
- Optional imports for ollama, openai, anthropic — silently skipped if not installed
- Factory function `get_summarizer(name)` returns an instance

### `daily_briefing/summarizer/providers/`

- `prompt_only.py` — Default: prints the prompt as-is (zero config, no LLM needed)
- `ollama_.py` — Local LLMs via Ollama REST API
- `openai_.py` — OpenAI GPT models
- `anthropic.py` — Anthropic Claude models

### `daily_briefing/summarizer/prompts.py`

- Locale-aware prompt builder
- Loads locale strings from `summarizer/locales/{lang}.yaml`
- Supports **variants:** morning, evening, weekly — each has its own system instruction and structure
- Injects source data, yesterday comparison diff, and output constraints (max_length, tone, emoji)
- `_simplify_data()` strips verbose fields from each source before prompting

### `daily_briefing/summarizer/locales/__init__.py`

- `load_locale(lang)` — loads YAML locale file, falls back to English
- `list_locales()` — auto-discovers available locale files
- Results are cached in `_CACHE` after first load

### `daily_briefing/summarizer/locales/{en,de}.yaml`

- Contains system instructions, format strings, source labels, and variant-specific prompts
- Add a new locale by creating `{lang}.yaml` — no code changes needed

### `daily_briefing/delivery/base.py`

- `DeliveryResult` dataclass: `success`, `channel`, `error`
- `DeliveryProtocol` ABC: `def send(message: str, **kwargs) -> DeliveryResult`

### `daily_briefing/delivery/__init__.py`

- Sender registry (`_SENDERS` dict)
- Factory function `get_sender(method)` returns an instance
- `deliver(message, delivery_configs)` sends through all configured channels

### `daily_briefing/delivery/senders/`

- `stdout.py` — Prints to terminal (default, always works)
- `ntfy.py` — Sends via [ntfy.sh](https://ntfy.sh) push notifications
- Extensible — add new senders by implementing `DeliveryProtocol` and registering

### `daily_briefing/storage/history.py`

- SQLite schema: `briefings(id, date, source_name, data_json, created_at)`
- `save(results)`, `load(date)`, `diff(today, yesterday)`
- Yesterday's `data` field enables the LLM to compare (e.g., "3° warmer than yesterday")

### `daily_briefing/cli.py`

- Click-based CLI with subcommands:
  - `daily-briefing` — Run the briefing (default)
  - `daily-briefing setup` — Interactive configuration wizard
  - `daily-briefing doctor` — Configuration diagnostics
- Options: `--source`, `--json`, `--verbose`, `--dry-run`, `--lang`, `--variant`, `--list-sources`
- Pipeline: load config → orchestrate → save history → build prompt → summarize → deliver

---

## Entry-Point Discovery (Third-Party Sources)

Daily Briefing uses **Python entry points** for plugin discovery. This is the primary mechanism for registering sources — both built-in and third-party sources use the same mechanism.

### How it works

1. **Registration:** Source packages declare an entry point in `pyproject.toml`:

   ```toml
   [project.entry-points."daily_briefing.sources"]
   weather = "daily_briefing.sources.weather:WeatherSource"
   my_custom = "my_package.module:MyCustomSource"
   ```

2. **Discovery:** The orchestrator calls `importlib.metadata.entry_points(group="daily_briefing.sources")` to find all installed sources.

3. **Instantiation:** Each entry point is loaded with `.load()`, instantiated, and `fetch(config)` is called.

4. **Fallback:** The hardcoded `SOURCE_REGISTRY` in `orchestrator.py` exists as a fallback for built-in sources. New sources should **only** use entry points.

### Benefits for third-party developers

- **Zero configuration in the core project** — just install your pip package
- **Auto-registration** — sources appear in `daily-briefing --list-sources` immediately
- **Isolation** — your source runs in its own process context, no registry dict to modify

---

## Summarizer Protocol

The summarizer layer is pluggable. All providers implement the same ABC:

```python
class SummarizerProtocol(ABC):
    name: str = ""

    @abstractmethod
    def summarize(self, prompt: str, **kwargs) -> SummarizerResult:
        """Given a built prompt, return summarized text."""
        ...
```

### Available providers

| Provider | Config value | Dependencies | Use case |
|----------|-------------|--------------|----------|
| **Prompt-only** | `prompt-only` | None | Default — prints the raw prompt for manual review or piping |
| **Ollama** | `ollama` | `requests` | Local LLMs (Llama, Mistral, etc.) |
| **OpenAI** | `openai` | `openai` | GPT-4o, GPT-4, GPT-3.5 |
| **Anthropic** | `anthropic` | `anthropic` | Claude 3.5 Sonnet, Claude 3 Opus |

Select the provider in `brief.yaml`:

```yaml
summarizer:
  provider: openai
  model: gpt-4o
```

Defaults to `prompt-only` if unset — zero configuration required to run.

---

## Delivery Protocol

The delivery layer is also pluggable:

```python
class DeliveryProtocol(ABC):
    name: str = ""

    @abstractmethod
    def send(self, message: str, **kwargs) -> DeliveryResult:
        """Send a message through this channel."""
        ...
```

### Available senders

| Sender | Config value | Dependencies | Use case |
|--------|-------------|--------------|----------|
| **stdout** | `stdout` | None | Terminal output (default, always works) |
| **ntfy** | `ntfy` | `requests` | Push notifications via ntfy.sh |

Configured in `brief.yaml` as a list (multiple channels supported):

```yaml
delivery:
  - method: stdout
  - method: ntfy
    topic: my-briefing
```

If no delivery config is provided, stdout is used automatically.

---

## i18n / Locale System

Prompt templates and output strings are separated into locale YAML files:

### File structure

```
daily_briefing/summarizer/locales/
├── __init__.py    # Loader: load_locale(), list_locales()
├── en.yaml        # English (default)
└── de.yaml        # German
```

### How it works

1. The prompt builder calls `load_locale(lang)` where `lang` comes from `brief.yaml` (`output.lang`) or the `--lang` CLI flag.
2. `load_locale()` loads the corresponding `{lang}.yaml` file (cached after first load).
3. If the requested locale doesn't exist, it falls back to `en.yaml`.
4. Locale files contain:
   - **System instructions** — per-variant (morning/evening/weekly)
   - **Format strings** — output constraints, headers, error labels
   - **Source labels** — display names for each source
   - **Diff strings** — yesterday comparison templates

### Adding a locale

1. Copy `en.yaml` to `{lang}.yaml`
2. Translate all strings
3. Done — `list_locales()` auto-discovers it, no registration needed

---

## Configuration (brief.yaml)

```yaml
sources:
  weather:
    enabled: true
    priority: 10
    locations:
      - name: London
        lat: 51.5074
        lon: -0.1278
  github:
    enabled: true
    priority: 30

summarizer:
  provider: prompt-only   # prompt-only | ollama | openai | anthropic

delivery:
  - method: stdout
  # - method: ntfy
  #   topic: my-briefing

output:
  variant: morning        # morning | evening | weekly
  max_length: 800
  tone: friendly          # friendly | concise | technical
  emoji: true
  lang: en
  timezone: Europe/Berlin

# Optional variant overrides
variants:
  evening:
    sources: [weather, calendar, news]
  weekly:
    sources: [weather, calendar, github, news, reddit]
```

### Config resolution order

1. Explicit `--config` CLI argument
2. `BRIEF_CONFIG` environment variable
3. `./brief.yaml` in current directory
4. `~/.config/daily-briefing/brief.yaml`

### Secrets

Credentials go in `.env` (never committed). Each source reads from `os.environ`:

```bash
GITHUB_TOKEN=ghp_xxx
EMAIL_USER=you@gmail.com
EMAIL_PASSWORD=app_password
NTFY_TOPIC=my-briefing
```

---

## Error Handling Strategy

Sources fail independently — one broken source does not block others:

```
SourceResult(name="github", priority=30, data=None, error="401 Unauthorized — check GITHUB_TOKEN")
```

The orchestrator collects all results including failures. The summarizer includes error sources with a note (e.g., "GitHub not available") but still produces a useful briefing from the remaining sources.

### Timeout handling

Each source has a 20-second timeout. If a source hangs (e.g., a slow API), the orchestrator catches `TimeoutError` and returns a `SourceResult(error="Timed out after 20s")` — the other sources are not affected.

---

## Variants

Three built-in briefing variants are supported:

| Variant | Focus | Config key |
|---------|-------|-----------|
| **Morning** 🌅 | Full overview of the day ahead — weather, calendar, GitHub, news, etc. | `morning` |
| **Evening** 🌆 | Recap of what happened today — tomorrow's weather, today's activity | `evening` |
| **Weekly** 📊 | Weekly overview — week's weather trend, upcoming events, GitHub summary | `weekly` |

Each variant has its own system instruction and structure in the locale files. Optionally, you can limit which sources run for each variant using the `variants` section in `brief.yaml`.

---

## What's Deferred

- **OAuth flow for Google Calendar.** Current approach uses the `google-api-python-client` SDK with a pre-authenticated token. An in-code OAuth flow adds 200+ lines and a dependency — deferred until needed.
- **Push notification delivery beyond ntfy.sh.** The delivery protocol is ready for new senders; we just haven't added them yet.
- **Async runtime.** `concurrent.futures` is sufficient for the current 7 sources. If scaling to 50+ sources, `asyncio` or `anyio` might become worthwhile.
