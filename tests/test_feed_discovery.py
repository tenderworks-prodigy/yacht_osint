from pathlib import Path

import vcr
import vcr.stubs

vcr.stubs.VCRHTTPResponse.version_string = "HTTP/1.1"

from src.scrape import parse


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
    monkeypatch.setattr(parse, "_stage_link_rel", tracker.stage("s1", ["a1"]))
    monkeypatch.setattr(
        parse, "_stage_anchor_heuristics", tracker.stage("s2", ["a1", "a2"])
    )
    monkeypatch.setattr(
        parse.feedfinder2, "find_feeds", tracker.stage("s3", ["a2", "a3"])
    )
    monkeypatch.setattr(parse, "probe_default_endpoints", tracker.stage("s4", ["a4"]))
    feeds = parse.discover_feeds("https://example.com")
    assert feeds == ["a1", "a2", "a3", "a4"]
    assert tracker.called == ["s1", "s2", "s3", "s4"]


vcr_inst = vcr.VCR(cassette_library_dir=str(Path(__file__).parent / "cassettes"))
vcr_inst.before_playback_response = (
    lambda r: setattr(r, "version_string", "HTTP/1.1") or r
)


@vcr_inst.use_cassette("rss.yaml")
def test_integration_rss():
    feeds = parse.discover_feeds("https://xkcd.com")
    assert any("rss" in f for f in feeds)


@vcr_inst.use_cassette("atom.yaml")
def test_integration_atom():
    feeds = parse.discover_feeds("https://blog.python.org")
    assert any("feeds" in f for f in feeds)


@vcr_inst.use_cassette("none.yaml")
def test_integration_none():
    feeds = parse.discover_feeds("https://example.com")
    assert feeds == []
