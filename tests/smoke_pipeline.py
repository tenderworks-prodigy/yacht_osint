import pandas as pd

from src.cli import run as cli_run
from src.export import csv as export_csv
from src.scrape import search as search_mod


def test_smoke_pipeline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(search_mod, "run", lambda q, n: ["boatinternational.com"])
    cli_run()
    (tmp_path / "exports").mkdir()
    (tmp_path / "exports" / "new_data.json").write_text('[{"name": "A", "length_m": 1}]')
    export_csv.run(tmp_path / "missing.duckdb")
    df = pd.read_csv(tmp_path / "exports" / "yachts.csv")
    assert len(df) >= 1
