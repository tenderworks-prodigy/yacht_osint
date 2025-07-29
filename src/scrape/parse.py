from __future__ import annotations

import logging
from typing import List
from urllib.parse import urljoin, urlparse

import feedfinder2
import feedparser
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

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


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1))
def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=10)
    log.info(
        "fetch %s -> %s %s", url, resp.status_code, resp.headers.get("content-type", "")
    )
    resp.raise_for_status()
    return resp.text


def _stage_link_rel(html: str, base: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    feeds: List[str] = []
    for link in soup.find_all("link", rel="alternate"):
        type_ = (link.get("type") or "").lower()
        if type_ in {"application/rss+xml", "application/atom+xml"}:
            href = link.get("href")
            if href:
                feeds.append(urljoin(base, href))
    return feeds


def _stage_anchor_heuristics(html: str, base: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    feeds: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(token in href.lower() for token in _ANCHOR_TOKENS):
            feeds.append(urljoin(base, href))
    return feeds


def _parse_feed(url: str) -> List[dict]:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:  # pragma: no cover - network failures
        log.warning("feed request failed for %s: %s", url, exc)
        return []
    parsed = feedparser.parse(resp.text)
    return list(parsed.entries)


def _probe_extensions(url: str) -> List[str]:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    return [root + ext for ext in _EXT_PROBES]


def probe_default_endpoints(url: str) -> List[str]:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    return [urljoin(root, ep) for ep in _DEFAULT_ENDPOINTS]


def discover_feeds(url: str) -> List[str]:
    """Return a list of valid feed URLs discovered on ``url``."""
    html = fetch_html(url)

    approaches = [
        ("link-rel", lambda: _stage_link_rel(html, url)),
        ("defaults", lambda: probe_default_endpoints(url)),
        ("anchors", lambda: _stage_anchor_heuristics(html, url)),
        ("feedfinder2", lambda: feedfinder2.find_feeds(url)),
        ("extensions", lambda: _probe_extensions(url)),
    ]

    for name, func in approaches:
        candidates = func()
        valid: List[str] = []
        for c in candidates:
            if _parse_feed(c):
                valid.append(c)
        if valid:
            log.info("%s succeeded with %s", name, valid)
            return valid

    return []


def run() -> None:  # pragma: no cover - manual invocation only
    log.info("stub")
