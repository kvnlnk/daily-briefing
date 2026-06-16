"""Ollama summarizer — calls a local LLM via Ollama API.

No API key needed — works with a local Ollama instance.
Configure via OLLAMA_BASE_URL and OLLAMA_MODEL env vars.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from daily_briefing.summarizer.base import SummarizerProtocol, SummarizerResult

OLLAMA_DEFAULT_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3.2"


class OllamaProvider(SummarizerProtocol):
    """Summarizes via a local Ollama model."""

    name = "ollama"

    def summarize(self, prompt: str, **kwargs: Any) -> SummarizerResult:
        base_url = os.environ.get("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)
        model = os.environ.get("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL)
        try:
            resp = requests.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "")
            return SummarizerResult(text=text.strip(), provider=self.name, model=model)
        except requests.RequestException as e:
            return SummarizerResult(
                text="",
                provider=self.name,
                model=model,
                error=f"Ollama error: {e}",
            )
