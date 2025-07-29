import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def run() -> pd.DataFrame:
    """Assemble scraped data into a DataFrame."""
    path = Path("exports") / "new_data.json"
    records = []
    if path.exists():
        try:
            records = json.loads(path.read_text())
        except Exception as exc:  # pragma: no cover - data issues
            log.warning("failed to load %s: %s", path, exc)
    df = pd.DataFrame(records)
    for col in ["name", "length_m"]:
        if col not in df.columns:
            df[col] = None
    log.info("DF shape %s, columns %s", df.shape, df.columns.tolist())
    return df
