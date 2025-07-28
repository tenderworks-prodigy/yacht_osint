import os
from typing import List


from src.scrape.search import search_sites


class DummyResponse:
    def __init__(self, items: List[str]):
        self._items = items

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
