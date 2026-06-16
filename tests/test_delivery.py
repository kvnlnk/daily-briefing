"""Tests for delivery protocol — stdout, ntfy, and factory."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import requests

from daily_briefing.delivery import deliver, get_sender
from daily_briefing.delivery.base import DeliveryProtocol, DeliveryResult
from daily_briefing.delivery.senders.stdout import StdoutSender
from daily_briefing.delivery.senders.ntfy import NtfySender


class TestDeliveryProtocol:
    """DeliveryProtocol ABC contract."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            DeliveryProtocol()  # type: ignore[abstract]

    def test_delivery_result_defaults(self):
        r = DeliveryResult(success=True, channel="stdout")
        assert r.error is None

    def test_delivery_result_with_error(self):
        r = DeliveryResult(success=False, channel="ntfy", error="oops")
        assert r.error == "oops"


class TestStdoutSender:
    """Stdout sender — zero-config default."""

    def test_send_prints_via_click(self):
        sender = StdoutSender()
        with patch("daily_briefing.delivery.senders.stdout.click.echo") as mock:
            result = sender.send("Hello world")
        mock.assert_called_once_with("Hello world")
        assert result.success is True
        assert result.channel == "stdout"

    def test_name_is_stdout(self):
        assert StdoutSender().name == "stdout"

    def test_accepts_extra_kwargs_gracefully(self):
        sender = StdoutSender()
        with patch("daily_briefing.delivery.senders.stdout.click.echo"):
            result = sender.send("test", unknown_param="ignored")
        assert result.success is True


class TestNtfySender:
    """Ntfy sender — push notification."""

    def test_name_is_ntfy(self):
        assert NtfySender().name == "ntfy"

    def test_send_success(self):
        sender = NtfySender()
        with patch("requests.post") as mock_post:
            mock_response = mock_post.return_value
            mock_response.raise_for_status.return_value = None

            result = sender.send("Test message", topic="mytopic")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://ntfy.sh/mytopic"
        assert kwargs["data"] == b"Test message"
        assert kwargs["headers"]["Title"] == "Daily Briefing"
        assert result.success is True
        assert result.channel == "ntfy:mytopic"

    def test_send_with_custom_server(self):
        sender = NtfySender()
        with patch("requests.post") as mock_post:
            mock_response = mock_post.return_value
            mock_response.raise_for_status.return_value = None

            result = sender.send("hi", topic="test", server="https://ntfy.example.com")

        mock_post.assert_called_once_with(
            "https://ntfy.example.com/test",
            data=b"hi",
            timeout=10,
            headers={"Title": "Daily Briefing"},
        )
        assert result.success is True

    def test_send_no_topic_raises_graceful_error(self):
        sender = NtfySender()
        # Ensure NTFY_TOPIC is not set
        with patch.dict(os.environ, {}, clear=True):
            result = sender.send("msg")
        assert result.success is False
        assert "NTFY_TOPIC not set" in result.error

    def test_send_uses_env_var_topic(self):
        sender = NtfySender()
        with patch.dict(os.environ, {"NTFY_TOPIC": "env-topic"}):
            with patch("requests.post") as mock_post:
                mock_response = mock_post.return_value
                mock_response.raise_for_status.return_value = None
                result = sender.send("msg")

        mock_post.assert_called_once_with(
            "https://ntfy.sh/env-topic",
            data=b"msg",
            timeout=10,
            headers={"Title": "Daily Briefing"},
        )
        assert result.success is True
        assert result.channel == "ntfy:env-topic"

    def test_send_http_error(self):
        sender = NtfySender()
        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.RequestException("Connection refused")
            result = sender.send("msg", topic="test")
        assert result.success is False
        assert "Connection refused" in result.error


class TestFactory:
    """Delivery factory selection."""

    def test_get_stdout_sender(self):
        sender = get_sender("stdout")
        assert isinstance(sender, StdoutSender)

    def test_get_ntfy_sender(self):
        sender = get_sender("ntfy")
        assert isinstance(sender, NtfySender)

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="unknown"):
            get_sender("unknown")

    def test_deliver_convenience_defaults_to_stdout(self):
        with patch("daily_briefing.delivery.senders.stdout.click.echo") as mock:
            results = deliver("Hello")
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].channel == "stdout"
        mock.assert_called_once_with("Hello")

    def test_deliver_multiple_channels(self):
        configs = [
            {"method": "stdout"},
            {"method": "ntfy", "topic": "mytopic"},
        ]
        with patch("daily_briefing.delivery.senders.stdout.click.echo"):
            with patch("requests.post") as mock_post:
                mock_response = mock_post.return_value
                mock_response.raise_for_status.return_value = None
                results = deliver("Multi-test", configs)

        assert len(results) == 2
        assert results[0].channel == "stdout"
        assert results[0].success is True
        assert results[1].channel == "ntfy:mytopic"
        assert results[1].success is True

    def test_deliver_unknown_method_returns_error(self):
        configs = [{"method": "invalid"}]
        results = deliver("Test", configs)
        assert len(results) == 1
        assert results[0].success is False
        assert "unknown" in results[0].error.lower()
