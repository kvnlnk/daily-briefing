"""Base types and protocol for all data sources.

Every source module implements SourceProtocol.fetch() → SourceResult.
This uniform interface means the orchestrator can treat all sources identically
— zero coupling between source modules.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceResult:
    """The result of one source's fetch operation.

    On success: `data` contains the parsed result (dict), `error` is None.
    On failure: `data` is None, `error` contains a human-readable message.
    This dual-result pattern lets the orchestrator collect partial failures
    and still produce a useful briefing from the remaining sources.
    """

    name: str
    """Machine-readable source name (e.g. 'weather', 'github')."""

    priority: int
    """Display priority — lower numbers appear first in the briefing."""

    data: dict[str, Any] | None = None
    """The parsed result from the source. Schema varies per source."""

    error: str | None = None
    """Human-readable error message if the source failed."""

    def is_success(self) -> bool:
        return self.error is None and self.data is not None


class SourceProtocol(ABC):
    """Protocol that all data sources must implement.

    Each source module defines a class that inherits from this ABC and
    implements `fetch()`. The orchestrator calls `fetch(config)` once per
    source with the loaded YAML config dict.

    Sources are expected to:
    1. Handle their own errors internally (network, auth, parsing)
    2. Return SourceResult with error=str on failure — never raise
    3. Be stateless between calls (no instance-level cache needed)
    """

    @abstractmethod
    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch data from the source and return a structured result.

        Args:
            config: The full parsed YAML config dict. Sources read their
                    section from `config['sources'][self.name]` plus any
                    source-specific env vars.

        Returns:
            SourceResult with either `data` (on success) or `error` (on failure).
        """
        ...
