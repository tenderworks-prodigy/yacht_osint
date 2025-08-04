import os


def require_env(var: str) -> str:
    """Return environment variable or exit with error."""
    value = os.environ.get(var)
    if not value:
        raise SystemExit(f"Missing required environment variable: {var}")
    return value
