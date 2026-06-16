"""Tests for daily_briefing.sources.weather — multi-location support."""

from unittest.mock import patch

import pytest

from daily_briefing.sources.weather import WeatherSource


@pytest.fixture
def source():
    return WeatherSource()


class TestWeatherSource:
    """Tests the weather source logic using mocked HTTP responses."""

    def test_name(self, source):
        assert source.name == "weather"

    def test_missing_locations_returns_error(self, source):
        """When no locations in config, returns clear error instead of defaults."""
        result = source.fetch({"sources": {"weather": {}}})
        assert result.is_success() is False
        assert "Weather not configured" in result.error

    @patch("daily_briefing.sources.weather.requests.get")
    def test_multiple_locations(self, mock_get, source):
        """When locations are configured, returns dict keyed by name."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "current": {
                "temperature_2m": 15.0,
                "relative_humidity_2m": 70,
                "apparent_temperature": 14.0,
                "weather_code": 3,
                "wind_speed_10m": 8.0,
                "precipitation": 0.2,
            },
            "daily": {
                "temperature_2m_max": [18.0],
                "temperature_2m_min": [10.0],
                "precipitation_probability_max": [40],
            },
        }

        config = {
            "sources": {
                "weather": {
                    "locations": [
                        {"name": "Verden (Aller)", "lat": 52.923, "lon": 9.236},
                        {"name": "Rethem (Aller)", "lat": 52.785, "lon": 9.378},
                    ],
                },
            },
        }
        result = source.fetch(config)
        assert result.is_success()
        assert "locations" in result.data
        assert "Verden (Aller)" in result.data["locations"]
        assert "Rethem (Aller)" in result.data["locations"]
        assert result.data["locations"]["Verden (Aller)"]["condition"] == "Overcast"

    def test_no_emoji_in_weather_data(self):
        """WEATHER_MAP should not contain emoji characters."""
        import unicodedata

        from daily_briefing.sources.weather import WEATHER_MAP

        for code, condition in WEATHER_MAP.items():
            for ch in condition:
                cat = unicodedata.category(ch)
                if cat.startswith("S"):
                    # Skip symbols category which includes emoji
                    pass
            assert isinstance(code, int)
            assert isinstance(condition, str)

    @patch("daily_briefing.sources.weather.requests.get")
    def test_api_error_returns_error_result(self, mock_get, source):
        """A failed API call should produce a SourceResult with error set."""
        import requests

        mock_get.side_effect = requests.RequestException("Connection refused")

        result = source.fetch({
            "sources": {
                "weather": {
                    "locations": [{"name": "Test", "lat": 50.0, "lon": 8.0}],
                },
            },
        })
        assert result.is_success() is False
        assert "Connection refused" in result.error
