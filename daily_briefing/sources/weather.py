"""Weather source — fetches current conditions from Open-Meteo (free, no API key).

Open-Meteo API docs: https://open-meteo.com/en/docs
Weather codes: https://open-meteo.com/en/docs#weathervariables
"""

from __future__ import annotations

import os
from typing import Any

import requests

from daily_briefing.sources.base import SourceProtocol, SourceResult

# WMO Weather interpretation codes → human-readable
# Source: https://open-meteo.com/en/docs#weathervariables
WEATHER_MAP: dict[int, str] = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# Default single location (fallback if no locations in brief.yaml)
DEFAULT_LAT = float(os.environ.get("WEATHER_LAT", "50.1109"))
DEFAULT_LON = float(os.environ.get("WEATHER_LON", "8.6821"))
DEFAULT_NAME = os.environ.get("WEATHER_NAME", "Frankfurt")


class WeatherSource(SourceProtocol):
    """Fetches current weather from Open-Meteo's free API."""

    name = "weather"

    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch current conditions + today's forecast for configured locations."""
        try:
            # Read locations from brief.yaml or use default
            weather_cfg = config.get("sources", {}).get("weather", {})
            locations = weather_cfg.get("locations", [])

            if not locations:
                # Fallback to single env-var location
                data = self._fetch_one(DEFAULT_LAT, DEFAULT_LON, DEFAULT_NAME)
                return SourceResult(name=self.name, priority=10, data=data)

            # Fetch all locations
            all_data = {}
            for loc in locations:
                lat = loc.get("lat")
                lon = loc.get("lon")
                name = loc.get("name", "Unknown")
                if lat is not None and lon is not None:
                    all_data[name] = self._fetch_one(float(lat), float(lon), name)

            return SourceResult(
                name=self.name,
                priority=10,
                data={"locations": all_data},
            )
        except requests.RequestException as e:
            return SourceResult(
                name=self.name,
                priority=10,
                error=f"Weather API unreachable: {e}",
            )
        except (KeyError, ValueError, TypeError) as e:
            return SourceResult(
                name=self.name,
                priority=10,
                error=f"Weather data parse error: {e}",
            )

    def _fetch_one(self, lat: float, lon: float, name: str) -> dict[str, Any]:
        """Fetch weather for a single location."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "Europe/Berlin",
            "forecast_days": 1,
        }
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()

        current = body.get("current", {})
        daily = body.get("daily", {})

        weather_code = current.get("weather_code", 0)
        condition = WEATHER_MAP.get(weather_code, "Unknown")

        return {
            "location": name,
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
            "condition": condition,
            "weather_code": weather_code,
            # Today's forecast
            "high": daily.get("temperature_2m_max", [None])[0] if daily.get("temperature_2m_max") else None,
            "low": daily.get("temperature_2m_min", [None])[0] if daily.get("temperature_2m_min") else None,
            "rain_chance": daily.get("precipitation_probability_max", [None])[0] if daily.get("precipitation_probability_max") else None,
        }
