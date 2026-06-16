# Daily Briefing — Product Generalization Design

> **Status:** Draft for review
> **Date:** 2026-06-16
> **Author:** kvnlnk

## 1. North Star

> 1. A stranger in a different city, with different interests and NO Hermes Agent, can
>    `pipx install daily-briefing`, run `daily-briefing setup`, fill in config, and get
>    a complete delivered briefing — without ever touching a `.py` file.
> 2. A third party can publish their own data source as a SEPARATE pip package that
>    auto-registers without forking or editing core code.

Every design decision is measured against these two sentences.

---

## 2. Design Decisions (Answered Questions)

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Default LLM Provider | `prompt-only` (default), `ollama`, `openai`, `anthropic` as optional | Zero-key startup; local-first; cloud opt-in |
| 2 | Delivery channels | `stdout` + `ntfy` (both) | stdout = zero-config, ntfy = easiest push without phone number |
| 3 | PyPI publish? | Prepare metadata, don't publish. pipx-from-GitHub is enough. | Low maintenance, zero publishing friction for early adopters |
| 4 | Git history rewrite? | No. Clean from HEAD forward only. | Public repo — rewrite destroys forks/stars/issues |
| 5 | Languages | `de` + `en` with YAML locale files, extensible. Default: `en`. | i18n-ready without code changes; two languages covers 95% of dev audience |
| 6 | CLI command name | `daily-briefing setup` instead of `daily-briefing init` | User preference |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      daily-briefing CLI                      │
│  (console_scripts entrypoint → click group)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  daily-briefing setup     ─── interactive config wizard      │
│  daily-briefing           ─── run full briefing              │
│  daily-briefing doctor    ─── validate config + credentials  │
│  daily-briefing --list-sources  ─── show available sources   │
│  daily-briefing --source X      ─── single source debug      │
│  daily-briefing --variant M/E/W ─── variant briefing         │
│  daily-briefing --lang de/en    ─── language override        │
│  daily-briefing --dry-run       ─── fetch only, no deliver   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Config   │───▶│ Orchestrator │───▶│  Summarizer  │       │
│  │  Loader   │    │              │    │  (pluggable) │       │
│  └──────────┘    │ • Entry-Pt   │    └──────┬───────┘       │
│                  │   Discovery  │           │                │
│                  │ • Parallel   │    ┌──────▼───────┐       │
│                  │   Fetch      │    │  Delivery    │       │
│                  │ • Priority   │    │  (pluggable) │       │
│                  │   Sort       │    └──────────────┘       │
│                  └──────┬───────┘                           │
│                         │                                   │
│              ┌──────────▼──────────┐                        │
│              │  Source Registry    │                        │
│              │  (Entry-Points)     │                        │
│              │  ↓ discover at      │                        │
│              │    runtime          │                        │
│              └─────────────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Packages & Responsibilities

| Package | Responsibility | Deps |
|---------|---------------|------|
| `daily_briefing/` | CLI, config, orchestration | click, pyyaml, requests |
| `daily_briefing/sources/` | Data source modules | varies per source |
| `daily_briefing/sources/base.py` | `SourceProtocol` + `SourceResult` | none (stdlib) |
| `daily_briefing/summarizer/` | LLM summarization (pluggable) | (optional) openai, anthropic |
| `daily_briefing/delivery/` | Output delivery (pluggable) | (optional) requests for ntfy |
| `daily_briefing/storage/` | SQLite history + diff | none (stdlib) |

### 3.2 Entry-Point Plugin Discovery (P5 — Core)

The critical architectural change:

**Before (hardcoded):**
```python
# orchestrator.py
SOURCE_REGISTRY = {
    "weather": ("daily_briefing.sources.weather", "WeatherSource"),
}
```

**After (discovery):**
```python
# orchestrator.py — at startup
import importlib.metadata
entry_points = importlib.metadata.entry_points(group="daily_briefing.sources")
for ep in entry_points:
    SOURCE_REGISTRY[ep.name] = ep

# pyproject.toml (built-in sources)
[project.entry-points."daily_briefing.sources"]
weather = "daily_briefing.sources.weather:WeatherSource"
github = "daily_briefing.sources.github:GitHubSource"
# ... etc.

# Third-party package (e.g. daily-briefing-source-spotify)
[project.entry-points."daily_briefing.sources"]
spotify = "my_package:SpotifySource"
```

