from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger(__name__)

_LENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*m", re.I)


def _parse_length(text: str) -> float | None:
    match = _LENGTH_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:  # pragma: no cover - defensive
        log.debug("length parse failed for %s", text)
        return None


def parse_entry(entry: dict[str, Any]) -> dict[str, Any]:
    title = (entry.get("title") or "").strip()
    summary = entry.get("summary") or ""
    length = _parse_length(" ".join([title, summary]))
    out: dict[str, Any] = {"name": title, "length_m": length}
    for key in ["link", "published", "summary"]:
        if key in entry:
            out[key] = entry[key]
    return out


def run(entries: dict[str, list[dict]]) -> list[dict]:
    records: list[dict] = []
    for items in entries.values():
        for e in items:
            records.append(parse_entry(e))
    return records
