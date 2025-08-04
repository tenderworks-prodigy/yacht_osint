import pandas as pd

from src.export import csv as export_csv
from src.scrape import crawl


def test_pipeline_no_new_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    crawl.run([])
    (tmp_path / "exports").mkdir()
    (tmp_path / "exports" / "new_data.json").write_text("[]")
    out = export_csv.run(tmp_path / "missing.duckdb")
    df = pd.read_csv(out)
    assert list(df.columns) == ["name", "length_m"]
    assert len(df) == 0
