import importlib


def test_import_new_data():
    module = importlib.import_module("src.persist.new_data")
    assert hasattr(module, "run")
