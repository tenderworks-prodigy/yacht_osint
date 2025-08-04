from pathlib import Path

import pandas as pd

from src.export import csv as export_csv
from src.persist import duckdb_io


def test_run_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    duckdb_io.run(pd.DataFrame([{"name": "A", "length_m": 1}]), tmp_path / "db.duckdb")
    out = export_csv.run(tmp_path / "db.duckdb")
    assert Path(out).exists()
    assert Path("exports/yachts.csv").is_file()
    df = pd.read_csv(out)
    assert list(df.columns) == ["name", "length_m"]
    assert len(df) == 1


def test_export_empty_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import duckdb

    con = duckdb.connect(str(tmp_path / "db.duckdb"))
    con.execute("CREATE TABLE yachts (name VARCHAR, length_m DOUBLE)")
    con.close()
    out = export_csv.run(tmp_path / "db.duckdb")
    df = pd.read_csv(out)
    assert Path("exports/yachts.csv").is_file()
    assert list(df.columns) == ["name", "length_m"]
    assert len(df) == 0


def test_run_exports_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "exports").mkdir()
    (tmp_path / "exports" / "new_data.json").write_text('{"name": "B", "length_m": 2}')
    out = export_csv.run(tmp_path / "missing.duckdb")
    df = pd.read_csv(out)
    assert Path("exports/yachts.csv").is_file()
    assert df.iloc[0]["name"] == "B"


def test_run_exports_empty_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "exports").mkdir()
    (tmp_path / "exports" / "new_data.json").write_text("[]")
    out = export_csv.run(tmp_path / "missing.duckdb")
    df = pd.read_csv(out)
    assert Path("exports/yachts.csv").is_file()
    assert list(df.columns) == ["name", "length_m"]
    assert len(df) == 0
