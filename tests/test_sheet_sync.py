import pandas as pd

from src.persist import sheet_sync


class DummyWS:
    def __init__(self):
        self.data = []

    def clear(self):
        self.data.clear()

    def update(self, rows):
        self.data.extend(rows)


class DummySheet:
    def __init__(self):
        self.sheet1 = DummyWS()


class DummyClient:
    def __init__(self):
        self.opened = False

    def open_by_key(self, key):
        self.opened = True
        return DummySheet()


def test_sheet_sync(monkeypatch):
    df = pd.DataFrame([{"name": "A", "length_m": 1}])

    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "creds.json")
    monkeypatch.setenv("SPREADSHEET_ID", "123")

    monkeypatch.setattr(sheet_sync, "_get_client", lambda: DummyClient())

    sheet_sync.run(df)