The entry point stores a reference: the `load()` method of `importlib.metadata.EntryPoint` lazily imports the module and returns the class, so discovery is cheap even with many third-party packages installed.

**Transition plan:** Both systems co-exist during migration. If an entry point is found via traditional `SOURCE_REGISTRY` *and* via entry points, the entry point wins (new system). Documented in `ARCHITECTURE.md` as the one true registration mechanism.

---

## 4. Detailed Component Design

### 4.1 Config (`daily_briefing/config.py`)

**Existing types** — keep but extend:

```python
@dataclass
class OutputConfig:
    max_length: int = 800
    include_diff: bool = True
    tone: str = "friendly"
    emoji: bool = True
    timezone: str = "Europe/Berlin"
    lang: str = "en"  # NEW

class BriefingConfig:
    @property
    def enabled_sources(self) -> list[SourceConfig]: ...
    @property
    def delivery(self) -> DeliveryConfig: ...  # NEW
    @property
    def summarizer(self) -> SummarizerConfig: ...  # NEW
```

**Config flow:**
1. `daily-briefing setup` creates `brief.yaml` + `.env` from templates
2. At runtime: `brief.yaml` → `BriefingConfig`, `.env` → `os.environ`
3. `.env` precedence: env vars > .env file > defaults in code

### 4.2 Source Discovery (`daily_briefing/orchestrator.py`)

```python
def discover_sources() -> dict[str, importlib.metadata.EntryPoint]:
    """Discover all installed daily_briefing.sources entry points."""
    eps = importlib.metadata.entry_points(group="daily_briefing.sources")
    return {ep.name: ep for ep in eps}
```

Backward compat: hardcoded `SOURCE_REGISTRY` becomes a **fallback** for 1 release, then removed.

### 4.3 Summarizer Protocol (P2 — NEW)

```python
# daily_briefing/summarizer/base.py
class SummarizerProtocol(ABC):
    name: str  # e.g. "prompt-only", "ollama", "openai", "anthropic"
    def summarize(self, prompt: str, config: OutputConfig) -> SummarizerResult: ...

@dataclass
class SummarizerResult:
    text: str
    provider: str
    error: str | None = None
```

Concrete providers:

| Provider | Key | When selected |
|----------|-----|---------------|
| `prompt-only` | None | Default — prints prompt, user pipes it elsewhere |
| `ollama` | `OLLAMA_BASE_URL` (default: localhost:11434) + `OLLAMA_MODEL` | Local LLM, zero cost |
| `openai` | `OPENAI_API_KEY` | Cloud GPT |
| `anthropic` | `ANTHROPIC_API_KEY` | Cloud Claude |

Selection via `brief.yaml`:
```yaml
summarizer:
  provider: ollama       # prompt-only | ollama | openai | anthropic
  model: llama3.2        # provider-specific model name
  base_url: http://localhost:11434  # for ollama
```

### 4.4 Delivery Protocol (P3 — NEW)

```python
# daily_briefing/delivery/base.py
class DeliveryProtocol(ABC):
    name: str
    def send(self, message: str, config: DeliveryConfig) -> DeliveryResult: ...

@dataclass
class DeliveryResult:
    success: bool
    channel: str
    error: str | None = None
```

Concrete senders:

| Sender | Key | Config |
|--------|-----|--------|
| `stdout` | None | Zero-config, default |
| `ntfy` | `NTFY_TOPIC` | Public topic or self-hosted server |

Config in `brief.yaml` — der `delivery:` Block existiert heute als toter Code, bekommt jetzt einen Leser:
```yaml
delivery:
  - method: stdout    # always included as fallback
  - method: ntfy
    topic: my-briefing
    server: https://ntfy.sh  # optional, default
```

### 4.5 CLI Setup (`daily-briefing setup`)

```python
# daily-briefing setup
#  1. Creates brief.yaml from brief.example.yaml
#  2. Creates .env from .env.example
#  3. Interactive prompts for:
#     - Location(s) for weather
#     - Language (de/en)
#     - Ntfy topic (optional)
#     - LLM provider (optional)
```

The interactive mode uses Click's `click.prompt()` and `click.confirm()`. Non-interactive mode supported via `--config-only` (just copy templates, no prompts).

