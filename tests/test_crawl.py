import logging
from types import SimpleNamespace

import pytest

from src.scrape import crawl


def test_crawl_builds_url(monkeypatch):
    called = []

    def fake_get(url, *a, **k):  # pragma: no cover - simple stub
        called.append(url)
        return SimpleNamespace(status_code=200)

    monkeypatch.setattr(crawl.requests, "get", fake_get)
    feeds = [{"domain": "example.com", "timestamp": 12345}]
    crawl.run(feeds)
    assert called == ["https://example.com"]


def test_validate_feeds():
    feeds = [{"domain": "x.com", "timestamp": 1}]
    assert crawl.validate_feeds(feeds) == feeds
    with pytest.raises(ValueError):
        crawl.validate_feeds([{"timestamp": 1}])


def test_crawl_skips_invalid(monkeypatch, caplog):
    monkeypatch.setattr(crawl.requests, "get", lambda *a, **k: None)
    caplog.set_level(logging.WARNING)
    crawl.run([{"timestamp": 1}, "nope"])
    assert "invalid feed entry skipped" in caplog.text
