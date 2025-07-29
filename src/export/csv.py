import json
import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.sensors import sensor

EXPORT_DIR = Path("exports")

log = logging.getLogger(__name__)


@sensor("export")
def run(db_path: Path = Path("yachts.duckdb")) -> Path:
    EXPORT_DIR.mkdir(exist_ok=True)
    df = pd.DataFrame()
    if db_path.exists():
        con = duckdb.connect(str(db_path))
        try:
            df = con.execute("SELECT name, length_m FROM yachts").fetch_df()
        finally:
            con.close()

    if df.empty:
        json_path = EXPORT_DIR / "new_data.json"
        if json_path.exists():
            try:
                records = json.loads(json_path.read_text())
                df = pd.DataFrame(records)[["name", "length_m"]]
            except Exception as exc:  # pragma: no cover - data errors
                log.warning("failed to load %s: %s", json_path, exc)

    out = EXPORT_DIR / "yachts.csv"
    if df.empty:
        df = pd.DataFrame(columns=["name", "length_m"])
    with out.open("w", newline="") as f:
        df.to_csv(f, index=False)
    log.info("saved %d rows -> %s", len(df), out)
    return out