### 4.6 Doctor (`daily-briefing doctor`)

```
$ daily-briefing doctor

Daily Briefing — Config Health Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sources:
  weather   ✅ configured (Verden Aller, Rethem Aller)
  calendar  ⚠️  google-api-python-client not installed (pip install daily-briefing[calendar])
  github    ⚠️  gh CLI not authenticated
  bahn      ✅ configured
  reddit    ✅ configured (programming, de)
  news      ✅ configured (2 feeds)
  email     ⚠️  disabled in config

Summarizer: prompt-only (no LLM key needed)
Delivery:
  stdout    ✅
  ntfy      ⚠️  NTFY_TOPIC not set

── Dry-Run with configured sources ──
  weather   ✅ 18.5°C, Verden (Aller)
  bahn      ✅ 6 departures found
  reddit    ✅ 9 posts from 2 subreddits
  news      ✅ 6 headlines from 2 feeds
```

### 4.7 i18n / Locale (P4)

```
daily_briefing/summarizer/locales/
├── de.yaml    # German prompts
└── en.yaml    # English prompts (default)
```

Example `en.yaml`:
```yaml
system_instruction: >
  You are the Daily Briefing Bot. Summarize the following data into ONE
  morning message. The message should be informative, friendly, and concise
  — so the user catches everything important in 5 seconds.

  Priority: Weather > Calendar > GitHub > Transit > News > Reddit.
  Briefly mention failed sources (e.g. "Train data unavailable today").

format:
  header: "TODAY'S DATA"
  output: "OUTPUT FORMAT"
  max_chars: "Maximum {max_length} characters"
  tone: "Tone: {tone}"
  generate: "Generate the message NOW:"
```

---

## 5. File Changes Map

### New files to create

| File | Purpose |
|------|---------|
| `daily_briefing/summarizer/base.py` | SummarizerProtocol + result type |
| `daily_briefing/summarizer/providers/` | Provider implementations |
| `daily_briefing/summarizer/providers/__init__.py` | |
| `daily_briefing/summarizer/providers/prompt_only.py` | Default: just emit prompt |
| `daily_briefing/summarizer/providers/ollama.py` | Local LLM |
| `daily_briefing/summarizer/providers/openai_.py` | OpenAI |
| `daily_briefing/summarizer/providers/anthropic.py` | Anthropic |
| `daily_briefing/summarizer/locales/en.yaml` | English prompts |
| `daily_briefing/summarizer/locales/de.yaml` | German prompts |
| `daily_briefing/delivery/__init__.py` | |
| `daily_briefing/delivery/base.py` | DeliveryProtocol + result |
| `daily_briefing/delivery/senders/stdout.py` | stdout delivery |
| `daily_briefing/delivery/senders/ntfy.py` | ntfy.sh delivery |
| `daily_briefing/setup_wizard.py` | `daily-briefing setup` logic |
| `daily_briefing/doctor.py` | `daily-briefing doctor` logic |
| `brief.example.yaml` | Neutral template (no personal data) |
| `examples/daily-briefing-source-example/` | Example third-party source package |
| `examples/daily-briefing-source-example/pyproject.toml` | |
| `examples/daily-briefing-source-example/src/example_source.py` | |
| `examples/daily-briefing-source-example/README.md` | |
| `CONTRIBUTING.md` | Contribution guidelines |
| `daily_briefing/sources/weather.py` | (modified — remove hardcoded defaults) |
| `daily_briefing/sources/calendar.py` | (modified — configurable token path) |
| `docs/superpowers/guides/source-authoring.md` | How to write a third-party source |

### Existing files to modify

