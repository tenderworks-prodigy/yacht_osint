from __future__ import annotations

import logging
from typing import List
from urllib.parse import urljoin, urlparse

import feedfinder2
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

_ANCHOR_TOKENS = [".rss", ".xml", "/feed", "format=rss"]
_DEFAULT_ENDPOINTS = ["/feed", "/rss", "/atom", "/feeds/posts/default"]


def discover_feeds(url: str) -> List[str]:
    """Return a list of feed URLs discovered on ``url``."""

    def _fetch(u: str) -> tuple[str, str]:
        try:
            resp = requests.get(u, timeout=10)
            resp.raise_for_status()
            return resp.text, resp.url
        except Exception as exc:  # pragma: no cover - network failures
            log.warning("request failed for %s: %s", u, exc)
            return "", u

    html, final_url = _fetch(url)
    feeds: List[str] = []

    if html:
        soup = BeautifulSoup(html, "lxml")
        # <link rel="alternate" type="application/rss+xml" href="...">
        for link in soup.find_all("link", rel="alternate"):
            type_ = (link.get("type") or "").lower()
            if type_ in {"application/rss+xml", "application/atom+xml"}:
                href = link.get("href")
                if href:
                    feeds.append(urljoin(final_url, href))
        # <a href="...rss"> or similar heuristics
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(token in href.lower() for token in _ANCHOR_TOKENS):
                feeds.append(urljoin(final_url, href))

    # feedfinder2 fallback
    if not feeds:
        try:
            found = feedfinder2.find_feeds(html or final_url)
            feeds.extend(found)
        except Exception as exc:  # pragma: no cover - library failures
            log.debug("feedfinder2 failed for %s: %s", url, exc)

    # default endpoints like /feed or /rss
    if not feeds:
        parsed = urlparse(final_url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        for ep in _DEFAULT_ENDPOINTS:
            candidate = urljoin(root, ep)
            try:
                r = requests.head(candidate, allow_redirects=True, timeout=5)
                content_type = r.headers.get("content-type", "").lower()
                if r.status_code >= 400 or "xml" not in content_type:
                    r = requests.get(candidate, allow_redirects=True, timeout=5)
                    content_type = r.headers.get("content-type", "").lower()
                if r.status_code < 400 and "xml" in content_type:
                    feeds.append(candidate)
                    break
            except Exception:  # pragma: no cover - network failures
                continue

    if not feeds and html:
        log.debug("HTML snippet for %s: %s", url, html[:500])

    # deduplicate while preserving order
    return list(dict.fromkeys(feeds))


def run() -> None:  # pragma: no cover - manual invocation only
    log.info("stub")
