"""Tests for summarizer/prompts — prompt building and data simplification."""
import pytest
from daily_briefing.summarizer.prompts import build_prompt, _simplify_data
from daily_briefing.sources.base import SourceResult
from daily_briefing.config import OutputConfig


class TestBuildPrompt:
    def test_builds_prompt_from_results(self):
        results = [
            SourceResult(name="weather", priority=10, data={"location": "Berlin", "condition": "Sunny", "temperature": 20.0}),
        ]
        prompt = build_prompt(results, config=OutputConfig(max_length=100))
        assert "WEATHER" in prompt
        assert "Sunny" in prompt

    def test_includes_error_sources(self):
        results = [
            SourceResult(name="weather", priority=10, data={"condition": "Sunny"}),
            SourceResult(name="bahn", priority=40, error="API timeout"),
        ]
        prompt = build_prompt(results, config=OutputConfig(max_length=200))
        # Error sources should appear with NICHT VERFUEGBAR marker
        assert "NICHT" in prompt or "VERF" in prompt or "bahn" in prompt.lower()

    def test_respects_max_length(self):
        results = [
            SourceResult(name="weather", priority=10, data={"condition": "Sunny", "temperature": 20.0}),
        ]
        prompt = build_prompt(results, config=OutputConfig(max_length=50))
        assert len(prompt) > 0


class TestSimplifyData:
    def test_weather_single_location(self):
        data = {"location": "Berlin", "temperature": 18.0, "condition": "Cloudy", "weather_code": 3}
        simplified = _simplify_data("weather", data)
        assert simplified["temperature"] == 18.0
        assert "weather_code" not in simplified  # excluded from weather data

    def test_weather_multi_location(self):
        data = {"locations": {"Berlin": {"temperature": 18.0}, "Hamburg": {"temperature": 15.0}}}
        simplified = _simplify_data("weather", data)
        assert "locations" in simplified
        assert simplified["locations"]["Berlin"]["temperature"] == 18.0

    def test_unknown_source_passthrough(self):
        data = {"custom": "value"}
        simplified = _simplify_data("unknown_source", data)
        assert simplified == data

    def test_calendar_simplify(self):
        data = {
            "events": [{"title": "Meeting", "start": "2026-06-16T10:00", "location": "Room 1"}],
            "total": 1, "busy_hours": 1.0,
        }
        simplified = _simplify_data("calendar", data)
        assert simplified["total_events"] == 1
        assert simplified["events"][0]["title"] == "Meeting"
        assert simplified["busy_hours"] == 1.0
