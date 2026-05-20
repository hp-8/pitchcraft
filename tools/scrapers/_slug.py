"""Deterministic, filesystem-safe slug derivation from URLs."""
from __future__ import annotations

import re
from urllib.parse import urlparse

_SAFE = re.compile(r"[^a-z0-9]+")


def slugify_url(url: str) -> str:
    """Return a stable lowercased slug from a URL: netloc + path."""
    parsed = urlparse(url)
    base = f"{parsed.netloc}{parsed.path}".lower()
    slug = _SAFE.sub("-", base).strip("-")
    return slug[:120] or "ref"


def slugify(text: str) -> str:
    """Slugify arbitrary text into filesystem-safe lowercased token."""
    slug = _SAFE.sub("-", (text or "").lower()).strip("-")
    return slug[:120] or "ref"
