# P1 — Remove Personal Defaults Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans.

**Goal:** Remove all hardcoded personal data from source modules so the tool is usable by a stranger. Every source reads exclusively from its config section and fails with a clear error if required config is missing.

**Architecture:** The SOURCE_REGISTRY and config flow stay unchanged for now. This plan only touches config defaults in source modules and config templates. Each source keeps its class/fetch structure intact — only the fallback defaults and env-var lookups change.

**Tech Stack:** Python 3.11, no new dependencies

---

### Task 1: Weather — remove DEFAULT_LAT/LON/NAME

**Files:**
- Modify: `daily_briefing/sources/weather.py:49-53` (remove default constants)
- Test: `tests/test_sources_weather.py`

**Changes:**
```python
# REMOVE these lines entirely:
DEFAULT_LAT = float(os.environ.get("WEATHER_LAT", "50.1109"))
DEFAULT_LON = float(os.environ.get("WEATHER_LON", "8.6821"))
DEFAULT_NAME = os.environ.get("WEATHER_NAME", "Frankfurt")
```

**In `fetch()`**, change the fallback path at line 67-70:
```python
# OLD:
if not locations:
    data = self._fetch_one(DEFAULT_LAT, DEFAULT_LON, DEFAULT_NAME)
    return SourceResult(name=self.name, priority=10, data=data)

# NEW:
if not locations:
    return SourceResult(
        name=self.name,
        priority=10,
        error="Weather not configured. Add locations to sources.weather.locations in brief.yaml",
    )
```

- [ ] **Step 1: Update existing test_single_location_fallback**

Change the test at tests/test_sources_weather.py:22-48 — it currently tests the env-var fallback. Change it to test the error case:

```python
@patch("daily_briefing.sources.weather.requests.get")
def test_missing_locations_returns_error(self, mock_get, source):
    """When no locations in config, returns clear error instead of defaults."""
    result = source.fetch({"sources": {"weather": {}}})
    assert result.is_success() is False
    assert "Weather not configured" in result.error
    mock_get.assert_not_called()  # Should not make any API call
```

- [ ] **Step 2: Run tests — verify old test fails, new test passes**

Run: `python -m pytest tests/test_sources_weather.py -v -x`
Expected: test_single_location_fallback FAILS (DEFAULT_LAT removed), test_missing_locations_returns_error PASSES

- [ ] **Step 3: Apply the source changes**

Remove DEFAULT_LAT/LON/NAME. Replace the fallback `if not locations:` block with the error return.

- [ ] **Step 4: Run tests to confirm**

Run: `python -m pytest tests/test_sources_weather.py -v -x`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add daily_briefing/sources/weather.py tests/test_sources_weather.py
git commit -m "fix(weather): remove hardcoded DEFAULT_LAT/LON/NAME, error on missing config"
```

---

### Task 2: News — remove DEFAULT_FEEDS

**Files:**
- Modify: `daily_briefing/sources/news.py:21-25` (remove default)

**Changes in `news.py`:**
```python
# REMOVE:
DEFAULT_FEEDS = os.environ.get(
    "NEWS_FEEDS",
    "https://www.heise.de/rss/heise-atom.xml,https://dev.to/feed",
)
```

Change the fallback in `fetch()`:
```python
# OLD:
feeds_raw = source_config.get("feeds", DEFAULT_FEEDS)

# NEW:
feeds_raw = source_config.get("feeds", None)
```

And before the feed loop, add an early return:
```python
if not feeds_raw:
    return SourceResult(
        name=self.name,
        priority=60,
        error="No news feeds configured. Add sources.news.feeds to brief.yaml",
    )
```

- [ ] **Step 1: Write the failing test**

```python
def test_missing_feeds_returns_error(source):
    result = source.fetch({"sources": {"news": {}}})
    assert result.is_success() is False
    assert "No news feeds configured" in result.error
