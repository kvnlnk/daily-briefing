"""Summarizer provider factory and registration.

New providers register via PROVIDERS dict.
Default provider is prompt-only (zero configuration).
"""

from __future__ import annotations

from typing import Any

from daily_briefing.summarizer.base import SummarizerProtocol, SummarizerResult
from daily_briefing.summarizer.providers.prompt_only import PromptOnlyProvider

# Registry of available providers. New providers register here.
PROVIDERS: dict[str, type[SummarizerProtocol]] = {
    "prompt-only": PromptOnlyProvider,
}

# Optional providers — try to import, silently skip if not installed
try:
    from daily_briefing.summarizer.providers.ollama_ import OllamaProvider  # noqa: F811

    PROVIDERS["ollama"] = OllamaProvider
except ImportError:
    pass

try:
    from daily_briefing.summarizer.providers.openai_ import OpenAIProvider  # noqa: F811

    PROVIDERS["openai"] = OpenAIProvider
except ImportError:
    pass

try:
    from daily_briefing.summarizer.providers.anthropic import AnthropicProvider  # noqa: F811

    PROVIDERS["anthropic"] = AnthropicProvider
except ImportError:
    pass


def get_summarizer(provider_name: str | None = None) -> SummarizerProtocol:
    """Get a summarizer provider by name.

    Args:
        provider_name: Name of the provider (e.g. 'prompt-only', 'ollama').
                       Defaults to 'prompt-only'.

    Returns:
        An instance of the requested provider.

    Raises:
        ValueError: If the provider name is unknown.
    """
    if provider_name is None:
        provider_name = "prompt-only"

    cls = PROVIDERS.get(provider_name)
    if cls is None:
        raise ValueError(
            f"Unknown summarizer provider: {provider_name}. "
            f"Available: {list(PROVIDERS.keys())}"
        )
    return cls()


def list_providers() -> list[str]:
    """Return list of available provider names."""
    return list(PROVIDERS.keys())
