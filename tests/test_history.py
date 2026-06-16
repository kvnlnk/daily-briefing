"""Tests for daily_briefing.storage.history — SQLite save/load/diff."""

from datetime import date

import pytest

from daily_briefing.sources.base import SourceResult
from daily_briefing.storage.history import diff, load, save


class TestSaveLoad:
    def test_save_and_load_roundtrip(self):
        """Save results then load them back."""
        results = [
            SourceResult(name="weather", priority=10, data={"temp": 18.5}),
            SourceResult(name="news", priority=60, data={"headlines": ["Test"]}),
        ]
        key = date.today().isoformat()
        save(results)
        loaded = load(key)
        assert "weather" in loaded
        assert loaded["weather"]["temp"] == 18.5
        assert loaded["news"]["headlines"] == ["Test"]

    def test_load_missing_date_returns_empty_dict(self):
        """Loading a date that doesn't exist returns an empty dict."""
        result = load("1999-01-01")
        assert result == {}

    def test_save_updates_existing(self):
        """Saving twice for the same date overwrites."""
        save([SourceResult(name="weather", priority=10, data={"temp": 10.0})])
        save([SourceResult(name="weather", priority=10, data={"temp": 20.0})])
        loaded = load()
        assert loaded["weather"]["temp"] == 20.0

    def test_save_skips_failed_results(self):
        """Only successful results should be persisted."""
        save([
            SourceResult(name="weather", priority=10, data={"temp": 15.0}),
            SourceResult(name="bahn", priority=40, error="API down"),
        ])
        loaded = load()
        assert "weather" in loaded
        assert "bahn" not in loaded


class TestDiff:
    def test_no_diff_when_identical(self):
        today = {"weather": {"temperature": 15.0}}
        yesterday = {"weather": {"temperature": 15.0}}
        result = diff(today, yesterday)
        assert "weather" in result
        assert result["weather"]["temperature_diff"] == 0.0
        assert "unverändert" in result["weather"]["note"]

    def test_detects_temperature_change(self):
        today = {"weather": {"temperature": 20.0}}
        yesterday = {"weather": {"temperature": 15.0}}
        result = diff(today, yesterday)
        assert "weather" in result
        assert result["weather"]["temperature_diff"] == 5.0

    def test_detects_cooler_temperature(self):
        today = {"weather": {"temperature": 10.0}}
        yesterday = {"weather": {"temperature": 15.0}}
        result = diff(today, yesterday)
        assert "weather" in result
        assert result["weather"]["temperature_diff"] == -5.0

    def test_missing_yesterday_source(self):
        """If a source was not in yesterday, no diff for it."""
        today = {"weather": {"temperature": 15.0}}
        yesterday = {}
        result = diff(today, yesterday)
        assert result == {}

    def test_missing_today_source(self):
        """If a source is not in today, no diff for it."""
        today = {}
        yesterday = {"weather": {"temperature": 15.0}}
        result = diff(today, yesterday)
        assert result == {}

    def test_github_diff(self):
        today = {"github": {"total_issues": 5, "total_prs": 3}}
        yesterday = {"github": {"total_issues": 3, "total_prs": 1}}
        result = diff(today, yesterday)
        assert "github" in result
        assert result["github"]["issue_diff"] == 2
        assert result["github"]["pr_diff"] == 2
