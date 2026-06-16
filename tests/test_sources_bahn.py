"""Tests for bahn source — config validation."""
from daily_briefing.sources.bahn import BahnSource


class TestBahnConfig:
    def test_missing_station_returns_error(self):
        """With no station configured, returns error instead of defaults."""
        source = BahnSource()
        result = source.fetch({"sources": {"bahn": {}}})
        assert result.is_success() is False
        assert "Bahn not configured" in result.error

    def test_station_from_env_var(self, monkeypatch):
        """Station can be configured via env var as fallback."""
        monkeypatch.setenv("BAHN_DEPARTURE_STATION", "8000105")
        source = BahnSource()
        # This will still fail because the API is unreachable in tests,
        # but should NOT hit the "not configured" error
        result = source.fetch({"sources": {"bahn": {}}})
        # Should not be "not configured" — goes further to API call
        assert "Bahn not configured" not in (result.error or "")
