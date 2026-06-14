"""Bahn source — fetches departure times from DB transport.rest API.

Free public API — no API key needed.
Docs: https://v6.db.transport.rest/

Station IDs (examples):
  8000105 — Frankfurt (Main) Hbf
  8000152 — Wiesbaden Hbf
  8098160 — Frankfurt Flughafen Fernbahnhof

Configure departure/arrival stations in .env or brief.yaml.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from daily_briefing.sources.base import SourceProtocol, SourceResult

# Configure via env vars (supports .env file)
DEPARTURE_STATION = os.environ.get("BAHN_DEPARTURE_STATION", "8000105")  # Frankfurt Hbf
ARRIVAL_STATION = os.environ.get("BAHN_ARRIVAL_STATION", "")
DEPARTURE_TIME = os.environ.get("BAHN_TIME", "07:30")
BAHN_MODE = os.environ.get("BAHN_MODE", "depart")  # 'depart' or 'arrive'


class BahnSource(SourceProtocol):
    """Fetches upcoming departures at the configured station."""

    name = "bahn"

    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch next departures from DB Fahrplan."""
        source_config = config.get("sources", {}).get("bahn", {})
        station_id = source_config.get("station", DEPARTURE_STATION)
        target_station = source_config.get("target_station", ARRIVAL_STATION)
        time_filter = source_config.get("time", DEPARTURE_TIME)
        mode = source_config.get("mode", BAHN_MODE)

        try:
            # First, get station name for display
            station_info = self._get_station_info(station_id)
            station_name = station_info.get("name", f"Station {station_id}")

            # Get departures
            departures = self._get_departures(station_id, target_station, time_filter)
            upcoming = departures[:6]  # Next 6 departures

            return SourceResult(
                name=self.name,
                priority=40,
                data={
                    "station": station_name,
                    "station_id": station_id,
                    "target": target_station,
                    "mode": mode,
                    "departures": upcoming,
                    "total_upcoming": len(departures),
                },
            )
        except requests.RequestException as e:
            return SourceResult(
                name=self.name,
                priority=40,
                error=f"DB API unreachable: {e}",
            )
        except (KeyError, ValueError, TypeError) as e:
            return SourceResult(
                name=self.name,
                priority=40,
                error=f"DB data parse error: {e}",
            )

    def _get_station_info(self, station_id: str) -> dict[str, Any]:
        """Fetch station metadata."""
        resp = requests.get(
            f"https://v6.db.transport.rest/stops/{station_id}",
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def _get_departures(
        self,
        station_id: str,
        target_station: str,
        time_filter: str,
    ) -> list[dict[str, Any]]:
        """Fetch upcoming departures, optionally filtered by target and time."""
        resp = requests.get(
            f"https://v6.db.transport.rest/stops/{station_id}/departures",
            params={
                "duration": 120,  # Next 2 hours
                "linesOfStops": "false",
                "remarks": "false",
                "language": "de",
            },
            timeout=10,
        )
        resp.raise_for_status()
        all_departures = resp.json()

        # Filter by target station if configured
        if target_station:
            all_departures = [
                d for d in all_departures
                if d.get("direction", "").lower().find(target_station.lower()) != -1
                or any(
                    s.get("id") == target_station
                    for s in d.get("nextStops", [])
                )
            ]

        # Filter by time: only show departures after the configured time
        if time_filter:
            hour, minute = map(int, time_filter.split(":"))
            all_departures = [
                d for d in all_departures
                if self._is_after(d, hour, minute)
            ]

        # Format departures into a clean structure
        result = []
        for d in all_departures:
            # Extract platform
            platform = None
            if d.get("platform"):
                platform = d["platform"]

            # Extract delay
            delay_minutes = 0
            if d.get("delay") is not None:
                delay_minutes = int(d["delay"]) // 60
            elif d.get("departureDelay") is not None:
                delay_minutes = int(d["departureDelay"]) // 60

            # Build display line name
            line_name = d.get("line", {}).get("name", d.get("line", {}).get("productName", "??"))

            result.append({
                "time": d.get("when") or d.get("plannedWhen", ""),
                "line": line_name,
                "direction": d.get("direction", ""),
                "platform": platform,
                "delay_minutes": delay_minutes,
            })

        return result

    @staticmethod
    def _is_after(departure: dict, hour: int, minute: int) -> bool:
        """Check if departure is after the given time."""
        time_str = departure.get("when") or departure.get("plannedWhen", "")
        if not time_str:
            return True  # Can't determine — include it
        try:
            dep_hour = int(time_str[11:13])
            dep_minute = int(time_str[14:16])
            return (dep_hour > hour) or (dep_hour == hour and dep_minute >= minute)
        except (ValueError, IndexError):
            return True
