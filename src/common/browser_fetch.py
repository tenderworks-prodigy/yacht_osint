"""Fetch helper using Playwright Chromium with basic stealth settings."""

from __future__ import annotations

import asyncio
import os

from playwright.sync_api import TimeoutError, sync_playwright

from .throttle import sleep as throttle_sleep

BROWSER_SEMAPHORE = asyncio.Semaphore(2)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36"
)


def fetch_with_browser(url: str, timeout_ms: int = 15000) -> tuple[bytes | None, int, str]:
    """Fetch *url* using a headless Chromium browser."""
    throttle_sleep()
    with sync_playwright() as pw:
        launch_opts = {
            "headless": True,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if os.getenv("USE_PROXY_PLAYWRIGHT", "").lower() == "true" and (
            proxy := os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        ):
            launch_opts["proxy"] = {"server": proxy}

        browser = pw.chromium.launch(**launch_opts)
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            java_script_enabled=True,
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()
        try:
            resp = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            body = page.content().encode()
            status = resp.status if resp else 0
            ctype = resp.headers.get("content-type", "") if resp else ""
        except TimeoutError:
            body, status, ctype = None, 0, ""
        finally:
            browser.close()
        return body, status, ctype


__all__ = ["fetch_with_browser", "BROWSER_SEMAPHORE"]
