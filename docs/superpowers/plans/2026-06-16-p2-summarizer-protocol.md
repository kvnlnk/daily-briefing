# P2 — Summarizer Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Add pluggable LLM summarization so the tool is usable without Hermes Agent. Define SummarizerProtocol + concrete providers (prompt-only, ollama, openai, anthropic).

**Architecture:** Abstract base class in summarizer/base.py. Provider implementations in summarizer/providers/. Selection via brief.yaml summarizer.provider. Default: prompt-only (no API key needed).

**Tech Stack:** Python 3.11, httpx or requests (ollama/openai/anthropic), optional openai/anthropic SDKs

---

### Task 1: Create SummarizerProtocol base

**Files:**
- Create: `daily_briefing/summarizer/base.py`

```python
"""Protocol and result types for LLM summarization providers."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SummarizerResult:
    text: str
    provider: str
    model: str = ""
    error: str | None = None

    def is_success(self) -> bool:
        return self.error is None


class SummarizerProtocol(ABC):
    """Protocol that all summarization providers must implement."""

    name: str = ""

    @abstractmethod
    def summarize(self, prompt: str, **kwargs: Any) -> SummarizerResult:
        """Given a built prompt, return summarized text."""
        ...
```

- [ ] **Step 1: Write failing test for base types**

```python
from daily_briefing.summarizer.base import SummarizerResult, SummarizerProtocol

def test_summarizer_result_success():
    r = SummarizerResult(text="Hello", provider="test")
    assert r.is_success()
    assert r.text == "Hello"

def test_summarizer_result_error():
    r = SummarizerResult(text="", provider="test", error="Failed")
    assert not r.is_success()
```

- [ ] **Step 2: Implement base types**

- [ ] **Step 3: Run tests → pass**

- [ ] **Step 4: Commit**

---

### Task 2: Create prompt-only provider (default, zero-key)

**Files:**
- Create: `daily_briefing/summarizer/providers/__init__.py`
- Create: `daily_briefing/summarizer/providers/prompt_only.py`

```python
"""Default provider: just returns the prompt as-is (no LLM call)."""

from daily_briefing.summarizer.base import SummarizerProtocol, SummarizerResult
from typing import Any


class PromptOnlyProvider(SummarizerProtocol):
    name = "prompt-only"

    def summarize(self, prompt: str, **kwargs: Any) -> SummarizerResult:
        return SummarizerResult(
            text=prompt,
            provider=self.name,
            model="",
        )
```

- [ ] **Step 1: Write test**

```python
from daily_briefing.summarizer.providers.prompt_only import PromptOnlyProvider

def test_prompt_only_returns_prompt():
    p = PromptOnlyProvider()
    result = p.summarize("Hello world")
    assert result.text == "Hello world"
    assert result.provider == "prompt-only"
```

- [ ] **Step 2: Implement + pass**

- [ ] **Step 3: Commit**

---

### Task 3: Create Ollama provider

**Files:**
- Create: `daily_briefing/summarizer/providers/ollama_ provider.py`

```python
"""Ollama summarizer — calls a local LLM via Ollama API."""

import os
from typing import Any

import requests

from daily_briefing.summarizer.base import SummarizerProtocol, SummarizerResult


OLLAMA_DEFAULT_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3.2"


class OllamaProvider(SummarizerProtocol):
    name = "ollama"

    def summarize(self, prompt: str, **kwargs: Any) -> SummarizerResult:
        base_url = os.environ.get("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)
        model = os.environ.get("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL)
        try:
            resp = requests.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "")
            return SummarizerResult(text=text.strip(), provider=self.name, model=model)
        except requests.RequestException as e:
            return SummarizerResult(
                text="", provider=self.name, model=model, error=f"Ollama error: {e}"
            )
```

- [ ] **Step 1: Write test (mock)**

```python
from unittest.mock import patch
from daily_briefing.summarizer.providers.ollama_ import OllamaProvider

@patch("daily_briefing.summarizer.providers.ollama_.requests.post")
def test_ollama_summarize(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"response": "Summary text"}
    p = OllamaProvider()
    result = p.summarize("My prompt")
    assert result.text == "Summary text"
    assert result.provider == "ollama"
```

- [ ] **Step 2: Implement**

- [ ] **Step 3: Test passes**

- [ ] **Step 4: Commit**

---

### Task 4: Create OpenAI and Anthropic providers (stubs that return clear "not configured" errors)

**Files:**
- Create: `daily_briefing/summarizer/providers/openai_.py`
- Create: `daily_briefing/summarizer/providers/anthropic.py`

Both try to import their SDK, check for API key, return error if missing.
Keep minimal — core functionality, no streaming, no fancy params.

- [ ] **Step 1-3: Implement both + tests**

- [ ] **Step 4: Commit**

---

### Task 5: Create SummarizerFactory for provider selection

**Files:**
- Modify: `daily_briefing/summarizer/__init__.py`

```python
"""Summarizer provider factory."""

from daily_briefing.summarizer.base import SummarizerProtocol, SummarizerResult
from daily_briefing.summarizer.providers.prompt_only import PromptOnlyProvider
from daily_briefing.config import BriefingConfig
from typing import Any


PROVIDERS: dict[str, type[SummarizerProtocol]] = {
    "prompt-only": PromptOnlyProvider,
}

try:
    from daily_briefing.summarizer.providers.ollama_ import OllamaProvider
    PROVIDERS["ollama"] = OllamaProvider
except ImportError:
    pass

try:
    from daily_briefing.summarizer.providers.openai_ import OpenAIProvider
    PROVIDERS["openai"] = OpenAIProvider
except ImportError:
    pass

try:
    from daily_briefing.summarizer.providers.anthropic import AnthropicProvider
    PROVIDERS["anthropic"] = AnthropicProvider
except ImportError:
    pass


def get_summarizer(provider_name: str | None = None) -> SummarizerProtocol:
    if provider_name is None:
        provider_name = "prompt-only"
    cls = PROVIDERS.get(provider_name)
    if cls is None:
        raise ValueError(f"Unknown summarizer provider: {provider_name}. Available: {list(PROVIDERS.keys())}")
    return cls()


def summarize(prompt: str, config: BriefingConfig | None = None, **kwargs: Any) -> SummarizerResult:
    provider_name = kwargs.pop("provider", "prompt-only")
    summarizer = get_summarizer(provider_name)
    return summarizer.summarize(prompt, **kwargs)
```

- [ ] **Step 1: Write tests for factory**

- [ ] **Step 2: Implement**

- [ ] **Step 3: All tests pass**

- [ ] **Step 4: Commit**

---

### Task 6: Wire summarizer into CLI main

**Files:**
- Modify: `daily_briefing/cli.py`

After building prompt, call summarizer:
```python
from daily_briefing.summarizer import summarize as call_summarizer

# After prompt building:
provider = configuration.raw.get("summarizer", {}).get("provider", "prompt-only")
summary = call_summarizer(prompt, provider=provider)

if summary.is_success():
    click.echo(summary.text)
else:
    click.echo(f"Summarizer error ({provider}): {summary.error}", err=True)
    click.echo(prompt)  # Fallback: print the raw prompt
```

- [ ] **Step 1: Update tests for CLI**

- [ ] **Step 2: Wire summarizer**

- [ ] **Step 3: Test: `python -m daily_briefing` prints prompt (default = prompt-only)**

- [ ] **Step 4: Test: --dry-run flag (fetch but don't summarize)**

- [ ] **Step 5: Commit**
