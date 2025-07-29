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


def test_run_exports_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "exports").mkdir()
    (tmp_path / "exports" / "new_data.json").write_text(
        '[{"name": "B", "length_m": 2}]'
    )
    out = exports.run(tmp_path / "missing.duckdb")
    df = pd.read_csv(out)
    assert df.iloc[0]["name"] == "B"
