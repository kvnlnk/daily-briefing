"""Tests for calendar timezone logic."""

import datetime
from zoneinfo import ZoneInfo

from daily_briefing.sources.calendar import (
    TZ_BERLIN,
    today_start_in_tz,
)


class TestTimezone:
    """Verify today_start is correct in both CET and CEST."""

    def test_cest_summer_boundary(self):
        """July should use CEST (UTC+2) midnights."""
        t = datetime.datetime(2026, 7, 16, 22, 0, tzinfo=datetime.timezone.utc)
        start = today_start_in_tz(t, TZ_BERLIN)
        assert start.hour == 0
        assert start.minute == 0
        assert start.utcoffset() == datetime.timedelta(hours=2)

    def test_cet_winter_boundary(self):
        """January should use CET (UTC+1) midnights."""
        t = datetime.datetime(2026, 1, 16, 23, 0, tzinfo=datetime.timezone.utc)
        start = today_start_in_tz(t, TZ_BERLIN)
        assert start.hour == 0
        assert start.minute == 0
        assert start.utcoffset() == datetime.timedelta(hours=1)
