"""Run quick diagnostics then execute pipeline."""

import json
import logging
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency
    yaml = None

from src.common.http import get as http_get
from src.scrape.parse import discover_feeds

logging.basicConfig(level=logging.INFO)


def probe_sources(config_path: Path = Path("configs/sources.yml")) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if yaml is None:
        logging.error("yaml library missing; cannot run probe")
        return results
    sources = yaml.safe_load(config_path.read_text())
    for src in sources:
        url = src.get("rss") or f"https://{src['domain']}"
        entry: dict[str, Any] = {"source": src.get("domain"), "url": url}
        try:
            resp = http_get(url, timeout=10)
            entry.update(
                {
                    "status": resp.status_code,
                    "content_type": resp.headers.get("content-type"),
                    "size": len(resp.content),
                }
            )
        except Exception as exc:  # pragma: no cover - network errors
            logging.exception("probe failed for %s", url)
            entry["error"] = str(exc)
        results.append(entry)
    Path("diagnostics").mkdir(exist_ok=True)
    Path("diagnostics/manifest.json").write_text(json.dumps(results, indent=2))
    logging.info("wrote diagnostics/manifest.json")
    return results


def main() -> None:  # pragma: no cover - CLI helper
    probe_sources()
    # placeholder for full pipeline run
    for src in probe_sources():
        logging.info("discovered feeds for %s: %s", src["source"], discover_feeds(src["url"]))
    logging.info("diagnose_and_run complete")


if __name__ == "__main__":  # pragma: no cover - CLI helper
    main()
