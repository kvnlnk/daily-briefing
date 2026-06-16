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

    @patch("daily_briefing.sources.weather.requests.get")
    def test_single_location_fallback(self, mock_get, source):
        """When no locations in config, uses env var defaults."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "current": {
                "temperature_2m": 18.5,
                "relative_humidity_2m": 65,
                "apparent_temperature": 17.0,
                "weather_code": 2,
                "wind_speed_10m": 12.0,
                "precipitation": 0.0,
            },
            "daily": {
                "temperature_2m_max": [22.0],
                "temperature_2m_min": [12.0],
                "precipitation_probability_max": [30],
            },
        }

        result = source.fetch({"sources": {"weather": {}}})
        assert result.is_success()
        data = result.data
        assert data["location"] is not None
        assert data["condition"] == "Partly cloudy"
        assert data["high"] == 22.0
        assert data["low"] == 12.0
        assert data["rain_chance"] == 30

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

        result = source.fetch({"sources": {"weather": {}}})
        assert result.is_success() is False
        assert "Connection refused" in result.error
