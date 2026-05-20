"""Pinterest reference scraper.

KNOWN_LIMITATION: Pinterest is hostile to scraping (heavy JS, anti-bot,
session requirements). This scraper uses Scrapling StealthyFetcher and parses
whatever HTML it gets; if the page is empty or throttled it returns an empty
result rather than raising.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import typer

from tools.scrapers import _cache
from tools.scrapers._models import ScraperItem, ScraperResult
from tools.scrapers._slug import slugify

SOURCE = "pinterest"
SEARCH_URL = "https://www.pinterest.com/search/pins/"
MAX_LIMIT = 50
_PIN_RE = re.compile(
    r'<a[^>]+href="(/pin/(\d+)/?)"[^>]*>.*?<img\b([^>]*)>',
    re.IGNORECASE | re.DOTALL,
)
_SRC_RE = re.compile(r'src="([^"]+)"', re.IGNORECASE)
_ALT_RE = re.compile(r'alt="([^"]*)"', re.IGNORECASE)


def _stealth_get(url: str) -> str | None:
    try:
        from scrapling.fetchers import StealthyFetcher  # type: ignore
    except ImportError:
        return None
    try:
        resp = StealthyFetcher().fetch(url)
    except Exception:  # noqa: BLE001
        return None
    if resp is None:
        return None
    for attr in ("html_content", "text", "content", "body"):
        val = getattr(resp, attr, None)
        if val:
            return val if isinstance(val, str) else val.decode("utf-8", errors="ignore")
    return None


def fetch_pinterest(query: str, limit: int = 20, use_cache: bool = True) -> ScraperResult:
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = f"{query}|{limit}"

    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    items: list[ScraperItem] = []
    html = _stealth_get(f"{SEARCH_URL}?q={query}") or ""

    seen: set[str] = set()
    for path, pin_id, img_attrs in _PIN_RE.findall(html):
        if pin_id in seen:
            continue
        src_m = _SRC_RE.search(img_attrs)
        if not src_m:
            continue
        img = src_m.group(1)
        alt_m = _ALT_RE.search(img_attrs)
        alt = alt_m.group(1) if alt_m else ""
        seen.add(pin_id)
        items.append(
            ScraperItem(
                id=f"pinterest_{pin_id}",
                title=alt or None,
                url=f"https://www.pinterest.com{path}",
                image_url=img,
                tags=[slugify(query)] if query else [],
                channel="Pinterest",
                source=SOURCE,
                libs_detected=[],
                has_animation=False,
            )
        )
        if len(items) >= limit:
            break

    result = ScraperResult(
        source=SOURCE,
        query=query,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )
    _cache.set(SOURCE, cache_key, result.model_dump())
    return result


app = typer.Typer(add_completion=False, help="Pinterest scraper.")


@app.command()
def main(
    query: str = typer.Option(..., "--query", "-q"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_pinterest(query=query, limit=limit, use_cache=not no_cache)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
