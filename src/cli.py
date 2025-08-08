+12
-1

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.common import load_settings
from src.export import csv as export_csv
from src.extract import run_all as extract_run_all
from src.persist import duckdb_io, new_data
from src.scrape import crawl
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
    # Guardrail: if no feeds were discovered, exit with a non-zero status. A
    # successful pipeline run is expected to return at least one feed.
    if not feeds:
        log.error("no feeds discovered from %d domain(s), aborting", len(domains))
        raise SystemExit(1)
    out = Path("yacht_osint/data/cache/discovered_feeds.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(feeds, out.open("w"))
    log.info("saved feeds → %s", out)

    # Downstream pipeline stages
    crawl.run(feeds)
    new_data.run()
    df = extract_run_all.run()
    db_path = duckdb_io.run(df)
    export_csv.run(db_path)


if __name__ == "__main__":  # pragma: no cover
    run()
