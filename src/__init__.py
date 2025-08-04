import logging
import os

# Optional imports: gracefully handle missing development dependencies such as
# python‑dotenv and python‑json‑logger. When these packages are absent the
# module defines lightweight fallbacks so that importing ``src`` does not
# immediately raise a ``ModuleNotFoundError``.
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    def load_dotenv(*_args: object, **_kwargs: object) -> None:
        return None

try:
    from pythonjsonlogger import jsonlogger  # type: ignore
except Exception:
    class _JSONLoggerStub:
        class JsonFormatter(logging.Formatter):  # type: ignore
            pass

    jsonlogger = _JSONLoggerStub()  # type: ignore

load_dotenv()

if not logging.getLogger().handlers:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    # Use the JSON formatter when available; otherwise fall back to a basic format
    try:
        formatter = jsonlogger.JsonFormatter()  # type: ignore[attr-defined]
    except Exception:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=[handler])
