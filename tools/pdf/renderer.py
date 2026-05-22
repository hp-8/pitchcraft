"""Playwright PDF renderer: HTML string → PDF file."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def render_pdf(html: str, out_path: str | Path, format_: str = "A4") -> Path:
    from playwright.sync_api import sync_playwright

    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            page.pdf(
                path=str(out_p),
                format=format_,
                print_background=True,
                margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"},
            )
        finally:
            browser.close()

    logger.info("wrote %s (%d bytes)", out_p, out_p.stat().st_size)
    return out_p
