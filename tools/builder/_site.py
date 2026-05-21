"""Assemble the static site directory."""
from __future__ import annotations

import json
from pathlib import Path

from tools.builder._assets import PROTOTYPE_CSS, PROTOTYPE_JS, VERCEL_JSON

PAGE_FILENAMES: dict[str, str] = {
    "landing": "index.html",
    "services": "services.html",
    "about": "about.html",
    "contact": "contact.html",
}

PAGE_ORDER: tuple[str, ...] = ("landing", "services", "about", "contact")


def write_site(
    site_dir: str | Path, page_html: dict[str, str]
) -> dict[str, Path]:
    """Write transformed HTML + shared assets + vercel.json. Returns map of page→path."""
    root = Path(site_dir)
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    (assets / "prototype.js").write_text(PROTOTYPE_JS, encoding="utf-8")
    (assets / "prototype.css").write_text(PROTOTYPE_CSS, encoding="utf-8")
    (root / "vercel.json").write_text(
        json.dumps(VERCEL_JSON, indent=2) + "\n", encoding="utf-8"
    )

    written: dict[str, Path] = {}
    for page, html in page_html.items():
        if page not in PAGE_FILENAMES:
            continue
        target = root / PAGE_FILENAMES[page]
        target.write_text(html, encoding="utf-8")
        written[page] = target
    return written


def project_slug(business: str, lead_id: str) -> str:
    """Lowercase slug for vercel project name. Fallback to lead_id if business empty."""
    base = business.strip().lower() if business else lead_id
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", lead_id.lower()).strip("-")
    return slug[:63] or "site"
