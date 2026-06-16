"""Anthropic summarizer — calls Claude via Anthropic API.

Requires ANTHROPIC_API_KEY env var.
"""

from __future__ import annotations

import os
from typing import Any

from daily_briefing.summarizer.base import SummarizerProtocol, SummarizerResult

ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AnthropicProvider(SummarizerProtocol):
    """Summarizes via Anthropic's Claude API."""

    name = "anthropic"

    def summarize(self, prompt: str, **kwargs: Any) -> SummarizerResult:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return SummarizerResult(
                text="",
                provider=self.name,
                error="Anthropic not configured. Set ANTHROPIC_API_KEY env var.",
            )

        model = os.environ.get("ANTHROPIC_MODEL", ANTHROPIC_DEFAULT_MODEL)
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text if response.content else ""
            return SummarizerResult(text=text.strip(), provider=self.name, model=model)
        except Exception as e:
            return SummarizerResult(
                text="",
                provider=self.name,
                model=model,
                error=f"Anthropic error: {e}",
            )
