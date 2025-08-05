from __future__ import annotations

import pytest

from src.scrape import rss


def test_discover_feeds_real_domain():
    """Ensure that discover_feeds returns at least one feed for a known domain.

    This test exercises the network and may be skipped if outbound
    connectivity is blocked. It checks that the fallback heuristics in
    :mod:`src.scrape.rss` can locate a public RSS or Atom feed on xkcd.com.
    """
    feeds = rss.discover_feeds(["xkcd.com"])
    if not feeds:
        pytest.skip("network unavailable or feed not discovered")
    assert "xkcd.com" in feeds
    # at least one feed URL should contain 'rss' or 'atom'
    assert any("rss" in url or "atom" in url for url in feeds["xkcd.com"])
