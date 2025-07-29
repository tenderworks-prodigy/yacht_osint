import logging
import json
import os
from pathlib import Path

import duckdb
import pandas as pd

log = logging.getLogger(__name__)


def run(db_path: Path = Path("yachts.duckdb")) -> Path:
    """Export yacht data from DuckDB to CSV.

    If the database is missing or empty, fall back to ``exports/new_data.json``
    if it exists.
    """

    df = pd.DataFrame()
    if db_path.exists():
        con = duckdb.connect(str(db_path))
        try:
            df = con.execute("SELECT name, length_m FROM yachts").fetch_df()
        finally:
            con.close()

    if df.empty:
        json_path = Path("exports") / "new_data.json"
        if json_path.exists():
            try:
                records = json.loads(json_path.read_text())
                df = pd.DataFrame(records)
                df = df[["name", "length_m"]]
            except Exception as exc:  # pragma: no cover - data errors
                log.warning("failed to load %s: %s", json_path, exc)

    exports = Path("exports")
    exports.mkdir(parents=True, exist_ok=True)
    out = exports / "yachts.csv"
    if df.empty:
        df = pd.DataFrame(columns=["name", "length_m"])
    df.to_csv(out, index=False)
    log.info("saved %d rows -> %s", len(df), out)
    print("EXPORTS DIR:", os.listdir("exports"))
    return out
