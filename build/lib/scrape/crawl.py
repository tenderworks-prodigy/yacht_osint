import json
import logging
from collections.abc import Iterable
from pathlib import Path

import requests
from jsonschema import ValidationError, validate

log = logging.getLogger(__name__)

FEED_SCHEMA = {
    "type": "object",
    "required": ["domain", "timestamp"],
    "properties": {
        "domain": {"type": "string"},
        "timestamp": {"type": "integer"},
    },
}
FEEDS_SCHEMA = {"type": "array", "items": FEED_SCHEMA}


def validate_feeds(feeds: list[dict]) -> list[dict]:
    """Validate discovered feeds against the JSON schema."""
    try:
        validate(instance=feeds, schema=FEEDS_SCHEMA)
    except ValidationError as exc:  # pragma: no cover - error path
        log.warning("feed schema violation: %s", exc.message)
        raise ValueError("invalid feed data") from exc
    return feeds


def load_feeds(path: Path) -> list[dict]:
    """Load and validate feeds from a JSON file."""
    try:
        feeds = json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - IO issues
        log.warning("failed to load %s: %s", path, exc)
        return []
    try:
        return validate_feeds(feeds)
    except ValueError:
        return []


def run(feeds: Iterable[dict] | None = None, feeds_file: Path | None = None) -> None:
    """Crawl the provided feeds."""
    if feeds is None:
        if feeds_file is None:
            feeds_file = Path("yacht_osint/data/cache/discovered_feeds.json")
        if feeds_file.exists():
            feeds = load_feeds(feeds_file)
        else:
            feeds = []

    for feed in feeds:
        if not isinstance(feed, dict) or "domain" not in feed:
            log.warning("invalid feed entry skipped: %s", feed)
            continue
        url = f"https://{feed['domain']}"
        requests.get(url)
