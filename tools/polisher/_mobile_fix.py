"""Mobile correctness fixes (Hallmark non-negotiables subset)."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from tools.polisher._html import ensure_head

_BARE_1FR_RE = re.compile(r"grid-template-columns\s*:\s*1fr(?!\s*[a-z])", re.IGNORECASE)


def apply_mobile_fixes(soup: BeautifulSoup) -> list[str]:
    """Apply / warn mobile fixes. Returns list of applied / detected items."""
    fixes: list[str] = []

    head = ensure_head(soup)
    if not soup.find("meta", attrs={"name": "viewport"}):
        meta = soup.new_tag(
            "meta",
            attrs={"name": "viewport", "content": "width=device-width, initial-scale=1"},
        )
        head.append(meta)
        fixes.append("injected-viewport-meta")

    # Bare-1fr grid audit (warning only — best effort)
    for el in soup.find_all(style=True):
        style = el.get("style", "")
        if _BARE_1FR_RE.search(style) and "minmax" not in style:
            fixes.append("warn-bare-1fr-grid")
            break

    # Long-text button warning (>25 chars)
    for btn in soup.find_all(["button", "a"]):
        cls = btn.get("class") or []
        if isinstance(cls, str):
            cls = cls.split()
        if btn.name == "a" and not any(c in ("btn", "button") for c in cls):
            continue
        text = btn.get_text(strip=True)
        if len(text) > 25:
            fixes.append(f"warn-long-button-text:{text[:30]}")
            break

    return fixes
