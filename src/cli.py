from __future__ import annotations

import json
import logging
from pathlib import Path

from src.common import load_settings
from src.export import csv as csv_mod
from src.extract import parse as parse_mod
from src.persist import new_data as new_data_mod
from src.scrape import rss as rss_mod
from src.scrape import search as search_mod

log = logging.getLogger(__name__)


def run() -> None:
    settings = load_settings()
    domain_entries = search_mod.run(settings.search.queries, settings.search.result_count)
    domains = [d["domain"] for d in domain_entries]
    if settings.search.domain_whitelist:
        domains = [d for d in domains if d in settings.search.domain_whitelist]
    if settings.search.domain_blacklist:
        domains = [d for d in domains if d not in settings.search.domain_blacklist]
    if not domains:
        domains = ["xkcd.com"]
    feed_map = rss_mod.discover_feeds(domains)
    if not feed_map:
        log.error("no feeds discovered from %d domain(s), aborting", len(domains))
        raise SystemExit(1)
    entries = rss_mod.fetch_entries(feed_map)
    records = parse_mod.run(entries)
    new_data_mod.run(records, verbose=True)
    csv_mod.run()
    out = Path("yacht_osint/data/cache/discovered_feeds.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(feed_map, out.open("w"))
    log.info("saved feeds → %s", out)


if __name__ == "__main__":  # pragma: no cover
    run()
