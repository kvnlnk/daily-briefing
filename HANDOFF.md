# Daily Briefing — Handoff

## What was built

Daily Briefing was refactored from a personal tool to a standalone, extensible product. It's a CLI tool that fetches data from 7 built-in sources in parallel and summarizes everything into one concise message.

### Shipped Features
- **7 built-in sources**: Weather (Open-Meteo), Calendar (Google), GitHub, Bahn (DB API), Reddit (RSS), News (RSS), Email (IMAP)
- **Pluggable Source Architecture**: Third-party sources register via `pyproject.toml` entry points — no fork needed
- **Pluggable Summarizer Protocol**: `prompt-only` (default, zero-config), `ollama`, `openai`, `anthropic`
- **Pluggable Delivery Protocol**: `stdout` (default), `ntfy.sh` (push notifications)
- **i18n**: English (`en`) and German (`de`) via YAML locale files. Extensible — add `fr.yaml` to add French.
- **CLI with subcommands**: `daily-briefing` (run), `daily-briefing setup` (wizard), `daily-briefing doctor` (diagnostics)
- **Variants**: `morning`, `evening`, `weekly` — each with different source sets and prompt templates
- **Zero-key startup**: weather, news, Reddit work with zero API keys. Auth-requiring sources gracefully degrade with error messages.
- **Timezone-aware**: timezone config flows from `brief.yaml` through weather and calendar sources

### How to run locally
```bash
git clone https://github.com/kvnlnk/daily-briefing.git
cd daily-briefing
pip install -e .
daily-briefing setup
daily-briefing doctor
daily-briefing
```

### Test suite
103 tests — all passing. Run with `python -m pytest`.

### What's missing / next steps
- **Email source**: needs `imaplib` credentials configured
- **Calendar source**: requires `pip install 'daily-briefing[calendar]'` + OAuth setup
- **GitHub source**: requires `gh` CLI authenticated or `GITHUB_TOKEN` set
- **PyPI publish**: PyPI-ready but not published. Run `python -m build && twine upload dist/*` when ready
- **Additional delivery methods**: email, Telegram, SMS could be added via the DeliveryProtocol
- **Additional locales**: `fr.yaml`, `es.yaml`, `ja.yaml` can be added as copies of `en.yaml`
- **Automated CI**: GitHub Actions workflow for lint + test is prepared but needs configuring with secrets

### Required Secrets (never committed)
- `GITHUB_TOKEN` — for GitHub source (public repos work without, but rate limited)
- `EMAIL_USER` / `EMAIL_PASSWORD` — for Email source
- Google Calendar OAuth token (`~/.google_token.json`)
- `NTFY_TOPIC` — for ntfy push delivery
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — for LLM summarizers (optional)

These go in `.env` file (gitignored).

### Surprising discoveries
- Open-Meteo's free weather API is excellent and requires zero auth
- DB (Bahn) transport.rest API works without auth for schedule data
- Entry-point discovery via `importlib.metadata` is surprisingly clean — ~20 lines of code enables a full plugin system
- The locale YAML approach with `prompts` section for variants keeps complexity in data files, not code

### Architecture (in 30 seconds)
```
Sources (7 built-in + plugins via entry points)
  → Orchestrator (parallel fetch via ThreadPoolExecutor)
  → History (SQLite diff, optional)
  → build_prompt() (locale-aware, variant-aware)
  → Summarizer (prompt-only | ollama | openai | anthropic)
  → Delivery (stdout | ntfy)
```

### Claims audit results
- No "vibecoded" in any product-facing doc (only in gitignored internal plans)
- No WhatsApp mentions in product docs or code (only in gitignored internal plans)
- No "Hermes Agent required" claims
- README install instructions work for a stranger
- All doc claims backed by shipped code
- 103 tests passing
- `npm run build` passes for site/
