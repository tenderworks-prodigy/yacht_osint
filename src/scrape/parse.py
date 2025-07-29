from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import feedfinder2
import feedparser
import requests
import vcr
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from src.sensors import sensor

log = logging.getLogger(__name__)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

_ANCHOR_TOKENS = ["feed", "rss", "atom"]
_DEFAULT_ENDPOINTS = [
    "/feed",
    "/rss",
    "/feeds/posts/default?alt=atom",
    "/feeds/posts/default?alt=rss",
]
_EXT_PROBES = [".xml", ".rss"]


@sensor("scrape")
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1))
def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=10)
    log.info("fetch %s -> %s %s", url, resp.status_code, resp.headers.get("content-type", ""))
    resp.raise_for_status()
    return resp.text


def _stage_link_rel(html: str, base: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    feeds: list[str] = []
    for link in soup.find_all("link", rel="alternate"):
        type_ = (link.get("type") or "").lower()
        if type_ in {"application/rss+xml", "application/atom+xml"}:
            href = link.get("href")
            if href:
                feeds.append(urljoin(base, href))
    return feeds


def _stage_anchor_heuristics(html: str, base: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    feeds: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(token in href.lower() for token in _ANCHOR_TOKENS):
            feeds.append(urljoin(base, href))
    return feeds


def _parse_feed(url: str) -> list[dict]:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:  # pragma: no cover - network failures
        log.warning("feed request failed for %s: %s", url, exc)
        return []
    parsed = feedparser.parse(resp.text)
    return list(parsed.entries)


def _probe_extensions(url: str) -> list[str]:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    return [root + ext for ext in _EXT_PROBES]


def _validate_feed(url: str) -> bool:
    try:
        resp = requests.get(url, timeout=8)
        return 200 <= resp.status_code < 400
    except Exception as e:  # pragma: no cover - network errors
        log.warning("feed validation failed: %s \u2013 keeping URL", e)
        return True


@sensor("scrape")
def probe_default_endpoints(url: str) -> list[str]:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    return [urljoin(root, ep) for ep in _DEFAULT_ENDPOINTS]


@sensor("scrape")
def discover_feeds(url: str) -> list[str]:
    """Return a list of valid feed URLs discovered on ``url``."""
    html = fetch_html(url)

    approaches = [
        ("link-rel", lambda: _stage_link_rel(html, url)),
        ("defaults", lambda: probe_default_endpoints(url)),
        ("anchors", lambda: _stage_anchor_heuristics(html, url)),
        ("feedfinder2", lambda: feedfinder2.find_feeds(url)),
        ("extensions", lambda: _probe_extensions(url)),
    ]

    seen: set[str] = set()
    for name, func in approaches:
        candidates = func()
        valid: list[str] = []
        for c in candidates:
            if c in seen:
                continue
            seen.add(c)
            if getattr(vcr, "mode", None) is None and not _validate_feed(c):
                continue
            valid.append(c)
        if valid:
            log.info("%s succeeded with %s", name, valid)
            return valid

    return []


@sensor("scrape")
def run() -> None:  # pragma: no cover - manual invocation only
    log.info("stub")
