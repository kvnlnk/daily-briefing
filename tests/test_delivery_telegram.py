"""Tests for Telegram delivery sender."""

from __future__ import annotations

import os
from unittest.mock import patch

import requests

from daily_briefing.delivery import get_sender
from daily_briefing.delivery.senders.telegram import TelegramSender


class TestTelegramSender:
    """Telegram Bot API sender."""

    def test_name_is_telegram(self):
        assert TelegramSender().name == "telegram"

    def test_send_success(self):
        sender = TelegramSender()
        with patch("requests.post") as mock_post:
            mock_response = mock_post.return_value
            mock_response.json.return_value = {"ok": True}
            mock_response.raise_for_status.return_value = None

            result = sender.send("Hello", token="123:abc", chat_id="-100123")

        assert result.success is True
        assert result.channel == "telegram:-100123"

        # Verify API call format
        args, kwargs = mock_post.call_args
        assert "api.telegram.org" in args[0]
        assert kwargs["json"]["chat_id"] == "-100123"
        assert kwargs["json"]["text"] == "Hello"
        assert kwargs["json"]["parse_mode"] == "HTML"

    def test_send_no_token(self):
        sender = TelegramSender()
        result = sender.send("Hello", chat_id="-100123")
        assert result.success is False
        assert "TELEGRAM_BOT_TOKEN" in result.error

    def test_send_no_chat_id(self):
        sender = TelegramSender()
        result = sender.send("Hello", token="123:abc")
        assert result.success is False
        assert "TELEGRAM_CHAT_ID" in result.error

    def test_send_uses_env_vars(self):
        sender = TelegramSender()
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "env-token",
            "TELEGRAM_CHAT_ID": "env-chat",
        }):
            with patch("requests.post") as mock_post:
                mock_response = mock_post.return_value
                mock_response.json.return_value = {"ok": True}
                mock_response.raise_for_status.return_value = None

                result = sender.send("Env test")

        assert result.success is True
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["chat_id"] == "env-chat"

    def test_send_http_error(self):
        sender = TelegramSender()
        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.RequestException("Connection error")
            result = sender.send("Test", token="123:abc", chat_id="-100123")
        assert result.success is False
        assert "Connection error" in result.error

    def test_send_api_error(self):
        sender = TelegramSender()
        with patch("requests.post") as mock_post:
            mock_response = mock_post.return_value
            mock_response.json.return_value = {"ok": False, "description": "Chat not found"}
            mock_response.raise_for_status.return_value = None

            result = sender.send("Test", token="123:abc", chat_id="-100123")
        assert result.success is False
        assert "Chat not found" in result.error

    def test_factory_returns_telegram(self):
        sender = get_sender("telegram")
        assert isinstance(sender, TelegramSender)
