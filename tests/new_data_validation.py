from __future__ import annotations

\"\"\"Tests for the JSON schema validation added to ``src.persist.new_data``.\"\""

import pytest

from src.persist import new_data as nd


def test_new_data_valid_list():
    # proper list of yachts with required fields
    data = [{"name": "Yacht A", "length_m": 50.0}, {"name": "Yacht B", "length_m": 70.5}]
    result = nd.run(data, verbose=True)
    assert isinstance(result, list) or isinstance(result, dict)


def test_new_data_invalid_list():
    # missing required length_m should fail
    data = [{"name": "Yacht A"}]
    with pytest.raises(ValueError):
        nd.run(data)


def test_new_data_object_heartbeat():
    # single object without name/length_m allowed (heartbeat style)
    result = nd.run({"timestamp": 1234567890}, verbose=False)
    assert isinstance(result, dict)
