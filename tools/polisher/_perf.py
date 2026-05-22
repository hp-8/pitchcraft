"""Perf-pass — dedupe stylesheets, preconnect heavyweight CDNs."""
from __future__ import annotations

from bs4 import BeautifulSoup

from tools.polisher._html import ensure_head

_PRECONNECT_HOSTS = (
    "https://cdn.tailwindcss.com",
    "https://cdn.jsdelivr.net",
    "https://cdnjs.cloudflare.com",
    "https://fonts.googleapis.com",
    "https://fonts.gstatic.com",
)


def dedupe_links(soup: BeautifulSoup) -> int:
    """Remove duplicate <link rel=stylesheet> with identical href. Returns removed count."""
    seen: set[str] = set()
    removed = 0
    for link in soup.find_all("link"):
        rel = link.get("rel")
        if not rel:
            continue
        if isinstance(rel, list):
            rel = " ".join(rel)
        if "stylesheet" not in rel:
            continue
        href = link.get("href") or ""
        if not href:
            continue
        if href in seen:
            link.decompose()
            removed += 1
            continue
        seen.add(href)
    return removed


def add_preconnects(soup: BeautifulSoup) -> int:
    head = ensure_head(soup)
    existing = set()
    for link in head.find_all("link"):
        rel = link.get("rel")
        if not rel:
            continue
        if isinstance(rel, list):
            rel = " ".join(rel)
        if "preconnect" in rel:
            existing.add(link.get("href") or "")
    added = 0
    for host in _PRECONNECT_HOSTS:
        if host in existing:
            continue
        tag = soup.new_tag("link", rel="preconnect", href=host)
        if "fonts.gstatic" in host:
            tag["crossorigin"] = ""
        head.insert(0, tag)
        added += 1
    return added


def apply_perf(soup: BeautifulSoup) -> dict[str, int]:
    return {
        "deduped_stylesheets": dedupe_links(soup),
        "added_preconnects": add_preconnects(soup),
    }
