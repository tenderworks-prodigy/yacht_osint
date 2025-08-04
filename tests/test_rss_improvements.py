"""Additional tests for improved RSS feed discovery and parsing logic."""

from __future__ import annotations

from src.scrape import rss


def test_discover_feeds_with_dicts(monkeypatch):
    # feedfinder2 should be invoked with the normalized host
    monkeypatch.setattr("feedfinder2.find_feeds", lambda url: [f"{url}/feed"])
    feeds = rss.discover_feeds([{"domain": "example.com", "timestamp": 1}])
    assert "example.com" in feeds
    assert feeds["example.com"] == ["https://example.com/feed"]


def test_discover_feeds_skips_invalid(monkeypatch):
    monkeypatch.setattr("feedfinder2.find_feeds", lambda url: [f"{url}/feed"])
    # garbage or missing domain entries should be ignored
    feeds = rss.discover_feeds(["", None, {"foo": "bar"}])
    assert feeds == {}
