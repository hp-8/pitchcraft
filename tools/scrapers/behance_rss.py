"""Behance RSS scraper.

Behance public API shut down in 2019. Public feeds still work:
- Field-based: https://www.behance.net/feeds/projects?field=<id>
  88 = Web Design, 89 = UI/UX, 47 = Branding, 95 = Photography, 154 = Hospitality
- Tag-based path also returns RSS for tag pages.

CLI:
    uv run python -m tools.scrapers.behance_rss --query "web design" --limit 20
"""
from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import requests
import typer

from tools.scrapers import _cache
from tools.scrapers._models import ScraperItem, ScraperResult

logger = logging.getLogger(__name__)

SOURCE = "behance"
FEED_URL = "https://www.behance.net/feeds/projects"
MAX_LIMIT = 50

# Behance creative field IDs (subset relevant to our verticals).
FIELD_IDS: dict[str, int] = {
    "web design": 88,
    "ui/ux": 89,
    "branding": 47,
    "photography": 95,
    "hospitality": 154,
    "interior": 92,
    "illustration": 7,
    "architecture": 41,
}

_IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.I)


def _query_to_field_id(query: str) -> int:
    """Map a free-form query to the closest Behance field id; default web design."""
    q = query.lower()
    for key, fid in FIELD_IDS.items():
        if key in q:
            return fid
    if any(t in q for t in ("hotel", "restaurant", "winery", "wine", "vineyard", "cellar")):
        return FIELD_IDS["hospitality"]
    if any(t in q for t in ("dental", "clinic", "medical", "healthcare")):
        return FIELD_IDS["ui/ux"]
    if any(t in q for t in ("real estate", "realtor", "property")):
        return FIELD_IDS["architecture"]
    return FIELD_IDS["web design"]


def _first_image(html_desc: str) -> str | None:
    m = _IMG_RE.search(html_desc or "")
    return m.group(1) if m else None


def _entry_to_item(entry: ET.Element) -> ScraperItem | None:
    title_el = entry.find("title")
    link_el = entry.find("link")
    desc_el = entry.find("description")
    if title_el is None or link_el is None:
        return None
    link = (link_el.text or "").strip()
    if not link:
        return None
    # Behance project URLs end in /gallery/<id>/<slug>
    pid_match = re.search(r"/gallery/(\d+)/", link)
    pid = pid_match.group(1) if pid_match else link.rsplit("/", 1)[-1]
    image = _first_image(desc_el.text or "") if desc_el is not None else None
    return ScraperItem(
        id=f"behance_{pid}",
        title=(title_el.text or "").strip(),
        url=link,
        image_url=image,
        tags=[],
        channel=None,
        source=SOURCE,
    )


def fetch_behance(query: str, limit: int = 20, use_cache: bool = True) -> ScraperResult:
    limit = max(1, min(limit, MAX_LIMIT))
    field_id = _query_to_field_id(query)
    cache_key = f"{query}|{field_id}|{limit}"
    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    resp = requests.get(
        FEED_URL,
        params={"field": field_id, "content": "projects"},
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        timeout=30,
    )
    if resp.status_code != 200:
        logger.warning("behance feed %s: %s", resp.status_code, resp.text[:200])
        return ScraperResult(
            source=SOURCE, query=query,
            fetched_at=datetime.now(timezone.utc).isoformat(), items=[],
        )

    items: list[ScraperItem] = []
    try:
        root = ET.fromstring(resp.text)
        channel = root.find("channel")
        if channel is not None:
            for entry in channel.findall("item"):
                it = _entry_to_item(entry)
                if it is not None:
                    items.append(it)
                if len(items) >= limit:
                    break
    except ET.ParseError as exc:
        logger.warning("behance RSS parse failed: %s", exc)

    result = ScraperResult(
        source=SOURCE, query=query,
        fetched_at=datetime.now(timezone.utc).isoformat(), items=items,
    )
    _cache.set(SOURCE, cache_key, result.model_dump())
    return result


app = typer.Typer(add_completion=False, help="Behance RSS scraper.")


@app.command()
def main(
    query: str = typer.Option(..., "--query", "-q"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_behance(query=query, limit=limit, use_cache=not no_cache)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
