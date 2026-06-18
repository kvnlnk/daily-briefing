"""Tests for daily_briefing.scheduler — seconds_until_next_run calculation."""
import zoneinfo
from datetime import datetime

import pytest

from daily_briefing.scheduler import seconds_until_next_run


class TestSecondsUntilNextRun:
    def test_before_trigger_same_day(self):
        """If now is 06:30 and trigger is 07:00, wait ~30 minutes."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now = datetime(2026, 6, 16, 6, 30, 0, tzinfo=tz)
        secs = seconds_until_next_run(now, "07:00", tz)
        assert secs == pytest.approx(30 * 60, abs=2)

    def test_after_trigger_wait_tomorrow(self):
        """If now is 08:00 and trigger is 07:00, wait ~23 hours."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now = datetime(2026, 6, 16, 8, 0, 0, tzinfo=tz)
        secs = seconds_until_next_run(now, "07:00", tz)
        assert secs == pytest.approx(23 * 3600, abs=2)

    def test_exactly_at_trigger(self):
        """If now is exactly 07:00:00, wait 24 hours."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now = datetime(2026, 6, 16, 7, 0, 0, tzinfo=tz)
        secs = seconds_until_next_run(now, "07:00", tz)
        assert secs == pytest.approx(24 * 3600, abs=2)

    def test_midnight_boundary(self):
        """Trigger at 00:00, now at 23:50 — wait 10 minutes."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now = datetime(2026, 6, 16, 23, 50, 0, tzinfo=tz)
        secs = seconds_until_next_run(now, "00:00", tz)
        assert secs == pytest.approx(10 * 60, abs=2)

    def test_dst_spring_forward_positive(self):
        """DST spring-forward: just verify positive and reasonable."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        # 2026-03-29 01:30 UTC = 02:30 CET, clock jumps to 03:30 CEST at 02:00 CET
        now_utc = datetime(2026, 3, 29, 1, 30, 0, tzinfo=zoneinfo.ZoneInfo("UTC"))
        now_berlin = now_utc.astimezone(tz)
        secs = seconds_until_next_run(now_berlin, "07:00", tz)
        assert 60 < secs < 6 * 3600

    def test_dst_fall_back_positive(self):
        """DST fall-back: just verify positive and reasonable."""
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        # 2026-10-25 01:30 UTC = 03:30 CEST, clock falls back to 03:00 CET at 03:00 CEST
        # Actually 01:30 UTC on 2026-10-25 = 03:30 CEST before fallback
        now_utc = datetime(2026, 10, 25, 1, 30, 0, tzinfo=zoneinfo.ZoneInfo("UTC"))
        now_berlin = now_utc.astimezone(tz)
        secs = seconds_until_next_run(now_berlin, "03:00", tz)
        assert 60 < secs < 4 * 3600