| File | Changes |
|------|---------|
| `daily_briefing/orchestrator.py` | Entry-point discovery instead of hardcoded registry |
| `daily_briefing/sources/weather.py` | Remove DEFAULT_LAT/LON/NAME — fail clearly if no config |
| `daily_briefing/sources/calendar.py` | Token path configurable, zoneinfo from config |
| `daily_briefing/sources/news.py` | Remove DEFAULT_FEEDS |
| `daily_briefing/sources/reddit.py` | Remove DEFAULT_SUBREDDITS |
| `daily_briefing/sources/bahn.py` | Remove DEPARTURE_STATION etc. defaults |
| `daily_briefing/sources/github.py` | (check for hardcoded defaults) |
| `daily_briefing/summarizer/prompts.py` | Add locale loading, lang parameter |
| `daily_briefing/cli.py` | console_scripts, setup, doctor, new flags |
| `daily_briefing/config.py` | Add delivery, summarizer, lang config types |
| `pyproject.toml` | entry-points, console_scripts, optional deps |
| `brief.yaml` → `brief.example.yaml` | Personal data removed, .gitignored |
| `.env.example` | Neutralized, no Frankfurter defaults |
| `.gitignore` | Add `brief.yaml`, `site-dist/` |
| `README.md` | Full rewrite, product-focused |
| `tests/` | Tests for new modules |
| `site/` | P10 changes |

---

## 6. Architecture Principles Applied

1. **"For others" means remove assumptions, not add features** — every source loses hardcoded personal defaults
2. **Interface over implementation** — SummarizerProtocol and DeliveryProtocol let any provider be swapped
3. **Fail gracefully** — missing credentials = skipped source, not crash
4. **Zero-key startup** — `prompt-only` summarizer + `stdout` delivery = nothing to configure
5. **Pluggable by design** — Entry-points mean a third party's package auto-registers
6. **YAGNI** — Only build what the North Star requires. Nice-to-haves wait.

---

## 7. Deferred / Future (after this work)

- Telegram delivery (needs async event loop, heavier)
- Email delivery (SMTP config complexity)
- Cache with TTL + retries (P7)
- Conditional/actionable-only sections (P7)
- Weekly variant with ETF/index summary (P8)
- Pre-commit hooks (low value early)
- Coverage gate (after CI is stable)

---

---

## 8. Variants (P8)

Variants change which sources run and which prompt template is used:

```yaml
# brief.yaml
variants:
  morning:
    sources: [weather, calendar, github, bahn, reddit, news]
    prompt_template: morning  # uses locales/{lang}/morning.yaml
  evening:
    sources: [weather, calendar, news, reddit]
    prompt_template: evening
  weekly:
    sources: [weather, calendar, github, news, reddit]
    prompt_template: weekly
```

CLI usage: `daily-briefing --variant evening`. Default variant: `morning`.

Each variant has its own prompt template in the locale files. The summarizer uses
the variant-specific prompt instead of the default morning prompt.

Variant-specific note: the `weekly` variant's ETF/index summary is **documented
as a placeholder** in the default `en/` locale prompts, but the actual
implementation (fetching real ETF data) is explicitly deferred — it requires a
third-party source package or a future addition.

---

## 9. Website / site/ Updates (P10)

The existing marketing page at `site/` needs truth-to-reality alignment:

### 9.1 Remove Hermes- and WhatsApp-Claims
- Hero label: `"Open-source · Hermes Agent Skill"` → `"Open-source · Self-hosted · Extensible"`
- Meta description: remove "WhatsApp message" — phrase as "delivered to your phone"
- How It Works step 3: remove "WhatsApp Delivers" / "Hermes cron sends" → "Pluggable Delivery (stdout, ntfy)"
- Footer: remove "Powered by Hermes Agent" → replace with "Works with Hermes Agent, among others"

### 9.2 Show Extensibility
- New section: "Plugin Architecture" with the entry-point code snippet
- Short code example showing `SourceProtocol` + entry-point registration
- Link to `source-authoring.md`

### 9.3 Claims Alignment
- News card: "deduplicated across sources" → only if actually implemented, otherwise soften
- Source list matches actual built-in sources (7 sources + note about third-party)

### 9.4 Demo Mockup
- Replace hardcoded Frankfurt/German text with neutral demo data
- Add DE/EN toggle showing same message in both languages
- Preview clearly labeled as "Preview"
- No live backend — static Vite site stays as-is

### 9.5 Verification
- Full-text search over `site/`: no "WhatsApp" or "Hermes" as operational requirement
- `npm run build` passes
- Every claim backed by shipped code

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Entry-point API changes between Python 3.11 and 3.12 | Breakage | Use `importlib.metadata.entry_points(group=...)` which is stable since 3.9 |
| ntfy server down | No push | stdout always delivers as fallback |
| ollama not installed | Summarizer error | Clear error message pointing to `ollama pull` |
| User has no .env | Crashes | Default to env var lookup with None defaults |
