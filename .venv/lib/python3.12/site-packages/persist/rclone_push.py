from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_fixed

from src.common.env import require_env

log = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def _sync(src: Path, dest: str) -> None:
    """Run rclone sync with retries."""
    subprocess.check_call(["rclone", "sync", str(src), dest])


def run() -> None:
    """Sync exported CSVs and reports to Google Drive."""
    folder_id = require_env("DRIVE_FOLDER_ID")
    exports = Path("exports")
    csvs = list(exports.glob("*.csv"))
    if not csvs:
        raise RuntimeError("no CSV files found in exports/")

    dest = f"remote:folder/{folder_id}"
    log.info("syncing %d files to %s", len(csvs), dest)
    _sync(exports, dest)

    report = Path("dq_report.html")
    if report.exists():
        _sync(report, dest)
