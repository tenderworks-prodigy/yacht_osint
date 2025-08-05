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

import feedfinder2
import feedparser
from bs4 import BeautifulSoup

from src.common.diagnostics import validate_io

# Ensure *feedfinder2* uses the same soup implementation to avoid warnings.
if hasattr(feedfinder2, "BeautifulSoup"):
    feedfinder2.BeautifulSoup = lambda markup, *a, **k: BeautifulSoup(markup, "lxml", *a, **k)

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
    "feed.xml",
    "index.xml",
    "feeds/posts/default",
    "feed.json",
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


def _get_html(url: str) -> tuple[bytes, int, str]:
    """Return *(body, status_code, content_type)* for *url*.

    Any failure is logged and re-raised so calling code fails fast.
    """
    try:
        import requests  # type: ignore

        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        return resp.content, resp.status_code, resp.headers.get("Content-Type", "")
    except Exception as exc:  # noqa: BLE001
        log.error("fatal in _get_html: %s", exc, exc_info=True)
        raise


def _is_feed_url(url: str) -> bool:
    """Return True if *url* appears to be a feed endpoint."""
    from urllib.request import urlopen

    try:
        with urlopen(url, timeout=5) as resp:  # type: ignore[attr-defined]
            ct = resp.headers.get("Content-Type", "")
            if resp.status >= 400:
                log.debug("reject %s status=%s", url, resp.status)
                return False
            if not ct.startswith("application"):
                log.debug("reject %s content-type=%s", url, ct)
                return False
    except Exception as exc:  # noqa: BLE001
        log.debug("reject %s error=%s", url, exc)
        return False
    return True


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
            candidate = urljoin(self.base_url, href)
            if (
                rel == "alternate"
                or type_.startswith("application/rss+xml")
                or type_.startswith("application/atom+xml")
                or type_.startswith("application/feed+json")
                or "rss" in type_
                or "atom" in type_
            ):
                if _is_feed_url(candidate):
                    self.feed_links.append(candidate)


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
            if href and (
                "rss" in type_
                or "atom" in type_
                or type_.startswith("application/rss+xml")
                or type_.startswith("application/atom+xml")
                or type_.startswith("application/feed+json")
                or rel == "alternate"
            ):
                candidate = urljoin(base_url, href)
                if _is_feed_url(candidate):
                    links.append(candidate)

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
            except Exception:  # pragma: no cover - invalid JSON
                continue

            def _extract(obj):
                if isinstance(obj, str) and "feed" in obj:
                    cand = urljoin(base_url, obj)
                    if _is_feed_url(cand):
                        links.append(cand)
                elif isinstance(obj, dict):
                    for v in obj.values():
                        _extract(v)
                elif isinstance(obj, list):
                    for item in obj:
                        _extract(item)

            _extract(data)

        return links
    except Exception:  # noqa: BLE001 – soup may be stub
        return []


def _fallback_feed_endpoints(base_url: str) -> list[str]:
    """Probe common *FALLBACK_PATHS* under *base_url*."""
    found: list[str] = []
    for p in FALLBACK_PATHS:
        probe = urljoin(base_url, p)
        if _is_feed_url(probe):
            found.append(probe)
    return found


def _save_raw_html(domain: str, body: bytes):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{domain}.html").write_bytes(body)


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------


@validate_io
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
            try:
                found = feedfinder2.find_feeds(base_url) or []
            except Exception:  # noqa: BLE001
                found = []

            extra = _discover_with_bs(base_url, html)
            if extra:
                found.extend(extra)

            if not found:
                parser = _FeedHTMLParser(base_url)
                parser.feed(html)
                found = parser.feed_links

        if not found:
            found = _fallback_feed_endpoints(base_url)
        if not found and html_bytes:
            _save_raw_html(normalized, html_bytes)

        if found:
            unique: list[str] = []
            seen: set[str] = set()
            for url in found:
                norm = urlparse(url)._replace(query="", fragment="").geturl()
                if norm not in seen:
                    seen.add(norm)
                    unique.append(norm)
            feeds[normalized] = unique
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
