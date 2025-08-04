# ruff: noqa: I001
from pathlib import Path
import json
import logging
import duckdb
import pandas as pd
from src.sensors import sensor

EXPORT_DIR = Path("exports")

log = logging.getLogger(__name__)


@sensor("export")
def run(db_path: Path = Path("yachts.duckdb")) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Try the DuckDB first:
    if db_path.exists():
        con = duckdb.connect(str(db_path))
        try:
            df = con.execute("SELECT name, length_m FROM yachts").fetch_df()
        finally:
            con.close()
    else:
        df = pd.DataFrame()

    # If no rows in the DB, fall back to JSON:
    if df.empty:
        json_path = EXPORT_DIR / "new_data.json"
        if json_path.exists():
            try:
                records = json.loads(json_path.read_text())
                df = pd.DataFrame(records)[["name", "length_m"]]
            except Exception as exc:
                log.warning("failed to load %s: %s", json_path, exc)

    out = EXPORT_DIR / "yachts.csv"
    log.debug("cwd=%s, EXPORT_DIR=%s, writing to %s", Path.cwd(), EXPORT_DIR, out)

    if df.empty:
        df = pd.DataFrame(columns=["name", "length_m"])
    with out.open("w", newline="") as f:
        df.to_csv(f, index=False)

    if not out.exists():
        log.error("expected export missing: %s", out)

    log.info("saved %d rows -> %s", len(df), out)
    return out


if __name__ == "__main__":
    p = run()
    print("Export wrote:", p, "Exists?", p.exists())
