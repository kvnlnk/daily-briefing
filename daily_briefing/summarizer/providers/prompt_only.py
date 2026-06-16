"""Prompt-only summarizer — default provider, zero configuration needed.

Returns the raw prompt as-is, no LLM call. This is the default
provider and works without any API key or local model.
"""

from typing import Any

from daily_briefing.summarizer.base import SummarizerProtocol, SummarizerResult


class PromptOnlyProvider(SummarizerProtocol):
    """Returns the prompt unchanged — for piping into external LLMs."""

    name = "prompt-only"

    def summarize(self, prompt: str, **kwargs: Any) -> SummarizerResult:
        return SummarizerResult(
            text=prompt,
            provider=self.name,
            model="",
        )
