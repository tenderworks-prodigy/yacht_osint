from pathlib import Path

import vcr
import vcr.stubs
from src.scrape import parse

vcr.stubs.VCRHTTPResponse.version_string = "HTTP/1.1"


class CallTracker:
    def __init__(self):
        self.called = []

    def stage(self, name, ret):
        def _inner(*a, **k):
            self.called.append(name)
            return ret

        return _inner


def test_discover_feed_pipeline(monkeypatch):
    tracker = CallTracker()
    monkeypatch.setattr(parse, "fetch_html", lambda url: "<html></html>")
    monkeypatch.setattr(parse, "_stage_link_rel", tracker.stage("s1", []))
    monkeypatch.setattr(parse, "probe_default_endpoints", tracker.stage("s2", ["a1"]))
    monkeypatch.setattr(parse, "_stage_anchor_heuristics", tracker.stage("s3", ["a2"]))
    monkeypatch.setattr(parse.feedfinder2, "find_feeds", tracker.stage("s4", ["a3"]))
    monkeypatch.setattr(parse, "_probe_extensions", tracker.stage("s5", ["a4"]))
    monkeypatch.setattr(parse, "_parse_feed", lambda url: [1] if url == "a1" else [])
    feeds = parse.discover_feeds("https://example.com")
    assert feeds == ["a1"]
    assert tracker.called == ["s1", "s2"]


vcr_inst = vcr.VCR(cassette_library_dir=str(Path(__file__).parent / "cassettes"))
vcr_inst.before_playback_response = (
    lambda r: setattr(r, "version_string", "HTTP/1.1") or r
)


@vcr_inst.use_cassette("rss.yaml")
def test_integration_rss(monkeypatch):
    monkeypatch.setattr(
        parse,
        "fetch_html",
        lambda url: '<link rel="alternate" type="application/rss+xml" href="https://xkcd.com/rss.xml"/>',
    )
    feeds = parse.discover_feeds("https://xkcd.com")
    assert feeds == ["https://xkcd.com/rss.xml"]


@vcr_inst.use_cassette("atom.yaml")
def test_integration_atom(monkeypatch):
    monkeypatch.setattr(
        parse,
        "fetch_html",
        lambda url: '<link rel="alternate" type="application/atom+xml" href="https://blog.python.org/feeds/posts/default?alt=atom"/>',
    )
    feeds = parse.discover_feeds("https://blog.python.org")
    assert feeds == ["https://blog.python.org/feeds/posts/default?alt=atom"]


@vcr_inst.use_cassette("none.yaml")
def test_integration_none(monkeypatch):
    monkeypatch.setattr(parse, "fetch_html", lambda url: "<html></html>")
    feeds = parse.discover_feeds("https://example.com")
    assert feeds == []
