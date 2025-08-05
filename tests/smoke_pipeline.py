import pandas as pd

from src.export import csv as export_csv
from src.scrape import crawl


def test_smoke_pipeline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # stub network call
    monkeypatch.setattr(crawl.requests, "get", lambda url: None)
    feeds = [{"domain": "example.com", "timestamp": 1}]
    crawl.run(feeds)
    (tmp_path / "exports").mkdir()
    (tmp_path / "exports" / "new_data.json").write_text('[{"name": "A", "length_m": 1}]')
    export_csv.run(tmp_path / "missing.duckdb")
    df = pd.read_csv(tmp_path / "exports" / "yachts.csv")
    assert len(df) >= 1
