"""Protocol and result types for LLM summarization providers.

Each provider implements SummarizerProtocol.summarize().
Selection happens via brief.yaml summarizer.provider setting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SummarizerResult:
    """The result of one summarization attempt.

    On success: `text` contains the summarized message, `error` is None.
    On failure: `text` is empty, `error` contains a human-readable message.
    """

    text: str
    """The summarized message text (on success) or empty (on failure)."""

    provider: str
    """Machine-readable provider name (e.g. 'prompt-only', 'ollama')."""

    model: str = ""
    """Model name used (provider-specific, e.g. 'llama3.2', 'gpt-4o')."""

    error: str | None = None
    """Human-readable error message if summarization failed."""

    def is_success(self) -> bool:
        return self.error is None and bool(self.text)


class SummarizerProtocol(ABC):
    """Protocol that all summarization providers must implement.

    Each provider defines a class that inherits from this ABC and
    implements `summarize()`. The orchestrator calls it with a
    pre-built prompt string.
    """

    name: str = ""
    """Human-readable provider name."""

    @abstractmethod
    def summarize(self, prompt: str, **kwargs: Any) -> SummarizerResult:
        """Given a built prompt, return summarized text.

        Args:
            prompt: The pre-built prompt string from build_prompt().

        Returns:
            SummarizerResult with either text (on success) or error (on failure).
        """
        ...
