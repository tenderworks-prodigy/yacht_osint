from pathlib import Path

import pandas as pd
import pytest

from src.reporting import dq_report


def test_dq_report_pass(tmp_path, monkeypatch):
    csv = tmp_path / "yachts.csv"
    pd.DataFrame([{"name": "A", "length_m": 1}]).to_csv(csv, index=False)
    monkeypatch.chdir(tmp_path)
    out = dq_report.run(csv, tmp_path / "report.html")
    assert Path(out).exists()


def test_dq_report_fail(tmp_path, monkeypatch):
    csv = tmp_path / "yachts.csv"
    pd.DataFrame([{"name": "A", "length_m": -1}]).to_csv(csv, index=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError):
        dq_report.run(csv, tmp_path / "report.html")
