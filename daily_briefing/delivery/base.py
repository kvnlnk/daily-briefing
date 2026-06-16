"""Delivery protocol for sending briefing messages.

Each sender implements DeliveryProtocol.send().
Selection happens via brief.yaml delivery[] list.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DeliveryResult:
    """The result of one delivery attempt."""

    success: bool
    """Whether the message was sent successfully."""

    channel: str
    """The channel used (e.g. 'stdout', 'ntfy:mytopic')."""

    error: str | None = None
    """Human-readable error message if delivery failed."""


class DeliveryProtocol(ABC):
    """Protocol that all delivery senders must implement."""

    name: str = ""
    """Human-readable sender name."""

    @abstractmethod
    def send(self, message: str, **kwargs) -> DeliveryResult:
        """Send a message through this channel.

        Args:
            message: The text to deliver.
            **kwargs: Channel-specific options from brief.yaml.

        Returns:
            DeliveryResult indicating success or failure.
        """
        ...