```

- [ ] **Step 2: Verify test fails**

Run: `python -m pytest tests/test_sources_news.py -v -x`
Expected: test_missing_feeds_returns_error FAILS because DEFAULT_FEEDS still provides a value

- [ ] **Step 3: Implement — remove DEFAULT_FEEDS, add error for no feeds**

- [ ] **Step 4: Run tests — all pass**

Run: `python -m pytest tests/test_sources_news.py tests/test_sources_weather.py -v`
Expected: 6+4 = 10+ tests pass

- [ ] **Step 5: Commit**

```bash
git add daily_briefing/sources/news.py tests/test_sources_news.py
git commit -m "fix(news): remove hardcoded DEFAULT_FEEDS, error on missing feeds config"
```

---

### Task 3: Reddit — remove DEFAULT_SUBREDDITS

**Files:**
- Modify: `daily_briefing/sources/reddit.py:23` (remove default)

**Changes:**
```python
# REMOVE:
DEFAULT_SUBREDDITS = os.environ.get("REDDIT_SUBREDDITS", "programming,de")
```

Change fallback in `fetch()`:
```python
subreddits_raw = source_config.get("subreddits", None)
```

Add early return:
```python
if not subreddits_raw:
    return SourceResult(
        name=self.name,
        priority=50,
        error="No subreddits configured. Add sources.reddit.subreddits to brief.yaml",
    )
```

- [ ] **Step 1: Write the failing test for missing subreddits**

```python
def test_missing_subreddits_returns_error(source):
    result = source.fetch({"sources": {"reddit": {}}})
    assert result.is_success() is False
    assert "No subreddits configured" in result.error
```

- [ ] **Step 2: Verify test fails**

Run: `python -m pytest tests/test_sources_reddit.py -v -x` (create test if needed, or add to existing)
Expected: test fails because DEFAULT_SUBREDDITS still provides value

- [ ] **Step 3: Remove DEFAULT_SUBREDDITS, add error return**

- [ ] **Step 4: Run all source tests**

Run: `python -m pytest tests/ -v`
Expected: 46+ tests pass (old test count may adjust for removed/renamed tests)

- [ ] **Step 5: Commit**

```bash
git add daily_briefing/sources/reddit.py tests/
git commit -m "fix(reddit): remove hardcoded DEFAULT_SUBREDDITS, error on missing config"
```

---

### Task 4: Bahn — remove DEPARTURE_STATION/ARRIVAL_STATION/DEPARTURE_TIME/BAHN_MODE defaults

**Files:**
- Modify: `daily_briefing/sources/bahn.py:24-28` (remove env var defaults)

**Changes:**
```python
# REMOVE all four lines:
DEPARTURE_STATION = os.environ.get("BAHN_DEPARTURE_STATION", "8000105")
ARRIVAL_STATION = os.environ.get("BAHN_ARRIVAL_STATION", "")
DEPARTURE_TIME = os.environ.get("BAHN_TIME", "07:30")
BAHN_MODE = os.environ.get("BAHN_MODE", "depart")
```

Change fallback in `fetch()`:
```python
# OLD:
station_id = source_config.get("station", DEPARTURE_STATION)

# NEW:
station_id = source_config.get("station", None)
if not station_id:
    return SourceResult(
        name=self.name,
        priority=40,
        error="Bahn not configured. Add sources.bahn.station to brief.yaml",
    )
```

- [ ] **Step 1: Write test for missing station**

- [ ] **Step 2: Verify fails**

- [ ] **Step 3: Remove defaults, add error**

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add daily_briefing/sources/bahn.py tests/
git commit -m "fix(bahn): remove hardcoded station defaults, error on missing config"
```

---

### Task 5: Calendar — remove Hermes token path hardcoding

**Files:**
- Modify: `daily_briefing/sources/calendar.py:115-138` (_load_credentials method)

**Changes:**
Replace hardcoded `~/.hermes/google_token.json` with configurable path from source config:

```python
def _load_credentials(self, token_path: str | None = None):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if token_path is None:
        token_path = os.environ.get("GOOGLE_TOKEN_PATH", "~/.google_token.json")

    token_path = os.path.expanduser(token_path)

    if not os.path.exists(token_path):
        return None  # Not configured — not an error

    creds = Credentials.from_authorized_user_file(token_path)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds
```

