from __future__ import annotations

import json
import logging
from pathlib import Path

from src.common import load_settings
from src.scrape import rss as rss_mod
from src.scrape import search as search_mod

log = logging.getLogger(__name__)


def run() -> None:
    settings = load_settings()
    domains = search_mod.run(settings.search.queries, settings.search.result_count)
    if settings.search.domain_whitelist:
        domains = [d for d in domains if d in settings.search.domain_whitelist]
    if settings.search.domain_blacklist:
        domains = [d for d in domains if d not in settings.search.domain_blacklist]
    feeds = rss_mod.run(domains)
    out = Path("yacht_osint/data/cache/discovered_feeds.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(feeds, out.open("w"))
    log.info("saved feeds → %s", out)


if __name__ == "__main__":  # pragma: no cover
    run()
