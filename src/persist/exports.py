import logging
from pathlib import Path

import duckdb

log = logging.getLogger(__name__)


def run(db_path: Path = Path("yachts.duckdb")) -> Path:
    """Export yacht data from DuckDB to CSV."""
    con = duckdb.connect(str(db_path))
    try:
        df = con.execute("SELECT name, length_m FROM yachts").fetch_df()
    finally:
        con.close()

    if df.empty:
        raise RuntimeError("yachts table is empty")

    exports = Path("exports")
    exports.mkdir(parents=True, exist_ok=True)
    out = exports / "yachts.csv"
    df.to_csv(out, index=False)
    log.info("saved %d rows -> %s", len(df), out)
    return out
