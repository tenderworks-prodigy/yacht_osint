import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def run(df: pd.DataFrame | None = None) -> Path:
    """Write the main DataFrame to exports/yachts.csv."""
    if df is None:
        df = pd.DataFrame([{"name": "Example Yacht", "length_m": 100}])

    if df.empty:
        raise RuntimeError("Refusing to write empty DataFrame")

    exports = Path("exports")
    exports.mkdir(parents=True, exist_ok=True)
    out = exports / "yachts.csv"
    df.to_csv(out, index=False)
    log.info("saved %d rows -> %s", len(df), out)
    return out
