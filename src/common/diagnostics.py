from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

log = logging.getLogger(__name__)


def _shape(obj: Any) -> tuple[str, int | None]:
    """Return (type name, len) for *obj* if possible."""
    t = type(obj).__name__
    try:
        length = len(obj)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - len may not be supported
        length = None
    return t, length


def validate_io(func: Callable[..., Any]) -> Callable[..., Any]:
    """Log simple input/output type and length details."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        arg = args[0] if args else (next(iter(kwargs.values())) if kwargs else None)
        in_t, in_len = _shape(arg)
        result = func(*args, **kwargs)
        out_t, out_len = _shape(result)
        log.info(
            "%s input=%s len=%s output=%s len=%s",
            func.__name__,
            in_t,
            in_len,
            out_t,
            out_len,
        )
        return result

    return wrapper
