# ruff: noqa: I001
from pathlib import Path
import json
import logging
import duckdb
import pandas as pd
from src.common.diagnostics import validate_io
from src.sensors import sensor

EXPORT_DIR = Path("exports")

log = logging.getLogger(__name__)


@sensor("export")
@validate_io
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
                if isinstance(records, dict):
                    records = [records]
                elif not isinstance(records, list):
                    raise TypeError("export JSON must be list or dict")
                if records:
                    df = pd.DataFrame(records)
                    required = {"name", "length_m"}
                    if not required.issubset(df.columns):
                        missing = required - set(df.columns)
                        raise ValueError(f"missing columns: {missing}")
                    df = df[["name", "length_m"]]
                else:
                    df = pd.DataFrame(columns=["name", "length_m"])
            except Exception as exc:
                log.error("fatal in run: %s", exc, exc_info=True)
                raise

    out = EXPORT_DIR / "yachts.csv"
    log.debug("cwd=%s, EXPORT_DIR=%s, writing to %s", Path.cwd(), EXPORT_DIR, out)

    if df.empty:
        df = pd.DataFrame(columns=["name", "length_m"])
    required = {"name", "length_m"}
    if not required.issubset(df.columns):
        raise ValueError(f"missing columns: {required - set(df.columns)}")
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        df.to_csv(f, index=False)

    if not out.exists():
        log.error("expected export missing: %s", out)

    log.info("saved %d rows -> %s", len(df), out)
    return out


if __name__ == "__main__":
    p = run()
    print("Export wrote:", p, "Exists?", p.exists())
