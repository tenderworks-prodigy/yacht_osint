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
    monkeypatch.setattr(parse, "_validate_feed", lambda url: url == "a1")
    feeds = parse.discover_feeds("https://example.com")
    assert feeds == ["a1"]
    assert tracker.called == ["s1", "s2"]


vcr_inst = vcr.VCR(
    cassette_library_dir=str(Path(__file__).parent / "fixtures"),
    path_transformer=vcr.VCR.ensure_suffix(".yaml.gz"),
    record_mode="once",
)
vcr_inst.before_playback_response = lambda r: setattr(r, "version_string", "HTTP/1.1") or r


@vcr_inst.use_cassette("rss")
def test_integration_rss():
    feeds = parse.discover_feeds("https://xkcd.com")
    assert "https://xkcd.com/rss.xml" in feeds


@vcr_inst.use_cassette("atom")
def test_integration_atom():
    feeds = parse.discover_feeds("https://blog.python.org")
    assert feeds[0].startswith("https://blog.python.org/feeds/posts")


@vcr_inst.use_cassette("none")
def test_integration_none():
    feeds = parse.discover_feeds("https://example.com")
    assert feeds[0].startswith("https://example.com")
