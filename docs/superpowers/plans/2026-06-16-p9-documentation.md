# P9 — Documentation Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Rewrite README from "personal tool" to product. Add CONTRIBUTING, source-authoring guide, align with final codebase state.

---

### Task 1: Rewrite README.md

Product-focused structure:
- **Headline + badge row** (PyPI-prep, Python version, CI badge placeholder)
- **Quick start** (pip install from GitHub → setup → run)
- **Why Daily Briefing** (value prop: unified morning info, pluggable, self-hosted)
- **Data Sources** (table: source name, what it does, requires auth?)
- **Architecture overview** (brief, with link to ARCHITECTURE.md)
- **Usage** (subcommands with examples)
- **Configuration** (brief.yaml + .env)
- **Extending** (how to write a source, link to source-authoring guide)
- **Operating modes** (Hermes integration = ONE mode of many, documented briefly)
- **License** + footer link

Remove all "vibecoded", "Hermes Agent built this", WhatsApp-only claims.

- [ ] Step 1: Write new README.md
- [ ] Step 2: Review for claims accuracy
- [ ] Step 3: Commit

---

### Task 2: Create CONTRIBUTING.md

- Code style (ruff, line-length 100)
- Conventional commits
- TDD expectations
- How to add a source
- How to run tests
- How to run CI locally

- [ ] Step 1-3: Write + commit

---

### Task 3: Create source-authoring guide

**Files:**
- `docs/source-authoring.md`

Full guide for third-party developers:
1. Implement `SourceProtocol`
2. Handle errors gracefully
3. Read config from the `config` dict
4. Register entry point in pyproject.toml
5. Make it pip-installable
6. Test it
7. Example: Quote-of-the-Day source walkthrough

- [ ] Step 1-3: Write + commit

---

### Task 4: Update ARCHITECTURE.md

- Remove WhatsApp references
- Add Entry-Point Discovery flow
- Add SummarizerProtocol
- Add DeliveryProtocol
- Add i18n / locale system
- Reference design decisions from the spec doc

- [ ] Step 1-3: Update + commit

---

### Task 5: Final doc audit

- [ ] No "vibecoded" anywhere in the repo
- [ ] No WhatsApp as only delivery option
- [ ] No Hermes-as-requirement claims
- [ ] README install instructions work for a stranger
- [ ] All doc claims backed by shipped code
