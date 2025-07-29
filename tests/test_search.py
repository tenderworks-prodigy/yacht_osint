import os
from typing import List


from src.scrape.search import search_sites, run


class DummyResponse:
    def __init__(self, items: List[str]):
        self._items = items
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"items": [{"link": url} for url in self._items]}


def test_search_sites(monkeypatch):
    def fake_get(url, params, timeout):
        return DummyResponse(
            [
                "https://example.com/post1",
                "https://blog.example.com/post2",
                "https://other.com/abc",
            ]
        )

    monkeypatch.setattr("requests.get", fake_get)
    os.environ["GOOGLE_CSE_API_KEY"] = "1"
    os.environ["GOOGLE_CSE_CX"] = "2"
    domains = search_sites("test")
    assert domains == ["example.com", "other.com"]


def test_run_timestamp(monkeypatch):
    monkeypatch.setattr(
        "src.scrape.search.search_sites", lambda q, num=10: ["a.com", "b.com"]
    )
    out = run(["a"])
    assert isinstance(out[0]["timestamp"], int)
    assert {d["domain"] for d in out} == {"a.com", "b.com"}


def test_search_sites_rate_limit(monkeypatch):
    class RLResponse:
        status_code = 429

        def raise_for_status(self):
            pass

        def json(self):
            return {}

    monkeypatch.setattr("requests.get", lambda *a, **k: RLResponse())
    monkeypatch.setattr("time.sleep", lambda *_: None)
    os.environ["GOOGLE_CSE_API_KEY"] = "1"
    os.environ["GOOGLE_CSE_CX"] = "2"
    os.environ["CSE_RETRIES"] = "1"
    os.environ["CSE_MAX_CONSECUTIVE"] = "1"
    domains = search_sites("foo")
    assert domains == []
