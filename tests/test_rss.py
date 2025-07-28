from src.scrape import rss


def test_discover_feeds(monkeypatch):
    monkeypatch.setattr("feedfinder2.find_feeds", lambda url: [f"{url}/feed"])
    feeds = rss.discover_feeds(["example.com"])
    assert feeds == {"example.com": ["https://example.com/feed"]}
