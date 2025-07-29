from __future__ import annotations

import logging
import os
import random
import time
from typing import List

from src.common.env import require_env

import tldextract

import requests

log = logging.getLogger(__name__)
CSE_URL = "https://www.googleapis.com/customsearch/v1"

# retry configuration can be tweaked via environment variables
MAX_RETRIES = int(os.environ.get("CSE_RETRIES", "3"))
BACKOFF_BASE = float(os.environ.get("CSE_BACKOFF", "1"))
MAX_CONSECUTIVE = int(os.environ.get("CSE_MAX_CONSECUTIVE", "5"))

# counter for circuit breaker
_consecutive_429s = 0


def _search_google(query: str, num: int = 10) -> List[str]:
    """Query Google CSE and return root domains."""
    global _consecutive_429s

    if _consecutive_429s >= MAX_CONSECUTIVE:
        log.warning("skipping search due to repeated rate limits")
        return []

    key = require_env("GOOGLE_CSE_API_KEY")
    cx = require_env("GOOGLE_CSE_CX")

    payload = {}
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                CSE_URL,
                params={"key": key, "cx": cx, "q": query, "num": num},
                timeout=10,
            )
        except Exception as exc:  # pragma: no cover - network errors
            log.error("CSE request failed: %s", exc)
            raise

        if resp.status_code == 429:
            _consecutive_429s += 1
            wait = BACKOFF_BASE * 2**attempt + random.uniform(0, 1)
            log.warning("rate limit hit, retrying in %.1fs", wait)
            time.sleep(wait)
            continue

        _consecutive_429s = 0
        try:
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # pragma: no cover - network errors
            log.error("CSE request failed: %s", exc)
            raise
        break
    else:
        log.warning("rate limit persisted after %s retries", MAX_RETRIES)
        return []

    domains: List[str] = []
    for item in payload.get("items", []):
        url = item.get("link")
        if not url:
            continue
        ext = tldextract.extract(url)
        domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def _search_bing(query: str, num: int = 10) -> List[str]:
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
    except Exception:
        log.warning("bing search failed for %s", query)
        return []
    links = [
        item.get("url")
        for item in data.get("webPages", {}).get("value", [])
        if item.get("url")
    ]
    domains = []
    for url in links:
        ext = tldextract.extract(url)
        domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def _search_duckduckgo(query: str, num: int = 10) -> List[str]:
    api_url = os.environ.get("DDG_API_URL")
    if not api_url:
        return []
    try:
        resp = requests.get(
            api_url, params={"q": query, "format": "json", "no_redirect": 1}, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.warning("duckduckgo search failed for %s", query)
        return []
    links = [
        r.get("firstURL") for r in data.get("RelatedTopics", []) if r.get("firstURL")
    ]
    domains = []
    for url in links[:num]:
        ext = tldextract.extract(url)
        domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def search_sites(query: str, num: int = 10) -> List[str]:
    results: List[str] = []
    results.extend(_search_google(query, num))
    results.extend(_search_bing(query, num))
    results.extend(_search_duckduckgo(query, num))
    return list(dict.fromkeys(results))


def run(queries: List[str], num: int = 10) -> List[dict]:
    results: List[dict] = []
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
