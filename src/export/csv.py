from pathlib import Path
import json
import logging

import duckdb
import pandas as pd

REPO_ROOT  = Path(__file__).parent.parent.parent
EXPORT_DIR = REPO_ROOT / "exports"

log = logging.getLogger(__name__)


def run(db_path: Path = Path("yachts.duckdb")) -> Path:
    EXPORT_DIR.mkdir(exist_ok=True, parents=True)

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

    # Always produce a CSV (empty or not):
    out = EXPORT_DIR / "yachts.csv"
    if df.empty:
        df = pd.DataFrame(columns=["name", "length_m"])
    with out.open("w", newline="") as f:
        df.to_csv(f, index=False)

    log.info("saved %d rows → %s", len(df), out)
    return out


if __name__ == "__main__":
    # Run unconditionally when invoked as a script:
    run()
