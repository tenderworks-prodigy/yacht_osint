from pathlib import Path

import pandas as pd
from src.persist import duckdb_io, exports


def test_run_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    duckdb_io.run(pd.DataFrame([{"name": "A", "length_m": 1}]), tmp_path / "db.duckdb")
    out = exports.run(tmp_path / "db.duckdb")
    assert Path(out).exists()
    df = pd.read_csv(out)
    assert list(df.columns) == ["name", "length_m"]
    assert len(df) == 1
