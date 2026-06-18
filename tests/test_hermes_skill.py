"""Tests for integrations/hermes/briefing_skill.py — mocked subprocess."""
import json
import subprocess
from unittest.mock import MagicMock, patch

from integrations.hermes.briefing_skill import run_briefing, run_full_briefing


class TestHermesSkill:
    def test_run_briefing_calls_correct_command(self):
        """Verify the skill invokes daily-briefing with expected args."""
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"data": []}),
                stderr="",
            )
            result = run_briefing()

            mock_run.assert_called_once()
            args, _ = mock_run.call_args
            cmd = args[0]
            assert cmd[0] == "daily-briefing"
            assert "--json" in cmd
            assert "--dry-run" in cmd
            assert result == {"data": []}

    def test_run_briefing_with_config_path(self):
        """--config flag should be appended when config_path is given."""
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"data": []}),
                stderr="",
            )
            run_briefing(config_path="/custom/brief.yaml")

            args, _ = mock_run.call_args
            cmd = args[0]
            assert "--config" in cmd
            assert "/custom/brief.yaml" in cmd

    def test_run_briefing_timeout(self):
        """Timeout should return an error dict."""
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="daily-briefing", timeout=30
            )
            result = run_briefing()
            assert "error" in result
            assert "timed out" in result["error"]

    def test_run_briefing_cli_not_found(self):
        """FileNotFoundError (CLI not installed) should return an error dict."""
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = run_briefing()
            assert "error" in result
            assert "not found" in result["error"]

    def test_run_briefing_invalid_json(self):
        """Non-JSON stdout should return an error dict."""
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="not json",
                stderr="",
            )
            result = run_briefing()
            assert "error" in result
            assert "Invalid JSON" in result["error"]

    def test_run_briefing_nonzero_exit(self):
        """Non-zero exit code should return an error dict."""
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Config file not found",
            )
            result = run_briefing()
            assert "error" in result
            assert "exited with code 1" in result["error"]

    def test_run_full_briefing_no_dry_run(self):
        """run_full_briefing should NOT include --dry-run."""
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"data": []}),
                stderr="",
            )
            result = run_full_briefing()

            args, _ = mock_run.call_args
            cmd = args[0]
            assert "--dry-run" not in cmd
            assert result == {"data": []}

    def test_run_full_briefing_timeout(self):
        """Full briefing timeout should return an error dict."""
        with patch("integrations.hermes.briefing_skill.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="daily-briefing", timeout=60
            )
            result = run_full_briefing()
            assert "error" in result
            assert "timed out" in result["error"]
