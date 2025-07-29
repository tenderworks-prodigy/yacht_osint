from __future__ import annotations

import json
import logging
from pathlib import Path

import feedfinder2
import feedparser
from bs4 import BeautifulSoup

from typing import list

# silence feedfinder2 warnings by forcing the lxml parser
feedfinder2.BeautifulSoup = lambda markup, *a, **k: BeautifulSoup(markup, "lxml", *a, **k)

log = logging.getLogger(__name__)


def discover_feeds(domains: list[str]) -> dict[str, List[str]]:
    feeds: dict[str, list[str]] = {}
    for domain in domains:
        url = f"https://{domain}"
        try:
            found = feedfinder2.find_feeds(url)
            if found:
                feeds[domain] = found
        except Exception as exc:  # pragma: no cover - logging
            log.warning("feed discovery failed for %s: %s", domain, exc)
    return feeds


def fetch_entries(feed_map: dict[str, list[str]], limit: int = 20) -> dict[str, list[dict]]:
    results: dict[str, list[dict]] = {}
    for domain, urls in feed_map.items():
        results[domain] = []
        for url in urls:
            try:
                d = feedparser.parse(url)
                results[domain].extend(d.entries[:limit])
            except Exception as exc:  # pragma: no cover - logging
                log.warning("parse failed for %s: %s", url, exc)
    return results


def run(domains: list[str]) -> dict[str, List[dict]]:
    feeds = discover_feeds(domains)
    return fetch_entries(feeds)


if __name__ == "__main__":  # pragma: no cover - manual runs
    import sys

    domains = sys.argv[1:]
    data = run(domains)
    out = Path("yacht_osint/data/cache/discovered_feeds.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, out.open("w"))
    log.info("saved feeds → %s", out)
