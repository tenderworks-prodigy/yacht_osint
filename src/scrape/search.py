from __future__ import annotations

import logging
import os
import random
import time
from typing import List

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


def search_sites(query: str, num: int = 10) -> List[str]:
    """Query Google CSE and return unique root domains."""
    global _consecutive_429s

    if _consecutive_429s >= MAX_CONSECUTIVE:
        log.warning("skipping search due to repeated rate limits")
        return []

    key = os.environ.get("GOOGLE_CSE_API_KEY")
    cx = os.environ.get("GOOGLE_CSE_CX")
    if not key or not cx:
        raise RuntimeError("Missing Google CSE credentials")

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


def run(queries: List[str], num: int = 10) -> List[str]:
    all_domains: List[str] = []
    for q in queries:
        try:
            all_domains.extend(search_sites(q, num))
        except Exception as exc:  # pragma: no cover - logging
            log.warning("search failed for %s: %s", q, exc)
    # dedupe while preserving order
    deduped = list(dict.fromkeys(all_domains))
    log.info("\u2705 %d queries, %d unique domains", len(queries), len(deduped))
    return deduped
