"""Tests for reddit source — config validation."""
from daily_briefing.sources.reddit import RedditSource


class TestRedditConfig:
    def test_missing_subreddits_returns_error(self):
        """With no subreddits configured, returns error instead of defaults."""
        source = RedditSource()
        result = source.fetch({"sources": {"reddit": {}}})
        assert result.is_success() is False
        assert "No subreddits configured" in result.error
