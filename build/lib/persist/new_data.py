import json
import logging
import time
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate

log = logging.getLogger(__name__)


def run(data: dict | None = None, verbose: bool = False) -> dict:
    """Save new data under exports/ and return it, validating against schema."""
    if data is None:
        data = {"timestamp": int(time.time())}

    # JSON Schema: allow a single object (heartbeat) or an array of objects with required fields
    schema: dict[str, Any] = {
        "oneOf": [
            {"type": "object"},
            {
                "type": "array",
                "items": {"type": "object", "required": ["name", "length_m"]},
            },
        ]
    }
    try:
        validate(instance=data, schema=schema)
    except ValidationError as exc:
        log.error("new_data schema validation failed: %s", exc.message)
        raise ValueError("invalid new_data payload") from exc

    exports = Path("exports")
    exports.mkdir(parents=True, exist_ok=True)
    out = exports / "new_data.json"
    json.dump(data, out.open("w"))

    if verbose:
        if data:
            log.info("saved new data -> %s", out)
        else:
            log.info("no new records -> %s", out)
    return data


if __name__ == "__main__":  # pragma: no cover - manual runs
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")
    run(verbose=True)
