from pathlib import Path

from src.export import csv as export_csv
from src.scrape import crawl


def test_smoke_pipeline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fixture = Path(__file__).parent / "fixtures" / "smoke_yachts.csv"
    assert fixture.is_file(), "fixture missing"
    monkeypatch.setattr(crawl.requests, "get", lambda url: None)
    crawl.run([{"domain": "example.com", "timestamp": 1}])
    (tmp_path / "exports").mkdir()
    (tmp_path / "exports" / "new_data.json").write_text('[{"name": "A", "length_m": 1}]')
    out = export_csv.run(tmp_path / "missing.duckdb")
    assert Path(out).read_text() == fixture.read_text()
