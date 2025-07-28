from pathlib import Path

import pandas as pd
from src.persist import exports


def test_run_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = exports.run(pd.DataFrame([{"name": "A", "length_m": 1}]))
    assert Path(out).exists()
    df = pd.read_csv(out)
    assert list(df.columns) == ["name", "length_m"]
    assert len(df) == 1
