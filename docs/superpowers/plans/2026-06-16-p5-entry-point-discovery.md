# P5 — Entry-Point Plugin Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Replace hardcoded SOURCE_REGISTRY in orchestrator.py with setuptools entry-point discovery, so third-party source packages auto-register without forking the core.

**Architecture:** importlib.metadata.entry_points(group="daily_briefing.sources") at import time. Built-in sources register via the same mechanism in pyproject.toml. Hardcoded SOURCE_REGISTRY becomes a fallback for one release, then removed.

**Tech Stack:** Python 3.11 stdlib (importlib.metadata)

---

### Task 1: Add entry points to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

Add:
```toml
[project.entry-points."daily_briefing.sources"]
weather = "daily_briefing.sources.weather:WeatherSource"
github = "daily_briefing.sources.github:GitHubSource"
calendar = "daily_briefing.sources.calendar:CalendarSource"
bahn = "daily_briefing.sources.bahn:BahnSource"
reddit = "daily_briefing.sources.reddit:RedditSource"
news = "daily_briefing.sources.news:NewsSource"
email = "daily_briefing.sources.email:EmailSource"
```

- [ ] **Step 1: Add entry-point section to pyproject.toml**

- [ ] **Step 2: Verify entry points are discoverable**

```bash
cd /root/workspace/daily-briefing && pip install -e . && python -c "
import importlib.metadata
eps = importlib.metadata.entry_points(group='daily_briefing.sources')
for ep in eps:
    print(f'{ep.name} -> {ep.value}')
"
```
Expected: 7 entry points listed

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: register built-in sources via setuptools entry points"
```

---

### Task 2: Add discover_sources() to orchestrator

**Files:**
- Modify: `daily_briefing/orchestrator.py`
- Test: `tests/test_orchestrator.py`

**Implementation:**

```python
import importlib.metadata

def discover_sources() -> dict[str, importlib.metadata.EntryPoint]:
    """Discover all installed daily_briefing.sources entry points."""
    eps_by_name: dict[str, importlib.metadata.EntryPoint] = {}
    for ep in importlib.metadata.entry_points(group="daily_briefing.sources"):
        eps_by_name[ep.name] = ep
    return eps_by_name
```

Modify `_fetch_one` to try entry points first, fall back to SOURCE_REGISTRY:

```python
def _fetch_one(source_name: str, raw_config: dict[str, Any]) -> SourceResult:
    # Try entry points first (new discovery mechanism)
    if source_name in _ENTRY_POINTS:
        try:
            cls = _ENTRY_POINTS[source_name].load()
            source = cls()
            return source.fetch(raw_config)
        except Exception as e:
            return SourceResult(
                name=source_name,
                priority=99,
                error=f"Error loading '{source_name}' entry point: {e}",
            )

    # Fall back to hardcoded registry (deprecated)
    if source_name in SOURCE_REGISTRY:
        module_path, class_name = SOURCE_REGISTRY[source_name]
        try:
            module = importlib.import_module(module_path)
            source_class = getattr(module, class_name)
            source = source_class()
            return source.fetch(raw_config)
        except ImportError as e:
            return SourceResult(
                name=source_name,
                priority=99,
                error=f"Cannot import {module_path}: {e}",
            )
        ...

    return SourceResult(name=source_name, priority=99, error=f"Unknown source '{source_name}'")
```

Initialize at module level:
```python
_ENTRY_POINTS: dict[str, importlib.metadata.EntryPoint] = discover_sources()
```

- [ ] **Step 1: Write the failing test**

```python
def test_discover_sources_finds_builtin():
    from daily_briefing.orchestrator import discover_sources
    eps = discover_sources()
    assert "weather" in eps
    assert "github" in eps
    assert len(eps) >= 7

def test_entry_point_weather_loads_and_fetches():
    from daily_briefing.orchestrator import discover_sources
    eps = discover_sources()
    weather_ep = eps["weather"]
    cls = weather_ep.load()
    source = cls()
    assert source.name == "weather"
```

- [ ] **Step 2: Verify tests fail**

```python -m pytest tests/test_orchestrator.py -v -x```

- [ ] **Step 3: Implement discover_sources() + modify _fetch_one**

- [ ] **Step 4: Run all tests**

```python -m pytest tests/ -v```
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add daily_briefing/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: discover sources via entry points, fallback to hardcoded registry"
```

---

### Task 3: Add --list-sources CLI flag

**Files:**
- Modify: `daily_briefing/cli.py`

Add flag:
```python
@click.option("--list-sources", is_flag=True, help="List all installed data sources")
```

In main:
```python
if list_sources:
    from daily_briefing.orchestrator import discover_sources, SOURCE_REGISTRY
    eps = discover_sources()
    click.echo("Installed sources:")
    for name in sorted(eps.keys()):
        ep = eps[name]
        try:
            cls = ep.load()
            src = cls()
            priority = getattr(src, 'priority', 99)
            click.echo(f"  {name:15} priority={priority}")
        except Exception:
            click.echo(f"  {name:15} (failed to load)")
    return
```

- [ ] **Step 1: Write test for --list-sources**

```python
from click.testing import CliRunner
from daily_briefing.cli import main

def test_list_sources():
    runner = CliRunner()
    result = runner.invoke(main, ["--list-sources"])
    assert result.exit_code == 0
    assert "weather" in result.output
    assert "github" in result.output
```

- [ ] **Step 2: Implement --list-sources flag**

- [ ] **Step 3: Run tests**

- [ ] **Step 4: Commit**

```bash
git add daily_briefing/cli.py tests/
git commit -m "feat(cli): add --list-sources flag to enumerate installed sources"
```

---

### Task 4: Create example third-party source package

**Files:**
- Create: `examples/daily-briefing-source-example/`
- Create: `examples/daily-briefing-source-example/pyproject.toml`
- Create: `examples/daily-briefing-source-example/src/daily_briefing_source_example/__init__.py`
- Create: `examples/daily-briefing-source-example/src/daily_briefing_source_example/source.py`
- Create: `examples/daily-briefing-source-example/README.md`
- Create: `examples/daily-briefing-source-example/tests/test_source.py`

- [ ] **Step 1: Create package structure**

- [ ] **Step 2: Implement example source** (e.g., "Quote of the Day" from a free API)

- [ ] **Step 3: Write pyproject.toml with entry point**

```toml
[project.entry-points."daily_briefing.sources"]
quote = "daily_briefing_source_example.source:QuoteSource"
```

- [ ] **Step 4: Verify it can be pip-installed and auto-discovered**

```bash
cd examples/daily-briefing-source-example && pip install -e .
cd /root/workspace/daily-briefing && python -c "
from daily_briefing.orchestrator import discover_sources
eps = discover_sources()
print('quote' in eps)  # True
"
```

- [ ] **Step 5: Commit**

```bash
git add examples/
git commit -m "feat: add example third-party source package with entry-point discovery"
```

---

### Task 5: Verify acceptance criteria

- [ ] `daily-briefing --list-sources` shows all 7 built-in sources
- [ ] Installing example package adds "quote" to the list without modifying core
- [ ] All tests pass
- [ ] pip install from scratch works
