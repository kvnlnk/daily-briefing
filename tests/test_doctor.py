"""Tests for the doctor diagnostic module."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from daily_briefing.doctor import run_doctor


class TestDoctor:
    """Doctor diagnostics."""

    def test_doctor_with_nonexistent_config(self):
        """Doctor should detect missing config file."""
        import tempfile
        from pathlib import Path

        orig_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                result = run_doctor(config_path="/nonexistent/brief.yaml")
                assert result is False
            finally:
                os.chdir(orig_cwd)

    def test_doctor_detects_missing_config(self):
        from unittest.mock import MagicMock

        with patch("os.path.exists", return_value=False):
            with patch("daily_briefing.doctor._find_config", return_value=None):
                result = run_doctor(config_path="/fake/path.yaml")
                assert result is False

    def test_doctor_report_contains_sources(self):
        """Doctor output should mention sources."""
        from click.testing import CliRunner
        from daily_briefing.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        # Should mention "Sources" in output
        assert "Sources" in result.output or "📡" in result.output
