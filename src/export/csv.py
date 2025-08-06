"""
Create *exports/yachts.csv* from either a DuckDB file or a JSON fallback.

Contract required by the test-suite
-----------------------------------
• The file is always produced, even if there are zero rows.
• Header must be exactly ["name", "length_m"] (order matters).
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
REQUIRED = ["name", "length_m"]


# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #
def _columns_in_table(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    """Return the set of column names that exist in *table*."""
    rows: list[tuple] = con.execute(f"PRAGMA table_info('{table}')").fetchall()
    return {r[1] for r in rows}  # r[1] == column name


def _select_from_yachts(db_path: Path) -> pd.DataFrame:
    """Return DataFrame with canonical column names from *yachts* table."""
    con = duckdb.connect(str(db_path))
    try:
        cols = _columns_in_table(con, "yachts")
        name_col = "yacht_name" if "yacht_name" in cols else "name" if "name" in cols else None
        len_col = "LOA_m" if "LOA_m" in cols else "length_m" if "length_m" in cols else None

        if name_col and len_col:
            query = f"SELECT {name_col} AS name, {len_col} AS length_m " "FROM yachts"
            return con.execute(query).fetch_df()
    finally:
        con.close()
    return pd.DataFrame(columns=REQUIRED)


def _load_json_fallback() -> pd.DataFrame:
    json_path = EXPORT_DIR / "new_data.json"
    if not json_path.exists():
        return pd.DataFrame(columns=REQUIRED)

    try:
        records = json.loads(json_path.read_text())
        if isinstance(records, dict):
            records = [records]
        if not isinstance(records, list):
            raise TypeError("export JSON must be list or dict")
        if not records:
            return pd.DataFrame(columns=REQUIRED)
        df = pd.DataFrame(records)
        return df.rename(columns={"yacht_name": "name", "LOA_m": "length_m"})
    except Exception as exc:  # noqa: BLE001
        log.error("could not load JSON fallback: %s", exc, exc_info=True)
        return pd.DataFrame(columns=REQUIRED)


# --------------------------------------------------------------------------- #
# public entry-point                                                          #
# --------------------------------------------------------------------------- #
@sensor("export")
@validate_io
def run(db_path: Path = Path("yachts.duckdb")) -> Path:
    """Write **exports/yachts.csv** and return its Path."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = _select_from_yachts(db_path) if db_path.exists() else pd.DataFrame(columns=REQUIRED)

    if df.empty:
        df = _load_json_fallback()

    # Ensure schema & order
    df = df.reindex(columns=REQUIRED)
    df["name"] = df["name"].astype(str)
    df["length_m"] = pd.to_numeric(df["length_m"], errors="coerce")

    df.to_csv(CSV_PATH, index=False)
    log.info("wrote %d rows → %s", len(df), CSV_PATH)
    return CSV_PATH


if __name__ == "__main__":  # pragma: no cover
    p = run()
    print("wrote", p, "exists?", p.exists())
