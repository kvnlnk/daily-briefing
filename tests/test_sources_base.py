"""Tests for daily_briefing.sources.base — SourceResult + SourceProtocol."""

from daily_briefing.sources.base import SourceProtocol, SourceResult


class TestSourceResult:
    def test_success(self):
        r = SourceResult(name="test", priority=10, data={"key": "val"})
        assert r.is_success() is True
        assert r.error is None

    def test_error(self):
        r = SourceResult(name="test", priority=10, error="Something broke")
        assert r.is_success() is False
        assert r.error == "Something broke"

    def test_sort_key(self):
        a = SourceResult(name="a", priority=10, data={})
        b = SourceResult(name="b", priority=20, data={})
        c = SourceResult(name="c", priority=5, data={})
        sorted_list = sorted([a, b, c], key=lambda r: r.priority)
        assert [r.name for r in sorted_list] == ["c", "a", "b"]


class DummySource(SourceProtocol):
    """Minimal concrete source for testing the protocol."""
    name = "dummy"

    def fetch(self, config):
        return SourceResult(
            name=self.name,
            priority=50,
            data={"hello": "world"},
        )


class TestSourceProtocol:
    def test_name(self):
        src = DummySource()
        assert src.name == "dummy"

    def test_fetch_returns_result(self):
        src = DummySource()
        result = src.fetch({})
        assert isinstance(result, SourceResult)
        assert result.is_success()
        assert result.data == {"hello": "world"}
