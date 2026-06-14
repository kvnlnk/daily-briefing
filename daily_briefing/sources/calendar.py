"""Calendar source — fetches today's events from Google Calendar.

Uses `google-api-python-client` (already installed) which works with the
Hermes `google-workspace` skill OAuth setup.

Expected OAuth flow (one-time):
  python ~/.hermes/skills/productivity.disabled/google-workspace/scripts/setup.py --check
    → If NOT_AUTHENTICATED, follow the skill's setup instructions.
  The Google token lives at ~/.hermes/google_token.json after setup.

Calendar list output per event:
  {id, summary, start, end, location, description, htmlLink}
"""

from __future__ import annotations

import datetime
import os
import sys
from typing import Any

from daily_briefing.sources.base import SourceProtocol, SourceResult

# Timezone for date boundary calculation (user's local timezone)
DEFAULT_TZ = os.environ.get("TZ", "Europe/Berlin")


class CalendarSource(SourceProtocol):
    """Fetches today's Google Calendar events."""

    name = "calendar"

    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch events for today."""
        try:
            events = self._get_events()
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
                error="google-api-python-client not installed. Run: pip install google-api-python-client",
            )
        except Exception as e:
            error_msg = str(e)
            # Give helpful guidance for common setup issues
            if "NOT_AUTHENTICATED" in error_msg or "credentials" in error_msg.lower():
                error_msg = (
                    "Google Calendar not authenticated. "
                    "Run the google-workspace skill setup: "
                    "python ~/.hermes/skills/productivity.disabled/google-workspace/scripts/setup.py --check"
                )
            return SourceResult(
                name=self.name,
                priority=20,
                error=f"Calendar error: {error_msg}",
            )

    def _get_events(self) -> list[dict[str, Any]]:
        """Fetch today's events from Google Calendar."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = self._load_credentials()
        service = build("calendar", "v3", credentials=creds)

        # Time range: midnight to midnight in user's timezone
        now = datetime.datetime.now(datetime.timezone.utc)
        today_start = datetime.datetime.combine(
            now.astimezone(datetime.timezone(datetime.timedelta(hours=2))).date(),
            datetime.time.min,
            tzinfo=datetime.timezone(datetime.timedelta(hours=2)),
        )
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

    def _load_credentials(self):
        """Load Google OAuth credentials from Hermes token file."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        token_path = os.path.expanduser("~/.hermes/google_token.json")

        if not os.path.exists(token_path):
            # Try alternate locations
            alt_path = os.path.expanduser("~/.hermes/google_oauth_token.json")
            if os.path.exists(alt_path):
                token_path = alt_path
            else:
                raise FileNotFoundError(
                    f"Google token not found at {token_path}. "
                    "Run the google-workspace skill setup first."
                )

        creds = Credentials.from_authorized_user_file(token_path)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

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
