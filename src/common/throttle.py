"""Simple request throttling helpers."""

import random
import time

BASE = 0.2  # seconds
JITTER = 0.6


def sleep() -> None:
    """Sleep for a base duration plus random jitter."""
    time.sleep(BASE + random.random() * JITTER)
