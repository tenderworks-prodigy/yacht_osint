from __future__ import annotations

import logging
import os
from typing import List

import tldextract

import requests

log = logging.getLogger(__name__)
CSE_URL = "https://www.googleapis.com/customsearch/v1"


def search_sites(query: str, num: int = 10) -> List[str]:
    """Query Google CSE and return unique root domains."""
    key = os.environ.get("GOOGLE_CSE_API_KEY")
    cx = os.environ.get("GOOGLE_CSE_CX")
    if not key or not cx:
        raise RuntimeError("Missing Google CSE credentials")

    try:
        resp = requests.get(
            CSE_URL, params={"key": key, "cx": cx, "q": query, "num": num}, timeout=10
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # pragma: no cover - network errors
        log.error("CSE request failed: %s", exc)
        raise

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
    return list(dict.fromkeys(all_domains))
