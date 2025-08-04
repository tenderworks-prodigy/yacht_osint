from __future__ import annotations

"""
RSS feed discovery and parsing helpers.

This module originally relied on external libraries such as ``feedfinder2``,
``feedparser`` and BeautifulSoup. In constrained execution environments these
dependencies may be unavailable, so the import is now guarded. When the
libraries are missing, a minimal stub implementation is provided to maintain
backwards compatibility with test suites that monkey‑patch these symbols. The
fallback discovery logic below also includes additional heuristics and
diagnostics to improve the feed discovery rate and assist with debugging.
"""

import json
import logging
import random
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urljoin, urlparse

# Attempt to import optional dependencies. These are wrapped in a try/except so
# that the module can still load even if the packages are not installed. When
# missing, a simple stub with no‑op methods is substituted. Tests that
# monkey‑patch ``feedfinder2.find_feeds`` will continue to work because the
# attribute exists on the stub.
try:
    import feedfinder2  # type: ignore
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    class _FeedFinder2Stub:  # type: ignore
        """Fallback stub for feedfinder2 when the library is not available."""

        @staticmethod
        def find_feeds(url: str) -> list[str]:
            return []

    feedfinder2 = _FeedFinder2Stub()  # type: ignore

    class _SimpleSoup:
        def __init__(self, markup: str, parser: str | None = None, *_, **__):
            self.markup = markup

        def find_all(self, *_, **__):  # pragma: no cover - never used directly
            return []

    BeautifulSoup = _SimpleSoup  # type: ignore

try:
    import feedparser  # type: ignore
except Exception:
    class _FeedParserStub:  # type: ignore
        """Fallback stub for feedparser when the library is not available."""

        @staticmethod
        def parse(url: str):
            return type("_Feed", (), {"entries": []})()

    feedparser = _FeedParserStub()  # type: ignore

# If feedfinder2 was successfully imported, monkey‑patch it to use a stable
# parser. This suppresses warnings and ensures consistent behaviour when
# BeautifulSoup is present.
if hasattr(feedfinder2, "BeautifulSoup"):
    feedfinder2.BeautifulSoup = lambda markup, *a, **k: BeautifulSoup(markup, "lxml", *a, **k)

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Networking helpers
# ----------------------------------------------------------------------------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) "
        "Gecko/20100101 Firefox/117.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

FALLBACK_PATHS: tuple[str, ...] = (
    "feed",
    "rss",
    "rss.xml",
    "atom.xml",
    ".rss",
)

RAW_DIR = Path("diagnostics/raw")


def _normalize_domain(entry: str | dict) -> Optional[str]:
    """Extract and validate a domain string from an input entry."""
    domain: Optional[str] = None
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
    return parsed.netloc


def _get_html(url: str) -> tuple[Optional[bytes], int, str]:
    """Fetch a URL and return the raw body, status and content type."""
    try:
        import requests  # type: ignore
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
            return resp.content, resp.status_code, resp.headers.get("Content-Type", "")
        except Exception as exc:
            log.warning("request failed for %s: %s", url, exc)
            return None, 0, ""
    except Exception:
        from urllib.request import Request, urlopen
        try:
            req = Request(url, headers=DEFAULT_HEADERS)
            with urlopen(req, timeout=10) as resp:  # type: ignore[attr-defined]
                body: bytes = resp.read()
                status: int = getattr(resp, "status", 0)
                content_type: str = resp.headers.get("Content-Type", "")
                return body, status, content_type
        except Exception as exc:
            log.warning("request failed for %s: %s", url, exc)
            return None, 0, ""


class _FeedHTMLParser(HTMLParser):
    """Simple HTML parser that extracts <link> feed URLs and counts <a> tags."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.feed_links: list[str] = []
        self.a_count: int = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self.a_count += 1
        elif tag.lower() == "link":
            attr_dict = {k.lower(): (v or "") for k, v in attrs}
            rel = attr_dict.get("rel", "").lower()
            type_attr = attr_dict.get("type", "").lower()
            if "alternate" in rel and ("rss" in type_attr or "atom" in type_attr):
                href = attr_dict.get("href")
                if href:
                    self.feed_links.append(urljoin(self.base_url, href))


def _parse_homepage_for_feeds(base_url: str) -> tuple[list[str], int, bytes, int, str]:
    html, status, content_type = _get_html(base_url)
    if not html:
        return [], 0, b"", status, content_type
    parser = _FeedHTMLParser(base_url)
    try:
        parser.feed(html.decode(errors="ignore"))
    except Exception:
        pass
    return parser.feed_links, parser.a_count, html, status, content_type


def _fallback_feed_endpoints(base_url: str) -> list[str]:
    feeds: list[str] = []
    for i, path in enumerate(FALLBACK_PATHS):
        url = base_url.rstrip("/") + "/" + path
        html, status, content_type = _get_html(url)
        log.info(
            "fallback attempt %s/%s: %s status=%s content_type=%s",
            i + 1,
            len(FALLBACK_PATHS),
            url,
            status,
            content_type,
        )
        if html and 200 <= status < 300 and "xml" in (content_type or "").lower():
            feeds.append(url)
            break
        time.sleep(0.5 + random.random() * 0.2)
    return feeds


def _save_raw_html(domain: str, html: bytes) -> None:
    try:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_DIR / f"{domain}.html"
        with path.open("wb") as f:
            f.write(html)
    except Exception:
        log.warning("failed to save raw HTML for %s", domain)


def discover_feeds(domains: Iterable[str]) -> dict[str, list[str]]:
    feeds: dict[str, list[str]] = {}
    for entry in domains:
        normalized = _normalize_domain(entry)
        if not normalized:
            continue
        base_url = f"https://{normalized}"
        found: list[str] = []
        try:
            found = feedfinder2.find_feeds(base_url) or []  # type: ignore
        except Exception as exc:
            log.warning("feedfinder2 discovery failed for %s: %s", normalized, exc)
            found = []
        if not found:
            feed_links, a_count, html, status, content_type = _parse_homepage_for_feeds(base_url)
            log.info(
                json.dumps(
                    {
                        "domain": normalized,
                        "status": status,
                        "content_type": content_type,
                        "feed_link_count": len(feed_links),
                        "a_tag_count": a_count,
                    }
                )
            )
            found = feed_links
            if not found:
                found = _fallback_feed_endpoints(base_url)
            if not found and html:
                _save_raw_html(normalized, html)
        if found:
            feeds[normalized] = found
    return feeds


def fetch_entries(feed_map: dict[str, list[str]], limit: int = 20) -> dict[str, list[dict]]:
    results: dict[str, list[dict]] = {}
    for domain, urls in feed_map.items():
        results[domain] = []
        for url in urls:
            try:
                d = feedparser.parse(url)  # type: ignore[attr-defined]
                entries = getattr(d, "entries", []) or (d.get("entries") if isinstance(d, dict) else [])
                results[domain].extend(entries[:limit])
            except Exception as exc:
                log.warning("parse failed for %s: %s", url, exc)
    return results


def run(domains: List[str]) -> dict[str, list[dict]]:
    feeds = discover_feeds(domains)
    return fetch_entries(feeds)


if __name__ == "__main__":
    import sys
    domains: list[str] = list(sys.argv[1:])
    data = run(domains)
    out = Path("yacht_osint/data/cache/discovered_feeds.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, out.open("w"))
    log.info("saved feeds → %s", out)
