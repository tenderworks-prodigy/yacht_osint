from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import feedfinder2
import feedparser
from bs4 import BeautifulSoup

# silence feedfinder2 warnings by forcing the lxml parser
feedfinder2.BeautifulSoup = lambda markup, *a, **k: BeautifulSoup(markup, "lxml", *a, **k)

log = logging.getLogger(__name__)


def _normalize_domain(entry: str | dict) -> str | None:
    """Extract and validate domain string from input that may be a dict or string."""
    domain = None
    if isinstance(entry, dict):
        domain = entry.get("domain")
    elif isinstance(entry, str):
        domain = entry
    if not domain:
        return None
    parsed = urlparse(f"https://{domain}" if "://" not in domain else domain)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        log.warning("skipping invalid domain during RSS discovery: %s", entry)
        return None
    # strip scheme if present, keep just host
    return parsed.netloc


def discover_feeds(domains: list[str]) -> dict[str, list[str]]:
    feeds: dict[str, list[str]] = {}
    for entry in domains:
        normalized = _normalize_domain(entry)
        if not normalized:
            continue
        base_url = f"https://{normalized}"
        try:
            found = feedfinder2.find_feeds(base_url)
            if found:
                feeds[normalized] = found
        except Exception as exc:  # pragma: no cover - logging
            log.warning("feed discovery failed for %s: %s", normalized, exc)
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


def run(domains: list[str]) -> dict[str, list[dict]]:
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
