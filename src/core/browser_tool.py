"""
Browser tool via Playwright when installed (N17).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def browser_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


def fetch_page_text(url: str, timeout_ms: int = 15000) -> Dict[str, Any]:
    """
    Fetch page text. Requires: pip install playwright && playwright install chromium
    Blocks private/link-local destinations (SSRF mitigation).
    """
    from .net_safety import validate_public_http_url

    url_err = validate_public_http_url(url)
    if url_err:
        return {"ok": False, "error": url_err, "url": url}
    if not browser_available():
        return {
            "ok": False,
            "error": "playwright not installed",
            "hint": "pip install playwright && playwright install chromium",
            "stub": True,
            "url": url,
        }
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout_ms)
            text = page.inner_text("body")[:15000]
            title = page.title()
            browser.close()
            return {"ok": True, "url": url, "title": title, "text": text}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "url": url}
