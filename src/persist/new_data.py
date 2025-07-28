import json
import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)


def run(verbose: bool = False) -> dict:
    """Generate dummy data and save it under exports/."""
    data = {"timestamp": int(time.time())}
    exports = Path("exports")
    exports.mkdir(parents=True, exist_ok=True)
    out = exports / "new_data.json"
    json.dump(data, out.open("w"))
    if verbose:
        log.info("saved new data -> %s", out)
    return data


if __name__ == "__main__":  # pragma: no cover - manual runs
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s"
    )
    run(verbose=True)
