import logging
import time
from typing import Any

import requests
from requests import RequestException, Response
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

log = logging.getLogger(__name__)
SESSION = requests.Session()
SESSION.trust_env = False


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(multiplier=1, max=30),
    retry=retry_if_exception_type(RequestException),
    before_sleep=before_sleep_log(log, logging.WARNING),
)
def request(method: str, url: str, **kwargs: Any) -> Response:
    """Perform an HTTP request with logging and retries."""
    start = time.monotonic()
    resp = SESSION.request(method, url, **kwargs)
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After")
        if retry_after is not None:
            try:
                wait = int(retry_after)
                if wait > 0:
                    time.sleep(wait)
            except ValueError:
                pass
        # raise to trigger retry
        raise RequestException(f"429 for {url}")
    if resp.status_code >= 500:
        raise RequestException(f"{resp.status_code} for {url}")
    duration = time.monotonic() - start
    snippet = resp.text[:200] if resp.text else ""
    log.info(
        "http %s %s status=%s duration=%.2f",
        method,
        url,
        resp.status_code,
        duration,
        extra={
            "headers": dict(resp.headers),
            "body_snippet": snippet,
        },
    )
    return resp


def get(url: str, **kwargs: Any) -> Response:
    return request("GET", url, **kwargs)
