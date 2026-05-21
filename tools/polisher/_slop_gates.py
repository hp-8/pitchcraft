"""Hallmark slop-test subset gates."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

_URL_PILL_RE = re.compile(r"https?://|\.com|\.io|\.dev|/[a-z]+", re.IGNORECASE)


def _detect_fake_browser_chrome(soup: BeautifulSoup) -> bool:
    """Heuristic: a container with 3+ small dot children + a url-looking element."""
    for container in soup.find_all(["div", "header"]):
        dot_count = 0
        for child in container.find_all(["span", "div"], recursive=True):
            cls = child.get("class") or []
            if isinstance(cls, str):
                cls = cls.split()
            if any("dot" in c.lower() for c in cls):
                dot_count += 1
            if dot_count >= 3:
                break
        if dot_count >= 3:
            text = container.get_text(" ", strip=True)[:200]
            if _URL_PILL_RE.search(text):
                return True
    return False


def _detect_fake_phone_frame(soup: BeautifulSoup) -> bool:
    for el in soup.find_all(["div", "section"]):
        cls = el.get("class") or []
        if isinstance(cls, str):
            cls = cls.split()
        cls_lower = " ".join(c.lower() for c in cls)
        if "notch" in cls_lower or "iphone" in cls_lower or "phone-frame" in cls_lower:
            return True
        style = (el.get("style") or "").lower()
        if "aspect-ratio: 9 / 19" in style or "aspect-ratio: 9/19" in style:
            return True
    return False


def _detect_missing_focus_visible(soup: BeautifulSoup) -> bool:
    """If no <style> contains :focus-visible AND any button/link exists -> fail."""
    has_interactive = bool(soup.find(["button", "a"]))
    if not has_interactive:
        return False
    for style in soup.find_all("style"):
        if style.string and ":focus-visible" in style.string:
            return False
    return True


def check_gates(soup: BeautifulSoup) -> list[str]:
    failures: list[str] = []
    if _detect_fake_browser_chrome(soup):
        failures.append("gate:fake-browser-chrome")
    if _detect_fake_phone_frame(soup):
        failures.append("gate:fake-phone-frame")
    if _detect_missing_focus_visible(soup):
        failures.append("gate:missing-focus-visible")
    return failures
