"""
RSS feed discovery and parsing helpers.

This module attempts to discover RSS/Atom feeds for a given list of domains
and, when possible, parse the first *n* entries of each feed.  It relies on
``feedfinder2`` + ``feedparser`` + BeautifulSoup when they are available but
falls back to simple heuristics (HEAD <link> discovery and common path probes)
if those libraries are missing.  The goal is to keep the public interface
stable even in constrained environments where external packages may not be
installed.
"""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Iterable
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from src.common.browser_fetch import fetch_with_browser
from src.common.diagnostics import validate_io
from src.common.throttle import sleep

# ----------------------------------------------------------------------------
# Optional third‑party dependencies
# ----------------------------------------------------------------------------
try:
    import feedfinder2  # type: ignore
    from bs4 import BeautifulSoup  # type: ignore
except Exception:

    class _FeedFinder2Stub:  # type: ignore
        """Fallback stub when *feedfinder2* is unavailable."""

        @staticmethod
        def find_feeds(url: str) -> list[str]:
            return []

    feedfinder2 = _FeedFinder2Stub()  # type: ignore

    class _SimpleSoup:  # pylint: disable=too-few-public-methods
        def __init__(self, markup: str, *_: object, **__: object) -> None:  # noqa: D401
            self.markup = markup

        def find_all(self, *_: object, **__: object):  # pragma: no cover
            return []

    BeautifulSoup = _SimpleSoup  # type: ignore

try:
    import feedparser  # type: ignore
except Exception:

    class _FeedParserStub:  # type: ignore
        """Fallback stub when *feedparser* is unavailable."""

        @staticmethod
        def parse(_: str):  # noqa: D401
            return type("_Feed", (), {"entries": []})()

    feedparser = _FeedParserStub()  # type: ignore

# Ensure *feedfinder2* uses the same soup implementation to avoid warnings.
if hasattr(feedfinder2, "BeautifulSoup"):
    feedfinder2.BeautifulSoup = lambda markup, *a, **k: BeautifulSoup(
        markup, "lxml", *a, **k
    )  # type: ignore

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) " "Gecko/20100101 Firefox/117.0"
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

# ----------------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------------


def _normalize_domain(entry: str | dict) -> str | None:
    """Extract a valid domain/netloc from *entry* or return *None*."""
    domain: str | None = None
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


def _requests_fetch(url: str) -> tuple[bytes | None, int, str]:
    import requests  # type: ignore

    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
    return resp.content, resp.status_code, resp.headers.get("Content-Type", "")


def _get_html(url: str) -> tuple[bytes | None, int, str]:
    """Return *(body, status_code, content_type)* for *url*.

    Any failure is logged and re-raised so calling code fails fast.
    """
    try:
        sleep()
        body, status, ctype = _requests_fetch(url)
        if status in (403, 429) or b"cf-browser-verification" in (body or b""):
            body, status, ctype = fetch_with_browser(url)
        return body, status, ctype
    except Exception as exc:  # noqa: BLE001
        log.error("fatal in _get_html: %s", exc, exc_info=True)
        raise


class _FeedHTMLParser(HTMLParser):
    """Extract <link rel="alternate" …> pointing to feeds and count <a> tags."""

    def __init__(self, base_url: str) -> None:  # noqa: D401
        super().__init__()
        self.base_url = base_url
        self.feed_links: list[str] = []
        self.a_count = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ):  # type: ignore[override]
        tag = tag.lower()
        if tag == "a":
            self.a_count += 1
        elif tag == "link":
            attrs_dict = {k.lower(): v for k, v in attrs if v}
            rel = attrs_dict.get("rel", "").lower()
            type_ = attrs_dict.get("type", "").lower()
            href = attrs_dict.get("href")
            if not href:
                return
            if (
                "rss" in type_
                or "atom" in type_
                or "application/rss+xml" in type_
                or "application/atom+xml" in type_
                or rel == "alternate"
            ):
                self.feed_links.append(urljoin(self.base_url, href))


# ----------------------------------------------------------------------------
# Feed discovery helpers
# ----------------------------------------------------------------------------


