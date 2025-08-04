import logging
import time
import random

from waybackpy import WaybackMachineCDXServerAPI

log = logging.getLogger(__name__)


def run(urls: list[str] | None = None) -> list[str]:
    """Fetch latest Wayback snapshots for given URLs."""
    urls = urls or []
    snapshots: list[str] = []
    for url in urls:
        try:
            cdx = WaybackMachineCDXServerAPI(url, user_agent="yacht-osint")
            snap = cdx.newest()
            snapshots.append(snap.archive_url)
            log.info("snapshot chosen %s", snap.archive_url)
        except Exception as exc:  # pragma: no cover - network
            status = getattr(getattr(exc, "response", None), "status_code", 0)
            if status == 429:
                # exponential-ish backoff with jitter for Wayback rate limit
                backoff = 1 + random.uniform(0, 2)
                log.warning(
                    "rate limit from Wayback (status=429) for %s; sleeping %.1fs", url, backoff
                )
                time.sleep(backoff)
                continue
            log.warning("wayback failed for %s: %s", url, exc)
    return snapshots
