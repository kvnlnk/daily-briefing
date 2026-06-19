"""Tests for the setup wizard."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from daily_briefing.setup_wizard import run_setup


class TestSetupWizard:
    """Setup wizard integration tests."""

    def test_setup_creates_config_from_example(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cwd = Path.cwd()
            os.chdir(tmpdir)

            try:
                # Create an example config
                example = {"sources": {"weather": {"enabled": True}}, "output": {"lang": "en"}}
                with open("brief.example.yaml", "w") as f:
                    yaml.dump(example, f)

                # Run setup with mocked prompts
                with patch("click.confirm", return_value=False):
                    with patch("click.prompt", side_effect=["London", "51.5", "-0.12", "en"]):
                        run_setup(config_path="brief.yaml", env_path=".env")

                assert os.path.exists("brief.yaml")
                with open("brief.yaml") as f:
                    config = yaml.safe_load(f)
                assert config["sources"]["weather"]["enabled"] is True
                assert config["output"]["lang"] == "en"
            finally:
                os.chdir(orig_cwd)

    def test_setup_keeps_existing_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cwd = Path.cwd()
            os.chdir(tmpdir)

            try:
                # Create existing config + example
                existing = {"sources": {"weather": {"enabled": False}}, "output": {"lang": "de"}}
                with open("brief.yaml", "w") as f:
                    yaml.dump(existing, f)
                with open("brief.example.yaml", "w") as f:
                    yaml.dump({"sources": {}, "output": {}}, f)

                with patch("click.confirm", return_value=False):
                    with patch("click.prompt", side_effect=["London", "51.5", "-0.12", "en"]):
                        run_setup(config_path="brief.yaml", env_path=".env")

                # Original config should NOT be overwritten
                with open("brief.yaml") as f:
                    config = yaml.safe_load(f)
                assert config["output"]["lang"] == "de"  # unchanged
            finally:
                os.chdir(orig_cwd)

    def test_setup_creates_env_from_example(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cwd = Path.cwd()
            os.chdir(tmpdir)

            try:
                with open("brief.example.yaml", "w") as f:
                    yaml.dump({"output": {"lang": "en"}}, f)
                with open(".env.example", "w") as f:
                    f.write("NTFY_TOPIC=\n")

                with patch("click.confirm", return_value=False):
                    with patch("click.prompt", side_effect=["London", "51.5", "-0.12", "en"]):
                        run_setup(config_path="brief.yaml", env_path=".env")

                assert os.path.exists(".env")
                with open(".env") as f:
                    assert "NTFY_TOPIC" in f.read()
            finally:
                os.chdir(orig_cwd)

    def test_setup_adds_weather_location(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cwd = Path.cwd()
            os.chdir(tmpdir)

            try:
                with open("brief.example.yaml", "w") as f:
                    yaml.dump({"sources": {}, "output": {"lang": "en"}}, f)

                with patch("click.confirm", return_value=False):
                    with patch("click.prompt", side_effect=["Berlin", "52.52", "13.40", "en"]):
                        run_setup(config_path="brief.yaml", env_path=".env")

                with open("brief.yaml") as f:
                    config = yaml.safe_load(f)
                weather = config["sources"]["weather"]
                assert weather["enabled"] is True
                assert weather["locations"][0]["name"] == "Berlin"
            finally:
                os.chdir(orig_cwd)

    def test_cli_setup_subcommand_registered(self):
        """The setup subcommand should be available via CLI."""
        from click.testing import CliRunner
        from daily_briefing.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["setup", "--help"])
        assert result.exit_code == 0
        assert "setup" in result.output.lower()

    def test_cli_doctor_subcommand_registered(self):
        """The doctor subcommand should be available via CLI."""
        from click.testing import CliRunner
        from daily_briefing.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "doctor" in result.output.lower()
