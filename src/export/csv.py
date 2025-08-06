# ruff: noqa: I001
"""CSV export helper.

Writes a minimal **exports/yachts.csv** file with exactly the columns required by
our downstream tests (`yacht_name`, `LOA_m`).  The function tries, in order:

1. Reading from *yachts* table inside a DuckDB file (if it exists).
2. Falling back to a JSON dump at *exports/new_data.json*.
3. Creating an empty DataFrame with the correct headers when no data found.

The logic also transparently supports the older column names (`name`,
`length_m`) by renaming them on‑the‑fly so the rest of the pipeline remains
backward‑compatible.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.common.diagnostics import validate_io
from src.sensors import sensor

EXPORT_DIR = Path("exports")
log = logging.getLogger(__name__)


@sensor("export")
@validate_io
def run(db_path: Path = Path("yachts.duckdb")) -> Path:
    """Create **exports/yachts.csv** and return its path."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------
    # 1) Try fetching from DuckDB if it exists.
    # ---------------------------------------------------------------------
    if db_path.exists():
        con = duckdb.connect(str(db_path))
        try:
            df = con.execute(
                """
                SELECT
                    COALESCE(yacht_name, name) AS yacht_name,
                    COALESCE(LOA_m, length_m)  AS LOA_m
                FROM yachts
                """
            ).fetch_df()
        finally:
            con.close()
    else:
        df = pd.DataFrame()

    # ---------------------------------------------------------------------
    # 2) If DB empty, look for JSON fallback.
    # ---------------------------------------------------------------------
    if df.empty:
        json_path = EXPORT_DIR / "new_data.json"
        if json_path.exists():
            records: list[dict] | dict | str = json.loads(json_path.read_text())
            if isinstance(records, dict):
                records = [records]
            if not isinstance(records, list):  # pragma: no cover – type‑guard
                raise TypeError("export JSON must contain list or dict")
            df = pd.DataFrame(records)

            # Accept legacy column names.
            rename_map = {"name": "yacht_name", "length_m": "LOA_m"}
            df = df.rename(columns=rename_map)

    # ---------------------------------------------------------------------
    # 3) Guarantee required columns exist, even if empty.
    # ---------------------------------------------------------------------
    required = ["yacht_name", "LOA_m"]
    if not df.empty and not set(required).issubset(df.columns):
        missing = set(required) - set(df.columns)
        raise ValueError(f"missing columns: {missing}")
    df = df.reindex(columns=required)

    # ---------------------------------------------------------------------
    # 4) Write the CSV.
    # ---------------------------------------------------------------------
    out = EXPORT_DIR / "yachts.csv"
    df.to_csv(out, index=False)
    log.info("saved %d rows → %s", len(df), out)
    return out


if __name__ == "__main__":  # pragma: no cover – manual invocation
    path = run()
    print("Export wrote:", path, "Exists?", path.exists())
