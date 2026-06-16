"""Calendar source — fetches today's events from Google Calendar.

Uses `google-api-python-client` (optional dependency).

OAuth setup (one-time):
  1. Go to https://console.cloud.google.com/apis/credentials
  2. Create OAuth 2.0 Client ID for Desktop app
  3. Download credentials and save as ~/.google_client_id.json
  4. Run: pip install 'daily-briefing[calendar]'
  5. First run will open a browser for OAuth consent
  6. Token is saved to ~/.google_token.json (configurable)

Calendar list output per event:
  {title, start, end, location, link}
"""

from __future__ import annotations

import datetime
import os
from typing import Any
from zoneinfo import ZoneInfo

from daily_briefing.sources.base import SourceProtocol, SourceResult

# Default token path — can be overridden via brief.yaml or GOOGLE_TOKEN_PATH env var
DEFAULT_TOKEN_PATH = os.path.expanduser("~/.google_token.json")


def today_start_in_tz(now: datetime.datetime, tz: ZoneInfo) -> datetime.datetime:
    """Return midnight today in the given timezone."""
    today_date = now.astimezone(tz).date()
    return datetime.datetime.combine(today_date, datetime.time.min, tzinfo=tz)


class CalendarSource(SourceProtocol):
    """Fetches today's Google Calendar events."""

    name = "calendar"

    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch events for today."""
        try:
            source_config = config.get("sources", {}).get("calendar", {})
            token_path = (
                source_config.get("token_path", None)
                or os.environ.get("GOOGLE_TOKEN_PATH", None)
                or DEFAULT_TOKEN_PATH
            )
            tz_name = config.get("output", {}).get("timezone", "Europe/Berlin")
            events = self._get_events(token_path, tz_name)
            return SourceResult(
                name=self.name,
                priority=20,
                data={
                    "events": events,
                    "total": len(events),
                    "busy_hours": self._count_busy_hours(events),
                },
            )
        except ImportError:
            return SourceResult(
                name=self.name,
                priority=20,
                error="google-api-python-client not installed. Run: pip install 'daily-briefing[calendar]'",
            )
        except Exception as e:
            error_msg = str(e)
            if "credentials" in error_msg.lower() or "token" in error_msg.lower():
                error_msg = (
                    "Google Calendar not authenticated. "
                    "See docs/calendar-setup.md for OAuth setup instructions."
                )
            return SourceResult(
                name=self.name,
                priority=20,
                error=f"Calendar error: {error_msg}",
            )

    def _get_events(self, token_path: str, tz_name: str = "Europe/Berlin") -> list[dict[str, Any]]:
        """Fetch today's events from Google Calendar."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = self._load_credentials(token_path)
        if creds is None:
            raise FileNotFoundError(f"Google token not found at {token_path}")

        service = build("calendar", "v3", credentials=creds)

        # Time range: midnight to midnight in user's timezone
        tz = ZoneInfo(tz_name)
        now = datetime.datetime.now(datetime.timezone.utc)
        today_start = today_start_in_tz(now, tz)
        today_end = today_start + datetime.timedelta(days=1)

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=today_start.isoformat(),
                timeMax=today_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=10,
            )
            .execute()
        )

        events = []
        for event in events_result.get("items", []):
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            events.append({
                "title": event.get("summary", "Untitled"),
                "start": start,
                "end": end,
                "location": event.get("location", ""),
                "link": event.get("htmlLink", ""),
            })

        return events

    def _load_credentials(self, token_path: str):
        """Load Google OAuth credentials from token file.

        Returns None if token file doesn't exist (graceful degradation).
        """
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        token_path = os.path.expanduser(token_path)

        if not os.path.exists(token_path):
            return None

        creds = Credentials.from_authorized_user_file(token_path)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                return None

        return creds

    def _count_busy_hours(self, events: list[dict[str, Any]]) -> float:
        """Estimate total hours blocked by events today."""
        total_minutes = 0
        for event in events:
            try:
                start = datetime.datetime.fromisoformat(event["start"])
                end = datetime.datetime.fromisoformat(event["end"])
                total_minutes += (end - start).total_seconds() / 60
            except (ValueError, KeyError):
                # All-day events — count as 1 hour
                total_minutes += 60
        return round(total_minutes / 60, 1)
