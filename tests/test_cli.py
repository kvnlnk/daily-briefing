"""Tests for CLI — flag existence and basic invocation.

The --json flag already exists in cli.py. This test suite confirms:
- --help documents --json
- --list-sources works without network/config
"""
from click.testing import CliRunner

from daily_briefing.cli import cli


class TestCliFlags:
    def test_help_contains_json_flag(self):
        """--help output should mention --json."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_help_contains_daemon_command(self):
        """--help output should mention daemon."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "daemon" in result.output

    def test_list_sources(self):
        """--list-sources should work without config."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--list-sources"])
        assert result.exit_code == 0
        assert "weather" in result.output
        assert "news" in result.output
        assert "reddit" in result.output

    def test_daemon_help(self):
        """daemon --help should show options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["daemon", "--help"])
        assert result.exit_code == 0
        assert "--at" in result.output
        assert "--once" in result.output
