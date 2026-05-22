"""Multi-page Firecrawl helper for richer NLP input.

Crawls a lead's site for 3 high-signal pages (root, /about, /services or vertical equivalent)
plus any audit.json markdown if already cached. Returns concatenated cleaned text.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from tools.audit._firecrawl import fetch_firecrawl

logger = logging.getLogger(__name__)

# Per-vertical priority paths in addition to root.
EXTRA_PATHS: dict[str, list[str]] = {
    "fnb": ["/about", "/our-services", "/services", "/wineries", "/shop", "/wines"],
    "restaurant": ["/about", "/menu", "/services", "/private-events"],
    "dental": ["/about", "/services", "/team", "/treatments"],
    "realtor": ["/about", "/services", "/properties", "/listings", "/team"],
}

_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean(md: str) -> str:
    if not md:
        return ""
    md = _MD_LINK_RE.sub(r"\1", md)  # keep link text, drop URL
    md = _HTML_TAG_RE.sub(" ", md)
    md = _WS_RE.sub(" ", md)
    return md.strip()


def _existing_audit_markdown(lead_dir: Path) -> str:
    audit_path = lead_dir / "audit.json"
    if not audit_path.exists():
        return ""
    try:
        import json
        data = json.loads(audit_path.read_text(encoding="utf-8"))
        # Audit may have stored Firecrawl markdown
        fc = data.get("firecrawl") or {}
        return _clean(fc.get("markdown") or "")
    except Exception:
        return ""


def crawl_lead_pages(
    site_url: str,
    vertical: str,
    lead_dir: Path,
    max_pages: int = 3,
) -> dict[str, Any]:
    """Pull root + N vertical-specific pages. Returns {pages: [{url, text}], combined_text}.

    Reuses audit Firecrawl markdown when present (cost-free). Only new URLs hit network.
    """
    parsed = urlparse(site_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    candidates: list[str] = [site_url]
    for path in EXTRA_PATHS.get(vertical.lower(), []):
        candidates.append(urljoin(base, path))
    seen: set[str] = set()
    unique: list[str] = []
    for u in candidates:
        if u in seen:
            continue
        seen.add(u)
        unique.append(u)
        if len(unique) >= max_pages:
            break

    pages: list[dict[str, str]] = []

    # Reuse cached audit markdown for root if present
    cached = _existing_audit_markdown(lead_dir)
    if cached and unique:
        pages.append({"url": unique[0], "text": cached})
        unique = unique[1:]

    for u in unique:
        try:
            res = fetch_firecrawl(u)
        except Exception as exc:  # noqa: BLE001
            logger.warning("firecrawl %s failed: %s", u, exc)
            continue
        if res.get("error"):
            logger.info("firecrawl %s returned error: %s", u, res["error"])
            continue
        text = _clean(res.get("markdown") or "")
        if text:
            pages.append({"url": u, "text": text})

    combined = "\n\n".join(p["text"] for p in pages)
    return {"pages": pages, "combined_text": combined, "char_count": len(combined)}