Then in `fetch()`, handle `None` credentials gracefully:
```python
try:
    creds = self._load_credentials(config.get("sources", {}).get("calendar", {}).get("token_path"))
    if creds is None:
        return SourceResult(
            name=self.name,
            priority=20,
            error="Google Calendar not configured. Set token_path in sources.calendar or GOOGLE_TOKEN_PATH env var",
        )
    events = self._get_events(creds)
    ...
```

- [ ] **Step 1: Update tests for configurable token path**

- [ ] **Step 2: Implement configurable path + graceful None handling**

- [ ] **Step 3: Run tests**

- [ ] **Step 4: Commit**

```bash
git add daily_briefing/sources/calendar.py tests/
git commit -m "fix(calendar): make token path configurable, remove Hermes hardcode"
```

---

### Task 6: .gitignore brief.yaml + neutralize templates

**Files:**
- Modify: `.gitignore` (add brief.yaml entry)
- Create: `brief.example.yaml` (neutral template from existing brief.yaml)
- Modify: `.env.example` (neutralize defaults)
- Modify: `brief.yaml` → move to `.gitignore` but keep for local use

- [ ] **Step 1: Update .gitignore**

Add to `.gitignore`:
```
# Personal config — each user creates their own
brief.yaml
```

- [ ] **Step 2: Create brief.example.yaml**

Copy existing `brief.yaml` but:
- Replace location data with neutral placeholders
- Change all language to English
- Mark all optional sources as `enabled: false` or comment them
- Add `delivery:` block with stdout example
- Add `summarizer:` block with prompt-only example
- Add `output.lang: en` and `output.timezone: UTC`
- Add `variants:` example section
- Fill with explanatory comments

- [ ] **Step 3: Update .env.example**

- Replace Frankfurter BAHN defaults with empty/example values
- Remove WEATHER_LAT/LON/NAME entirely (locations come from brief.yaml)
- Add GOOGLE_TOKEN_PATH example
- Add NTFY_TOPIC example
- Add OLLAMA_BASE_URL and OLLAMA_MODEL example
- Add summaries of which config keys are optional
- Make clear that `.env` is only for secrets, brief.yaml is for config

- [ ] **Step 4: Run tests** — all should still pass (brief.yaml still exists locally)

- [ ] **Step 5: Commit**

```bash
git add .gitignore brief.example.yaml .env.example
git commit -m "chore: gitignore brief.yaml, add neutral brief.example.yaml, update .env.example"
```

---

### Task 7: Audit repo for remaining personal data

- [ ] **Step 1: Search for remaining personal data**

Run:
```bash
grep -rn "Frankfurt\|Verden\|Rethem\|kvnlnk\|kevinlingk" daily_briefing/ --include="*.py" --include="*.yaml" --include="*.yml"
grep -rn "hermes\|Hermes" daily_briefing/ --include="*.py" --include="*.yaml" --include="*.yml"
grep -rn "~/.hermes" daily_briefing/ --include="*.py"
```

- [ ] **Step 2: Remediate findings**

- Any text references to Frankfurt/Verden in comments → rewrite as generic examples
- Any Hermes path references → make configurable
- The "Hermes Agent" in User-Agent headers in news.py and reddit.py → make generic
- Update User-Agent: `DailyBriefing/1.0 (daily-briefing; +https://github.com/kvnlnk/daily-briefing)`

- [ ] **Step 3: Run full test suite**

- [ ] **Step 4: Commit**

```bash
git add ...  # affected files
git commit -m "chore: remove remaining personal data from source code and comments"
```

---

### Task 8: Final verification

- [ ] **Step 1: Full test suite**

```bash
cd /root/workspace/daily-briefing && python -m pytest tests/ -v
```
Expected: All tests pass, no regressions

- [ ] **Step 2: Clean install test**

```bash
python -m venv /tmp/test-p1
/tmp/test-p1/bin/pip install -e .
/tmp/test-p1/bin/python -m daily_briefing --source weather
```
Expected: Error about missing weather config (not a crash)

- [ ] **Step 3: Confirm brief.yaml still works locally**

```bash
python -m daily_briefing --source weather
```
Expected: Works as before (brief.yaml still exists, has locations)

- [ ] **Step 4: Push and finalize**

```bash
git log --oneline -5
```