def _discover_with_bs(base_url: str, html: str) -> list[str]:
    """Discover feeds using BeautifulSoup if available."""
    try:
        soup = BeautifulSoup(html, "lxml")  # type: ignore[arg-type]
        links: list[str] = []
        for link in soup.find_all("link"):
            rel = (link.get("rel") or "").lower()
            type_ = (link.get("type") or "").lower()
            href = link.get("href")
            if href and ("rss" in type_ or "atom" in type_ or rel == "alternate"):
                links.append(urljoin(base_url, href))
        return links
    except Exception:  # noqa: BLE001 – soup may be stub
        return []


def _fallback_feed_endpoints(base_url: str) -> list[str]:
    """Probe common *FALLBACK_PATHS* under *base_url*."""
    found: list[str] = []
    from urllib.request import urlopen  # late import to avoid ssl cost if unused

    for p in FALLBACK_PATHS:
        probe = urljoin(base_url, p)
        try:
            with urlopen(probe, timeout=5) as resp:  # type: ignore[attr-defined]
                content_type = resp.headers.get("Content-Type", "")
                if resp.status < 400 and content_type.startswith("application"):
                    found.append(probe)
        except Exception:  # noqa: BLE001
            continue
    return found


def _save_raw_html(domain: str, body: bytes):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{domain}.html").write_bytes(body)


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------


def discover_feeds(domains: Iterable[str]) -> dict[str, list[str]]:
    """Return mapping **domain → [feed URLs]**."""
    feeds: dict[str, list[str]] = {}
    for entry in domains:
        normalized = _normalize_domain(entry)
        if not normalized:
            continue

        base_url = f"https://{normalized}"
        html_bytes, _, _ = _get_html(base_url)
        html = html_bytes.decode("utf-8", "ignore") if html_bytes else ""

        found: list[str] = []
        if html:
            # Prefer *feedfinder2* if present.
            try:
                found = feedfinder2.find_feeds(base_url) or []  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                found = []

            # If still nothing, DIY parsing.
            if not found:
                # Try BeautifulSoup‑based discovery first.
                found = _discover_with_bs(base_url, html)

            if not found:
                # Fallback to cheap HTMLParser.
                parser = _FeedHTMLParser(base_url)
                parser.feed(html)
                found = parser.feed_links

        if not found:
            found = _fallback_feed_endpoints(base_url)
        if not found and html_bytes:
            _save_raw_html(normalized, html_bytes)

        if found:
            feeds[normalized] = found
    return feeds


@validate_io
def fetch_entries(feed_map: dict[str, list[str]], limit: int = 20) -> dict[str, list[dict]]:
    """Read up to *limit* entries per *feed_map* URL using *feedparser*."""
    results: dict[str, list[dict]] = {}
    for domain, urls in feed_map.items():
        collected: list[dict] = []
        random.shuffle(urls)
        for url in urls:
            try:
                d = feedparser.parse(url)  # type: ignore[attr-defined]
                entries = getattr(d, "entries", None)
                if entries is None and isinstance(d, dict):
                    entries = d.get("entries")
                if entries:
                    collected.extend(entries[:limit])
                    if len(collected) >= limit:
                        break
            except Exception as exc:  # noqa: BLE001
                log.warning("parse failed for %s: %s", url, exc)
        results[domain] = collected[:limit]
    return results


@validate_io
def run(domains: list[str]) -> dict[str, list[dict]]:
    feeds = discover_feeds(domains)
    if not feeds:
        raise ValueError("no feeds discovered")
    entries = fetch_entries(feeds)
    if any(len(v) == 0 for v in entries.values()):
        raise ValueError("no entries fetched for some domains")
    return entries


if __name__ == "__main__":  # pragma: no cover – manual debug entry point
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    domains_arg: list[str] = list(sys.argv[1:])
    data = run(domains_arg)
    out_path = Path("yacht_osint/data/cache/discovered_feeds.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, out_path.open("w"))
    log.info("saved feeds → %s", out_path)
