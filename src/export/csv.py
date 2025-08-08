"""CSV export helpers.

This module reads yacht data either from a DuckDB database or from a
JSON fallback file and writes a ``yachts.csv`` export.  The implementation
mirrors the behaviour exercised in the tests: when the database is missing
or empty we look for ``exports/new_data.json`` and, if present, convert the
records to a :class:`pandas.DataFrame` before writing the CSV.

The :func:`run` function is decorated with ``validate_io`` so tests can
inspect simple input/output diagnostics.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.common.diagnostics import validate_io
from src.sensors import sensor

log = logging.getLogger(__name__)

# Directory and file locations used for exports
EXPORT_DIR = Path("exports")
CSV_PATH = EXPORT_DIR / "yachts.csv"

# Columns required in the exported CSV
REQUIRED = ["name", "length_m"]


def _select_from_yachts(db_path: Path) -> pd.DataFrame:
    """Return a DataFrame with yacht records from ``db_path``.

    Any failure to query the database results in an empty DataFrame with the
    required columns.  This keeps ``run`` simple and avoids propagating DuckDB
    errors to callers.
    """

    con = duckdb.connect(str(db_path))
    try:
        return con.execute("SELECT name, length_m FROM yachts").fetch_df()
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("duckdb select failed: %s", exc)
        return pd.DataFrame(columns=REQUIRED)
    finally:
        con.close()


def _load_json_fallback() -> pd.DataFrame:
    """Load ``exports/new_data.json`` if it exists.

    The JSON file may contain either a single object or a list of objects.
    Any parsing errors or schema mismatches result in an empty DataFrame with
    the required columns.
    """

    json_path = EXPORT_DIR / "new_data.json"
    if not json_path.exists():
        return pd.DataFrame(columns=REQUIRED)

    try:
        payload = json.loads(json_path.read_text() or "[]")
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("failed to load %s: %s", json_path, exc)
        return pd.DataFrame(columns=REQUIRED)

    if isinstance(payload, dict):
        records = [payload]
    elif isinstance(payload, list):
        records = payload
    else:  # pragma: no cover - defensive
        log.warning("export JSON must be list or dict")
        return pd.DataFrame(columns=REQUIRED)

    df = pd.DataFrame(records)
    return df


@validate_io
@sensor("export")
def run(db_path: Path = Path("yachts.duckdb")) -> Path:
    """Write ``exports/yachts.csv`` and return its :class:`Path`.

    The function prefers reading from ``db_path`` but will fall back to the
    JSON helper if necessary.  Basic data cleaning is performed to ensure
    required columns are present and correctly typed.
    """

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = _select_from_yachts(db_path) if db_path.exists() else pd.DataFrame(columns=REQUIRED)

    if df.empty:
        df = _load_json_fallback()

    # Ensure schema & order
    df = df.reindex(columns=REQUIRED)
    df["name"] = df["name"].astype(str)
    df["length_m"] = pd.to_numeric(df["length_m"], errors="coerce")

    # Drop rows with nulls in required columns
    df = df.dropna(subset=REQUIRED)
    # Fill remaining nulls
    df["name"] = df["name"].fillna("Unknown")
    df["length_m"] = df["length_m"].fillna(0)

    df.to_csv(CSV_PATH, index=False)
    log.info("wrote %d rows → %s", len(df), CSV_PATH)
    return CSV_PATH


__all__ = ["run"]
