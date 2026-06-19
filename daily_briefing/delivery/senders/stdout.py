"""Stdout sender — default delivery method, zero configuration.

Simply prints the message to stdout. Always available as fallback.
"""


import click

from daily_briefing.delivery.base import DeliveryProtocol, DeliveryResult


class StdoutSender(DeliveryProtocol):
    """Prints the message to stdout."""

    name = "stdout"

    def send(self, message: str, **kwargs) -> DeliveryResult:
        click.echo(message)
        return DeliveryResult(success=True, channel="stdout")
