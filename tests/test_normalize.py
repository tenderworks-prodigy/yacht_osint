from src.extract.normalize import normalize_builder


def test_normalize_builder():
    assert normalize_builder("X-Tenders") == "Xtenders"
    assert normalize_builder("Oceanco") == "Oceanco"
