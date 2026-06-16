"""Delivery sender factory.

Registers available senders and selects them by method name.
Defaults to stdout if no delivery config is provided.
"""

from __future__ import annotations

from daily_briefing.delivery.base import DeliveryProtocol, DeliveryResult
from daily_briefing.delivery.senders.stdout import StdoutSender
from daily_briefing.delivery.senders.ntfy import NtfySender
from daily_briefing.delivery.senders.telegram import TelegramSender

# Registry of available senders
_SENDERS: dict[str, type[DeliveryProtocol]] = {
    "stdout": StdoutSender,
    "ntfy": NtfySender,
    "telegram": TelegramSender,
}


def get_sender(method: str) -> DeliveryProtocol:
    """Get a delivery sender by method name.

    Args:
        method: 'stdout', 'ntfy'

    Returns:
        An instance of the requested sender.

    Raises:
        ValueError: If the method is unknown.
    """
    cls = _SENDERS.get(method)
    if cls is None:
        raise ValueError(
            f"Unknown delivery method: {method}. "
            f"Available: {list(_SENDERS.keys())}"
        )
    return cls()


def deliver(
    message: str,
    delivery_configs: list[dict] | None = None,
) -> list[DeliveryResult]:
    """Deliver a message through all configured channels.

    Args:
        message: The text to deliver.
        delivery_configs: List of delivery config dicts from brief.yaml.
                         Each dict has 'method' and optional kwargs.
                         Defaults to [{'method': 'stdout'}].

    Returns:
        List of DeliveryResult objects, one per configured method.
    """
    if not delivery_configs:
        delivery_configs = [{"method": "stdout"}]

    results = []
    for dc in delivery_configs:
        method = dc.get("method", "stdout")
        try:
            sender = get_sender(method)
            kwargs = {k: v for k, v in dc.items() if k != "method"}
            result = sender.send(message, **kwargs)
            results.append(result)
        except ValueError as e:
            results.append(DeliveryResult(success=False, channel=method, error=str(e)))

    return results
