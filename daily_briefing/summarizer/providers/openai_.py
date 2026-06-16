"""OpenAI summarizer — calls OpenAI chat completions API.

Requires OPENAI_API_KEY env var.
"""

from __future__ import annotations

import os
from typing import Any

from daily_briefing.summarizer.base import SummarizerProtocol, SummarizerResult

OPENAI_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(SummarizerProtocol):
    """Summarizes via OpenAI's chat completions API."""

    name = "openai"

    def summarize(self, prompt: str, **kwargs: Any) -> SummarizerResult:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return SummarizerResult(
                text="",
                provider=self.name,
                error="OpenAI not configured. Set OPENAI_API_KEY env var.",
            )

        model = os.environ.get("OPENAI_MODEL", OPENAI_DEFAULT_MODEL)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            text = response.choices[0].message.content or ""
            return SummarizerResult(text=text.strip(), provider=self.name, model=model)
        except Exception as e:
            return SummarizerResult(
                text="",
                provider=self.name,
                model=model,
                error=f"OpenAI error: {e}",
            )
