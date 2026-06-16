"""Tests for news source - timeout and User-Agent."""
from unittest.mock import patch, Mock
import pytest
from daily_briefing.sources.news import NewsSource


class TestNewsTimeout:
    def test_fetch_feed_uses_requests_with_timeout(self):
        """_fetch_feed should use requests.get with timeout=10 and User-Agent."""
        source = NewsSource()
        with patch("daily_briefing.sources.news.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = b'<?xml version="1.0"?><rss version="2.0"><channel><title>Test</title></channel></rss>'
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            with patch("daily_briefing.sources.news.feedparser.parse") as mock_parse:
                mock_parse.return_value.bozo = False
                mock_parse.return_value.entries = []
                mock_parse.return_value.feed = {"title": "Test"}

                source._fetch_feed("https://example.com/feed.xml")

                call_kwargs = mock_get.call_args[1]
                assert "timeout" in call_kwargs, "No timeout set on requests.get!"
                assert call_kwargs["timeout"] == 10, "Timeout should be 10s"
                headers = call_kwargs.get("headers", {})
                assert "User-Agent" in headers, "No User-Agent header!"
