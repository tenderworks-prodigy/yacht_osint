import functools
import hashlib
import inspect
import json
import logging
import pathlib
import time

LOG = logging.getLogger("sensors")


def sensor(tag: str):
    def decorate(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            t0 = time.perf_counter()
            ok = True
            try:
                result = fn(*a, **kw)
                return result
            except Exception:
                ok = False
                raise
            finally:
                payload = {
                    "tag": tag,
                    "fn": fn.__name__,
                    "file": pathlib.Path(inspect.getfile(fn)).name,
                    "ok": ok,
                    "dt_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "args_sha": hashlib.md5(repr((a, kw)).encode()).hexdigest()[:8],
                }
                LOG.info("SENSOR: %s", json.dumps(payload))

        return wrapper

    return decorate
