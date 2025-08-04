from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

log = logging.getLogger(__name__)


def run(df: pd.DataFrame | None = None, db_path: Path = Path("yachts.duckdb")) -> Path:
    """Persist yacht data to DuckDB."""
    if df is None:
        df = pd.DataFrame([{"name": "Example Yacht", "length_m": 100.0}])
    if df.empty:
        raise RuntimeError("No data provided for DuckDB persistence")

    con = duckdb.connect(str(db_path))
    try:
        con.register("tmp", df)
        con.execute("CREATE OR REPLACE TABLE yachts AS SELECT name, length_m FROM tmp")
        log.info("wrote %d rows to %s", len(df), db_path)
    finally:
        con.close()
    return db_path
