"""
Create exports/yachts.csv from either a DuckDB file or a JSON fallback.

The public contract is:
    • Always produce `exports/yachts.csv`
    • Columns must be exactly ["name", "length_m"]   (all tests rely on this)
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

EXPORT_DIR = Path("exports")
CSV_PATH = EXPORT_DIR / "yachts.csv"


@sensor("export")
@validate_io
def run(db_path: Path = Path("yachts.duckdb")) -> Path:
    """Return the path to **exports/yachts.csv** (creating dirs if required)."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 1) Try to read from DuckDB (if the file exists)                    #
    # ------------------------------------------------------------------ #
    df: pd.DataFrame
    if db_path.exists():
        con = duckdb.connect(str(db_path))
        try:
            # Use aliases *different* from source column names to avoid the
            # “referenced before defined” binder error.
            df = con.execute(
                """
                SELECT
                    COALESCE(yacht_name, name)   AS name,
                    COALESCE(LOA_m, length_m)    AS length_m
                FROM yachts
                """
            ).fetch_df()
        finally:
            con.close()
    else:
        df = pd.DataFrame()

    # ------------------------------------------------------------------ #
    # 2) Fallback: look for exports/new_data.json                        #
    # ------------------------------------------------------------------ #
    if df.empty:
        json_path = EXPORT_DIR / "new_data.json"
        if json_path.exists():
            try:
                records = json.loads(json_path.read_text())
                if isinstance(records, dict):
                    records = [records]
                elif not isinstance(records, list):
                    raise TypeError("export JSON must be list or dict")

                if records:
                    df = pd.DataFrame(records)
            except Exception as exc:  # noqa: BLE001
                log.error("could not load JSON fallback: %s", exc, exc_info=True)

    # ------------------------------------------------------------------ #
    # 3) Validate final frame                                            #
    # ------------------------------------------------------------------ #
    required_cols = {"name", "length_m"}
    if df.empty:
        raise ValueError("no data found in DB or JSON fallback")
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"missing columns: {missing}")

    # Normalise column order & types
    df = df.loc[:, ["name", "length_m"]]
    df["name"] = df["name"].astype(str)
    df["length_m"] = pd.to_numeric(df["length_m"], errors="coerce")

    # ------------------------------------------------------------------ #
    # 4) Write out                                                       #
    # ------------------------------------------------------------------ #
    df.to_csv(CSV_PATH, index=False)
    log.info("wrote %d rows → %s", len(df), CSV_PATH)
    return CSV_PATH


if __name__ == "__main__":  # pragma: no cover
    p = run()
    print("Export wrote:", p, "Exists?", p.exists())
