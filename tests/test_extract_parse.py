from src.extract import parse


def test_parse_entry_basic():
    entry = {"title": "Yacht A 100m", "summary": "A great yacht", "link": "http://e"}
    out = parse.parse_entry(entry)
    assert out["name"] == "Yacht A 100m"
    assert out["length_m"] == 100.0
    assert out["link"] == "http://e"


def test_run_handles_missing_length():
    entries = {"d": [{"title": "No length"}]}
    res = parse.run(entries)
    assert res[0]["name"] == "No length"
    assert "length_m" in res[0]
