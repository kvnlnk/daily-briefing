"""Scheduler — pure time calculations for the daemon command."""
from __future__ import annotations

import zoneinfo
from datetime import datetime, timedelta, time


def seconds_until_next_run(
    now: datetime,
    at_time: str,
    tz: zoneinfo.ZoneInfo,
) -> float:
    """Calculate seconds until the next scheduled trigger time.

    Args:
        now: Current datetime (timezone-aware).
        at_time: Trigger time in "HH:MM" 24h format.
        tz: Target timezone.

    Returns:
        Seconds until the next trigger (always > 0).
    """
    hour, minute = map(int, at_time.split(":"))
    trigger_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    diff = (trigger_today - now).total_seconds()
    if diff > 0:
        return diff
    # Trigger has passed today — schedule for tomorrow
    tomorrow_date = now.date() + timedelta(days=1)
    trigger_tomorrow = datetime.combine(tomorrow_date, time(hour, minute), tzinfo=tz)
    return (trigger_tomorrow - now).total_seconds()
