"""Dribbble RSS scraper.

Public OAuth restricted; public RSS still works:
- Popular: https://dribbble.com/shots/popular.rss
- By tag:  https://dribbble.com/tags/<tag>.rss  (where supported)

CLI:
    uv run python -m tools.scrapers.dribbble_rss --query "restaurant" --limit 20
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

SOURCE = "dribbble"
POPULAR_URL = "https://dribbble.com/shots/popular.rss"
TAG_URL = "https://dribbble.com/tags/{tag}.rss"
MAX_LIMIT = 50

_IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.I)
_TAG_NORM_RE = re.compile(r"[^a-z0-9]+")


def _normalize_tag(query: str) -> str:
    """First word of query, lowercased + slugified, used as Dribbble tag."""
    first = query.split()[0] if query.split() else "design"
    return _TAG_NORM_RE.sub("", first.lower()) or "design"


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
    pid_match = re.search(r"/shots/(\d+)", link)
    pid = pid_match.group(1) if pid_match else link.rsplit("/", 1)[-1]
    image = _first_image(desc_el.text or "") if desc_el is not None else None
    return ScraperItem(
        id=f"dribbble_{pid}",
        title=(title_el.text or "").strip(),
        url=link,
        image_url=image,
        tags=[],
        channel=None,
        source=SOURCE,
    )


def _fetch_feed(url: str) -> str | None:
    resp = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        timeout=30,
    )
    if resp.status_code != 200:
        logger.warning("dribbble feed %s: %s", resp.status_code, url)
        return None
    return resp.text


def fetch_dribbble(query: str, limit: int = 20, use_cache: bool = True) -> ScraperResult:
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = f"{query}|{limit}"
    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    items: list[ScraperItem] = []

    # Try tag feed first
    tag = _normalize_tag(query)
    text = _fetch_feed(TAG_URL.format(tag=tag))

    # Fallback to popular feed if tag returned nothing or 404
    if not text:
        text = _fetch_feed(POPULAR_URL)

    if text:
        try:
            root = ET.fromstring(text)
            channel = root.find("channel")
            if channel is not None:
                for entry in channel.findall("item"):
                    it = _entry_to_item(entry)
                    if it is not None:
                        items.append(it)
                    if len(items) >= limit:
                        break
        except ET.ParseError as exc:
            logger.warning("dribbble RSS parse failed: %s", exc)

    result = ScraperResult(
        source=SOURCE, query=query,
        fetched_at=datetime.now(timezone.utc).isoformat(), items=items,
    )
    _cache.set(SOURCE, cache_key, result.model_dump())
    return result


app = typer.Typer(add_completion=False, help="Dribbble RSS scraper.")


@app.command()
def main(
    query: str = typer.Option(..., "--query", "-q"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_dribbble(query=query, limit=limit, use_cache=not no_cache)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
