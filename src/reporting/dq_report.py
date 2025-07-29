from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def run(
    csv_path: Path = Path("exports/yachts.csv"), html_out: Path = Path("dq_report.html")
) -> Path:
    """Generate a simple data quality report."""
    df = pd.read_csv(csv_path)
    issues = []
    if df.isnull().any().any():
        issues.append("null values present")
    if "length_m" in df and (df["length_m"] <= 0).any():
        issues.append("non-positive lengths")

    html = ["<html><body><h1>Data Quality Report</h1>"]
    if issues:
        html.append("<p>Errors:</p><ul>")
        for item in issues:
            html.append(f"<li>{item}</li>")
        html.append("</ul>")
    else:
        html.append("<p>No issues detected.</p>")
    html.append("</body></html>")
    html_out.write_text("".join(html))
    log.info("saved report -> %s", html_out)

    if issues:
        raise RuntimeError("; ".join(issues))
    return html_out


if __name__ == "__main__":  # pragma: no cover
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)
    run()
