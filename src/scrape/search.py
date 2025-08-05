from __future__ import annotations

import logging
import os
import random
import time

import requests
from tenacity import retry, stop_after_attempt, wait_random_exponential

from src.common.diagnostics import validate_io

# Attempt to import tldextract, which provides accurate domain parsing. In
# restricted environments this library may be unavailable; in that case fall
# back to a simple parser using urllib.parse. The fallback returns the host
# component of the URL which is sufficient for de‑duplication in the search
# module. Tests that monkey‑patch tldextract.extract will continue to work
# because the attribute exists on the stub.
try:
    import tldextract  # type: ignore
except Exception:
    from urllib.parse import urlparse

    class _TldExtractStub:
        class ExtractResult:
            def __init__(self, domain: str, suffix: str) -> None:
                self.domain = domain
                self.suffix = suffix

        @staticmethod
        def extract(url: str) -> ExtractResult:
            parsed = urlparse(url)
            host = parsed.netloc
            # strip port
            if ":" in host:
                host = host.split(":", 1)[0]
            parts = host.split(".")
            if len(parts) >= 2:
                domain = parts[-2]
                suffix = parts[-1]
            elif parts:
                domain = parts[0]
                suffix = ""
            else:
                domain = ""
                suffix = ""
            return _TldExtractStub.ExtractResult(domain, suffix)

    tldextract = _TldExtractStub()  # type: ignore

from src.common.env import require_env

log = logging.getLogger(__name__)
CSE_URL = "https://www.googleapis.com/customsearch/v1"

# retry configuration can be tweaked via environment variables
MAX_RETRIES = int(os.environ.get("CSE_RETRIES", "3"))
BACKOFF_BASE = float(os.environ.get("CSE_BACKOFF", "1"))
MAX_CONSECUTIVE = int(os.environ.get("CSE_MAX_CONSECUTIVE", "5"))

# counter for circuit breaker
_consecutive_429s = 0


@retry(
    reraise=True,
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_random_exponential(multiplier=BACKOFF_BASE),
)
def _cse_request(params: dict) -> requests.Response:
    resp = requests.get(CSE_URL, params=params, timeout=10)
    if resp.status_code == 429:
        raise requests.RequestException("429")
    resp.raise_for_status()
    return resp


def _search_google(query: str, num: int = 10) -> list[str]:
    """Query Google CSE and return root domains."""
    global _consecutive_429s

    if _consecutive_429s >= MAX_CONSECUTIVE:
        log.warning("skipping search due to repeated rate limits")
        return []

    key = require_env("GOOGLE_CSE_API_KEY")
    cx = require_env("GOOGLE_CSE_CX")
    assert key and cx, "GOOGLE_CSE_* must be set"

    try:
        resp = _cse_request({"key": key, "cx": cx, "q": query, "num": num})
        _consecutive_429s = 0
    except requests.RequestException as exc:  # pragma: no cover - network errors
        if "429" in str(exc):
            _consecutive_429s += 1
            if _consecutive_429s > 3:
                delay = random.uniform(1, 3)
                log.warning(
                    "rate limit persisted %s times; sleeping %.2fs", _consecutive_429s, delay
                )
                time.sleep(delay)
            return []
        log.error("fatal in _search_google: %s", exc, exc_info=True)
        raise

    payload = resp.json()
    domains: list[str] = []
    for item in payload.get("items", []):
        url = item.get("link")
        if not url:
            continue
        ext = tldextract.extract(url)
        domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def _search_bing(query: str, num: int = 10) -> list[str]:
    """Placeholder Bing search via API."""
    api_key = os.environ.get("BING_API_KEY")
    if not api_key:
        return []
    # minimal stub using same payload structure
    url = os.environ.get("BING_API_URL", "https://api.bing.microsoft.com/v7.0/search")
    try:
        resp = requests.get(
            url,
            params={"q": query, "count": num},
            headers={"Ocp-Apim-Subscription-Key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.error("fatal in _search_bing: %s", exc, exc_info=True)
        raise
    links = [
        item.get("url") for item in data.get("webPages", {}).get("value", []) if item.get("url")
    ]
    domains = []
    for url in links:
        ext = tldextract.extract(url)
        domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def _search_duckduckgo(query: str, num: int = 10) -> list[str]:
    api_url = os.environ.get("DDG_API_URL")
    if not api_url:
        return []
    try:
        resp = requests.get(
            api_url,
            params={"q": query, "format": "json", "no_redirect": 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.error("fatal in _search_duckduckgo: %s", exc, exc_info=True)
        raise

    links = [r.get("firstURL") for r in data.get("RelatedTopics", []) if r.get("firstURL")]

    domains = []
    for url in links[:num]:
        ext = tldextract.extract(url)
        domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def search_sites(query: str, num: int = 10) -> list[str]:
    results: list[str] = []
    results.extend(_search_google(query, num))
    results.extend(_search_bing(query, num))
    results.extend(_search_duckduckgo(query, num))
    return list(dict.fromkeys(results))


@validate_io
def run(queries: list[str], num: int = 10) -> list[dict]:
    results: list[dict] = []
    for q in queries:
        try:
            domains = search_sites(q, num)
        except Exception as exc:  # pragma: no cover - logging
            log.warning("search failed for %s: %s", q, exc)
            domains = []
        ts = int(time.time())
        for d in domains:
            results.append({"domain": d, "timestamp": ts})
    deduped: dict[str, dict] = {}
    for item in results:
        deduped[item["domain"]] = item
    out = list(deduped.values())
    log.info("\u2705 %d queries, %d unique domains", len(queries), len(out))
    return out
