import requests
from src.scrape import parse


class DummyResp:
    def __init__(self, text="", status=200, headers=None, url="https://example.com/"):
        self.text = text
        self.status_code = status
        self.headers = headers or {"content-type": "text/html"}
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(self.status_code)


def test_link_and_anchor(monkeypatch):
    html = """<html><head><link rel='alternate' type='application/rss+xml' href='/feed.xml'></head><body><a href='feed.xml'>feed</a></body></html>"""
    monkeypatch.setattr(requests, "get", lambda *a, **k: DummyResp(html))
    feeds = parse.discover_feeds("https://example.com")
    assert feeds == ["https://example.com/feed.xml"]


def test_feedfinder_fallback(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: DummyResp(""))
    monkeypatch.setattr(
        parse.feedfinder2, "find_feeds", lambda html: ["https://example.com/rss"]
    )
    feeds = parse.discover_feeds("https://example.com")
    assert feeds == ["https://example.com/rss"]


def test_default_endpoint(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: DummyResp("<html></html>"))
    head_resp = DummyResp("", headers={"content-type": "application/rss+xml"})
    monkeypatch.setattr(requests, "head", lambda *a, **k: head_resp)
    monkeypatch.setattr(parse.feedfinder2, "find_feeds", lambda html: [])
    feeds = parse.discover_feeds("https://example.com/blog")
    assert feeds == ["https://example.com/feed"]


def test_no_feeds(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: DummyResp("<html></html>"))
    monkeypatch.setattr(requests, "head", lambda *a, **k: DummyResp(status=404))
    monkeypatch.setattr(parse.feedfinder2, "find_feeds", lambda html: [])
    feeds = parse.discover_feeds("https://example.com")
    assert feeds == []
