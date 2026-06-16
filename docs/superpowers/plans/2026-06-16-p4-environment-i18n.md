# P4 — Environment Assumptions + i18n Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Remove language/timezone assumptions, add i18n to prompts, ensure zero-key startup works (auth-requiring sources gracefully skip, free sources produce output).

---

### Task 1: Create locale YAML files

- [ ] Create `daily_briefing/summarizer/locales/__init__.py`
- [ ] Create `daily_briefing/summarizer/locales/en.yaml`
- [ ] Create `daily_briefing/summarizer/locales/de.yaml`

**Locale format:**
```yaml
# en.yaml
system_instruction: >
  You are the Daily Briefing Bot. Summarize the following data into ONE
  concise message. The message should be informative, friendly, and to the
  point — so the user catches everything important in 5 seconds.

format:
  header: "TODAY'S DATA"
  output: "OUTPUT FORMAT"
  max_chars: "Maximum {max_length} characters"
  tone: "Tone: {tone}"
  structure: "Structure: Weather → Calendar → GitHub → Transit → News → Reddit"
  generate: "Generate the message NOW:"
  yesterday_comparison: "COMPARISON WITH YESTERDAY:"
  no_data: "Not available"
```

- [ ] Step 1-2: Create both locale files

- [ ] Step 3: Write test that loads locale and returns expected keys

```python
def test_en_locale_has_required_keys():
    from daily_briefing.summarizer.locales import load_locale
    loc = load_locale("en")
    assert "system_instruction" in loc
    assert "format" in loc
    assert "generate" in loc["format"]
```

- [ ] Step 4: Commit

---

### Task 2: Update prompts.py to use locale + lang config

**Files:**
- Modify: `daily_briefing/summarizer/prompts.py`
- Modify: `daily_briefing/summarizer/locales/__init__.py` → locale loader

**Locale loader:**
```python
import os, yaml
_LOCALE_DIR = os.path.dirname(__file__)
_CACHE: dict[str, dict] = {}

def load_locale(lang: str = "en") -> dict:
    if lang not in _CACHE:
        path = os.path.join(_LOCALE_DIR, f"{lang}.yaml")
        if not os.path.exists(path):
            path = os.path.join(_LOCALE_DIR, "en.yaml")  # fallback
        with open(path) as f:
            _CACHE[lang] = yaml.safe_load(f)
    return _CACHE[lang]
```

**Update build_prompt signature:**
```python
def build_prompt(
    results: list[SourceResult],
    yesterday_diff: dict[str, Any] | None = None,
    config: OutputConfig | None = None,
    lang: str = "en",
    variant: str = "morning",
) -> str:
```

Use locale strings instead of hardcoded German text.

- [ ] Step 1: Write failing test for locale-aware prompt

- [ ] Step 2: Implement locale loader + update build_prompt

- [ ] Step 3: Test: prompt in en vs de differs

- [ ] Step 4: Commit

---

### Task 3: Thread timezone from config through all sources

**Files:**
- Modify: `daily_briefing/sources/weather.py` (use config timezone for API call)
- Modify: `daily_briefing/sources/calendar.py` (use config timezone for date boundary)
- Modify: `daily_briefing/orchestrator.py` (pass config down)
- Test: verify timezone is used

**In orchestrator:** pass `config.raw.get("output", {}).get("timezone", "UTC")` to each source's fetch.
**In sources:** each source reads `config.get("output", {}).get("timezone", "UTC")` if they need timezone data.

**Calendar source**: currently hardcodes TZ_BERLIN. Replace with:
```python
tz_name = config.get("output", {}).get("timezone", "UTC")
tz = ZoneInfo(tz_name)
```

**Weather source**: currently hardcodes `"timezone": "Europe/Berlin"` in API params. Replace with config timezone.

- [ ] Step 1: Test that calendar uses config timezone instead of hardcoded

- [ ] Step 2: Pass timezone through orchestrator

- [ ] Step 3: Update weather + calendar to use config timezone

- [ ] Step 4: Run all tests

- [ ] Step 5: Commit

---

### Task 4: Zero-key graceful degradation

**Files:**
- Modify: all sources to check credentials before making network calls
- Test: verify that with empty config, auth-free sources work

**What "zero-key" means:**
- Weather → works (no key needed, just needs locations in config)
- News → works (if feeds configured)
- Reddit → works (if subreddits configured)
- Calendar → error: "not configured" (returns error result, doesn't crash)
- GitHub → error: "gh CLI not authenticated"
- Bahn → works (if station configured)
- Email → error: "not configured" (already handled)

**Verify in `daily-briefing doctor` and `daily-briefing`** that failed sources produce SourceResult with error, not exceptions.

- [ ] Step 1: Audit all sources for crash-vs-error handling

- [ ] Step 2: Fix any source that raises instead of returning SourceResult error

- [ ] Step 3: Write integration test:

```python
def test_zero_key_run_does_not_crash():
    """With empty config, at least weather/reddit/news produce results."""
    cfg = ...  # config with no creds, bare minimum
    results = fetch_all(cfg)
    # Some should be errors (calendar, github, email)
    # Some should be successes (weather/locations, news/feeds, reddit/subreddits)
    # but NONE should raise exceptions
    errors = [r for r in results if not r.is_success()]
    successes = [r for r in results if r.is_success()]
    total = len(results)
    assert len(results) == total  # all returned, no crashes
```

- [ ] Step 4: Commit
