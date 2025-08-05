"""
Diagnostic utility for RSS feed discovery.

This script is intended to be run ad hoc from the command line to probe a
single domain or URL and collect information about its HTML response and
potential feed links. It operates independently of any third‑party
dependencies such as ``requests`` or BeautifulSoup, relying solely on Python's
standard library. The output is printed as a JSON object on stdout.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) " "Gecko/20100101 Firefox/117.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

RAW_DIR = Path("diagnostics/raw")


def _fetch(url: str) -> tuple[bytes, int, str]:
    try:
        req = Request(url, headers=DEFAULT_HEADERS)
        with urlopen(req, timeout=10) as resp:  # type: ignore[attr-defined]
            body = resp.read()
            status = getattr(resp, "status", 0)
            content_type = resp.headers.get("Content-Type", "")
            return body, status, content_type
    except Exception as exc:
        logging.warning("request failed for %s: %s", url, exc)
        return b"", 0, ""


class _TagExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.feed_links: list[str] = []
        self.a_count: int = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower == "a":
            self.a_count += 1
        elif tag_lower == "link":
            attr_dict = {k.lower(): (v or "") for k, v in attrs}
            rel = attr_dict.get("rel", "").lower()
            type_attr = attr_dict.get("type", "").lower()
            if "alternate" in rel and ("rss" in type_attr or "atom" in type_attr):
                href = attr_dict.get("href")
                if href:
                    self.feed_links.append(urljoin(self.base_url, href))


def _detect_bot_challenge(html: str) -> bool:
    lower = html.lower()
    for marker in ("captcha", "are you human", "cloudflare", "__cf_chl_jschl_tk__"):
        if marker in lower:
            return True
    return False


def diagnose(url: str) -> dict:
    if "://" not in url:
        url = f"https://{url}"
    body, status, content_type = _fetch(url)
    if not body:
        return {
            "url": url,
            "status": status,
            "content_type": content_type,
            "response_len": 0,
            "feed_link_tags": [],
            "a_count": 0,
            "bot_challenge_detected": False,
        }
    text = body.decode(errors="ignore")
    extractor = _TagExtractor(url)
    try:
        extractor.feed(text)
    except Exception:
        pass
    feed_links = extractor.feed_links
    a_count = extractor.a_count
    bot_challenge = _detect_bot_challenge(text)
    if not feed_links:
        try:
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            domain = urlparse(url).netloc
            with (RAW_DIR / f"{domain}.html").open("wb") as f:
                f.write(body)
        except Exception:
            logging.warning("failed to write raw HTML for %s", url)
    return {
        "url": url,
        "status": status,
        "content_type": content_type,
        "response_len": len(body),
        "feed_link_tags": feed_links,
        "a_count": a_count,
        "bot_challenge_detected": bot_challenge,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose feed discovery for a domain or URL")
    parser.add_argument("url", help="Domain or full URL to probe")
    parser.add_argument(
        "--json", action="store_true", help="Output full JSON instead of pretty printing"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = diagnose(args.url)
    if args.json:
        print(json.dumps(result))
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
