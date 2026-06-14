# Implementation Plan: Daily Briefing

## Overview

Build a modular morning briefing engine — 7 independent data sources fetched in
parallel, aggregated into a single LLM-friendly prompt, formatted as WhatsApp
text. Each source is a standalone module; adding a new source requires one new
file and one config line.

## Architecture Decisions

- See `ARCHITECTURE.md` for full rationale
- Sources = independent Python modules with uniform `fetch()` interface
- Orchestrator uses `ThreadPoolExecutor` for parallel I/O
- SQLite for yesterday-vs-today comparison
- LLM prompt assembly is the final output step (text only, no delivery logic)

---

## Task List

### Phase 1: Foundation

**Checkpoint goal:** Running skeleton with one working source.

#### Task 1: Source base class + config loader
**Description:** Define `SourceResult` dataclass, `SourceProtocol` ABC, and YAML config loader.
**Acceptance criteria:**
- [ ] `SourceResult` has fields: `name`, `priority`, `data`, `error`
- [ ] `SourceProtocol` defines `fetch(config) -> SourceResult` abstract method
- [ ] `load_config()` parses `brief.yaml` into `Config` dataclass
**Verification:** `python -c "from daily_briefing.sources.base import SourceResult, SourceProtocol; print('OK')"`
**Dependencies:** None
**Files:** `daily_briefing/sources/base.py`, `daily_briefing/config.py`
**Estimated scope:** S (2 files)

#### Task 2: Weather source (Open-Meteo)
**Description:** Fetch current conditions + forecast from free Open-Meteo API.
**Acceptance criteria:**
- [ ] `fetch()` returns temperature, condition, wind, precipitation for configured lat/lon
- [ ] Standalone test: `python -m daily_briefing --source weather` prints JSON
- [ ] Handles API errors gracefully (returns `SourceResult` with `error` field)
**Verification:** `python -m daily_briefing --source weather` outputs valid weather data
**Dependencies:** Task 1
**Files:** `daily_briefing/sources/weather.py`
**Estimated scope:** S (1 file)

---

### Checkpoint: Foundation

- [ ] Base class imports without errors
- [ ] `python -m daily_briefing --source weather` produces output
- [ ] Git commit: 2 commits (base class, weather)

---

### Phase 2: Core Sources

**Checkpoint goal:** All 7 sources independently functional.

#### Task 3: GitHub source
**Description:** Fetch notifications + open PRs from GitHub REST API using `GITHUB_TOKEN` env var.
**Acceptance criteria:**
- [ ] Returns: unread notification count, 3 most recent PRs with title+status
- [ ] Standalone test works
- [ ] Error handling for missing token, rate limit, network failure
**Dependencies:** Task 1
**Files:** `daily_briefing/sources/github.py`
**Estimated scope:** S (1 file)

#### Task 4: Calendar source
**Description:** Fetch today's events from Google Calendar via `gws` CLI (user already authenticated).
**Acceptance criteria:**
- [ ] Calls `gws calendar list --date today` via subprocess
- [ ] Parses output into list of {time, title, location}
- [ ] Returns empty list (not error) if no events
- [ ] Handles `gws` not installed gracefully
**Dependencies:** Task 1
**Files:** `daily_briefing/sources/calendar.py`
**Estimated scope:** S (1 file)

#### Task 5: Bahn source (DB Fahrplan)
**Description:** Fetch scheduled departure/arrival for configured station pair via DB Fahrplan API.
**Acceptance criteria:**
- [ ] Returns: configured route, next departure time, delay (if available), platform
- [ ] Standalone test works
- [ ] Handles station not found, API unreachable
**Dependencies:** Task 1
**Files:** `daily_briefing/sources/bahn.py`
**Estimated scope:** S (1 file)

#### Task 6: Reddit source
**Description:** Fetch top posts from configured subreddits via RSS feeds.
**Acceptance criteria:**
- [ ] For each subreddit: top 3 posts with title + score
- [ ] Uses Reddit RSS (no auth needed): `reddit.com/r/{sub}/top/.rss`
- [ ] Standalone test works
**Dependencies:** Task 1
**Files:** `daily_briefing/sources/reddit.py`
**Estimated scope:** S (1 file)

#### Task 7: News source
**Description:** Fetch latest headlines from configured RSS feeds.
**Acceptance criteria:**
- [ ] Parses each RSS/Atom feed → 3 most recent items per feed
- [ ] Deduplicates by title (same story across feeds)
- [ ] Standalone test works
**Dependencies:** Task 1
**Files:** `daily_briefing/sources/news.py`
**Estimated scope:** S (1 file)

#### Task 8: Email source
**Description:** Fetch unread mail count + subjects via IMAP.
**Acceptance criteria:**
- [ ] Returns: unread count, subject lines of 5 most recent unread
- [ ] Disabled by default in `brief.yaml` (requires IMAP creds)
- [ ] Handles auth failure gracefully
**Dependencies:** Task 1
**Files:** `daily_briefing/sources/email.py`
**Estimated scope:** S (1 file)

