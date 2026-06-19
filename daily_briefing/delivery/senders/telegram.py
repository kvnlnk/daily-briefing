"""Telegram sender — delivers briefing via a Telegram bot.

Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars
or config in brief.yaml delivery[] section.
"""

from __future__ import annotations

import os

import requests

from daily_briefing.delivery.base import DeliveryProtocol, DeliveryResult

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramSender(DeliveryProtocol):
    """Sends a briefing message via Telegram Bot API."""

    name = "telegram"

    def send(
        self,
        message: str,
        token: str = "",
        chat_id: str = "",
        parse_mode: str = "HTML",
        **kwargs,
    ) -> DeliveryResult:
        resolved_token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        resolved_chat = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

        if not resolved_token:
            return DeliveryResult(
                success=False,
                channel="telegram",
                error="TELEGRAM_BOT_TOKEN not set. Set env var or token in delivery config.",
            )
        if not resolved_chat:
            return DeliveryResult(
                success=False,
                channel="telegram",
                error="TELEGRAM_CHAT_ID not set. Set env var or chat_id in delivery config.",
            )

        url = TELEGRAM_API_BASE.format(token=resolved_token)
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": resolved_chat,
                    "text": message,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                return DeliveryResult(success=True, channel=f"telegram:{resolved_chat}")
            return DeliveryResult(
                success=False,
                channel="telegram",
                error=f"Telegram API error: {data.get('description', 'unknown')}",
            )
        except requests.RequestException as e:
            return DeliveryResult(
                success=False,
                channel="telegram",
                error=f"Telegram request failed: {e}",
            )
