"""ntfy sender — push notification via ntfy.sh (or self-hosted).

Requires NTFY_TOPIC env var or topic in brief.yaml delivery config.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from daily_briefing.delivery.base import DeliveryProtocol, DeliveryResult

NTFY_DEFAULT_SERVER = "https://ntfy.sh"


class NtfySender(DeliveryProtocol):
    """Sends push notification via ntfy.sh."""

    name = "ntfy"

    def send(
        self,
        message: str,
        topic: str = "",
        server: str = "",
        **kwargs,
    ) -> DeliveryResult:
        resolved_topic = topic or os.environ.get("NTFY_TOPIC", "")
        if not resolved_topic:
            return DeliveryResult(
                success=False,
                channel="ntfy",
                error="NTFY_TOPIC not set. Set NTFY_TOPIC env var or topic in brief.yaml delivery config.",
            )

        resolved_server = server or NTFY_DEFAULT_SERVER
        try:
            resp = requests.post(
                f"{resolved_server}/{resolved_topic}",
                data=message.encode("utf-8"),
                timeout=10,
                headers={"Title": "Daily Briefing"},
            )
            resp.raise_for_status()
            return DeliveryResult(success=True, channel=f"ntfy:{resolved_topic}")
        except requests.RequestException as e:
            return DeliveryResult(
                success=False,
                channel="ntfy",
                error=f"ntfy error: {e}",
            )
