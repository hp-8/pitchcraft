"""Honesty scan — flag invented metrics, fake social proof. Does not modify HTML."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

_PERF_CLAIM_RE = re.compile(
    r"\b(\d+%)\s+(faster|conversion|increase|growth|boost|uplift)\b", re.IGNORECASE
)
_PLUS_PCT_RE = re.compile(r"\+\d+%")
_TRUSTED_BY_RE = re.compile(
    r"trusted\s+by\s+\d+[,+]?\s*(teams|companies|users|customers|brands|businesses)",
    re.IGNORECASE,
)
_NX_FASTER_RE = re.compile(r"\b\d+x\s+(faster|better|more|stronger)\b", re.IGNORECASE)
_STAR_RATING_RE = re.compile(r"[★⭐]+\s*\d+(\.\d+)?")
_PLACEHOLDER_NAMES = (
    re.compile(r"\bJane\s+Doe\b"),
    re.compile(r"\bJohn\s+Doe\b"),
    re.compile(r"\bJohn\s+Smith\b"),
    re.compile(r"\bLorem\s+ipsum\b", re.IGNORECASE),
)


def scan(soup: BeautifulSoup) -> list[str]:
    """Return list of human-readable warnings."""
    text = soup.get_text(" ", strip=True)
    flags: list[str] = []

    for m in _PLUS_PCT_RE.findall(text):
        flags.append(f"invented-percent:{m}")
    for m in _PERF_CLAIM_RE.findall(text):
        flags.append(f"perf-claim:{m[0]} {m[1]}")
    if _TRUSTED_BY_RE.search(text):
        flags.append("trusted-by-banner")
    for m in _NX_FASTER_RE.findall(text):
        flags.append(f"nx-claim:{m}")
    if _STAR_RATING_RE.search(text):
        flags.append("unsourced-star-rating")
    for pat in _PLACEHOLDER_NAMES:
        if pat.search(text):
            flags.append(f"placeholder-name:{pat.pattern}")

    return flags