---

### Checkpoint: Core Sources

- [ ] All 7 sources pass standalone test
- [ ] Each handles its error path (missing token, API down, no data)
- [ ] Git: 7 commits (one per source)

---

### Phase 3: Orchestration & Storage

**Checkpoint goal:** Parallel fetch, storage, and prompt assembly working end-to-end.

#### Task 9: Orchestrator
**Description:** Parallel fetch all enabled sources, ordered by priority.
**Acceptance criteria:**
- [ ] Reads `brief.yaml`, filters to `enabled: true`, sorts by `priority`
- [ ] `ThreadPoolExecutor` fetches all sources in parallel
- [ ] Returns `List[SourceResult]` — failures included, not blocking
- [ ] `python -m daily_briefing` prints all results
**Dependencies:** Tasks 1-8
**Files:** `daily_briefing/orchestrator.py`, `daily_briefing/cli.py` (stub)
**Estimated scope:** M (2 files)

#### Task 10: Storage / History
**Description:** SQLite storage for yesterday-vs-today comparison.
**Acceptance criteria:**
- [ ] Schema: `briefings(id INTEGER PRIMARY KEY, date TEXT, source_name TEXT, data_json TEXT, created_at TEXT)`
- [ ] `save(results)` writes today's results
- [ ] `load(date)` reads results for a given date
- [ ] `diff(today, yesterday)` returns comparison dict for LLM
**Dependencies:** Task 9 (needs SourceResult format)
**Files:** `daily_briefing/storage/history.py`, `daily_briefing/storage/schema.sql`
**Estimated scope:** M (2 files)

#### Task 11: Summarizer
**Description:** Build LLM prompt from source results + yesterday comparison.
**Acceptance criteria:**
- [ ] `build_prompt(results, yesterday_diff, config)` returns structured text
- [ ] Prompt prioritizes: weather > calendar > github > bahn > news > reddit
- [ ] Output template respects `max_length`, `emoji`, `tone` from config
- [ ] `format_for_whatsapp(text)` ensures ≤800 chars, line breaks, emoji prefix
**Dependencies:** Tasks 9, 10
**Files:** `daily_briefing/summarizer/prompts.py`, `daily_briefing/summarizer/format.py`
**Estimated scope:** M (2 files)

---

### Checkpoint: Orchestration

- [ ] `python -m daily_briefing` runs all enabled sources in parallel
- [ ] Results saved to SQLite
- [ ] Yesterday comparison works
- [ ] Prompt text generated and printed

---

### Phase 4: Integration & Polish

**Checkpoint goal:** Complete, documented, deployable via Hermes cron.

#### Task 12: CLI entry point
**Description:** Full `python -m daily_briefing` with argparse.
**Acceptance criteria:**
- [ ] `--source weather` runs single source (for testing)
- [ ] `--verbose` prints raw results before summarization
- [ ] `--config path/to/brief.yaml` overrides default
- [ ] `--json` outputs raw JSON instead of formatted text
- [ ] `python -m daily_briefing` (no args) runs full pipeline
**Dependencies:** Tasks 9-11
**Files:** `daily_briefing/cli.py`, `daily_briefing/__main__.py`
**Estimated scope:** M (2 files, 100 lines)

#### Task 13: Hermes SKILL.md
**Description:** Create Hermes Skill so cron can run the briefing automatically.
**Acceptance criteria:**
- [ ] SKILL.md with YAML frontmatter (name, description, trigger)
- [ ] Instructions: run orchestrator → summarizer → deliver via WhatsApp
- [ ] Compatible with `hermes cron create --skill daily-briefing`
**Dependencies:** Task 12
**Files:** `SKILL.md` (in repo root)
**Estimated scope:** XS (1 file)

#### Task 14: Documentation
**Description:** README.md, HANDOFF.md, brief.yaml inline comments.
**Acceptance criteria:**
- [ ] README: what it does, how to install `pip install -e .`, how to configure
- [ ] HANDOFF: what's built, what's missing, required secrets, next steps
- [ ] All .env.example entries have clear comments
**Dependencies:** Task 13
**Files:** `README.md`, `HANDOFF.md`
**Estimated scope:** S (2 files)

---

### Checkpoint: Complete

- [ ] `python -m daily_briefing` end-to-end works
- [ ] Hermes SKILL.md loadable via `hermes skill load daily-briefing`
- [ ] README complete
- [ ] Final git push to `kvnlnk/daily-briefing`

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| DB Fahrplan API changes | Low — single source | Source fails gracefully, rest of briefing intact |
| Reddit RSS rate-limits | Low | `rss_bridge` or `teddit` as fallback |
| Google Calendar gws CLI breaks | Medium — daily dependency | Fallback to manual `gws auth login`; documented in HANDOFF |
| LLM summarization quality varies | Medium | Prompt template fine-tuned; human can tweak `summarizer/prompts.py` |

## Open Questions

- *None* — all decisions made during Phase 1 idea-selection and ARCHITECTURE.md
