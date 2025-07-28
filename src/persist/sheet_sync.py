from __future__ import annotations

import logging

import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

from src.common.env import require_env

log = logging.getLogger(__name__)


def _get_client() -> gspread.Client:
    creds_path = require_env("GOOGLE_APPLICATION_CREDENTIALS")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scopes)
    return gspread.authorize(creds)


def run(df: pd.DataFrame) -> None:
    """Sync dataframe to the first worksheet of the spreadsheet."""
    sheet_id = require_env("SPREADSHEET_ID")
    client = _get_client()
    sh = client.open_by_key(sheet_id)
    ws = sh.sheet1
    ws.clear()
    ws.update([df.columns.tolist()] + df.astype(str).values.tolist())
    log.info("synced %d rows to Google Sheet", len(df))
