from __future__ import annotations

import logging
from typing import List
from urllib.parse import urljoin, urlparse

import feedfinder2
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

_ANCHOR_TOKENS = [".rss", ".xml", "/feed", "format=rss"]
_DEFAULT_ENDPOINTS = ["/feed", "/rss", "/atom", "/feeds/posts/default"]


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


def probe_default_endpoints(url: str) -> List[str]:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    feeds: List[str] = []
    for ep in _DEFAULT_ENDPOINTS:
        candidate = urljoin(root, ep)
        try:
            r = requests.head(candidate, allow_redirects=True, timeout=5)
            content_type = r.headers.get("content-type", "").lower()
            if r.status_code < 400 and "xml" in content_type:
                feeds.append(candidate)
                continue
            r = requests.get(candidate, allow_redirects=True, timeout=5)
            content_type = r.headers.get("content-type", "").lower()
            if r.status_code < 400 and "xml" in content_type:
                feeds.append(candidate)
        except Exception:  # pragma: no cover - network failures
            continue
    return feeds


def discover_feeds(url: str) -> List[str]:
    """Return a list of feed URLs discovered on ``url``."""
    html = fetch_html(url)
    feeds: set[str] = set()

    stage1 = _stage_link_rel(html, url)
    feeds.update(stage1)
    print("[1] link-rel feeds:", stage1)

    stage2 = _stage_anchor_heuristics(html, url)
    feeds.update(stage2)
    print("[2] anchor heuristics:", stage2)

    stage3 = feedfinder2.find_feeds(html)
    feeds.update(stage3)
    print("[3] feedfinder2:", stage3)

    stage4 = probe_default_endpoints(url)
    feeds.update(stage4)
    print("[4] default endpoints:", stage4)

    print("[5] first 200 chars of HTML:", repr(html[:200]))

    return sorted(feeds)


def run() -> None:  # pragma: no cover - manual invocation only
    log.info("stub")
