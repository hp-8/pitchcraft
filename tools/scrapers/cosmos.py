"""Cosmos.so reference scraper.

KNOWN_LIMITATION: Cosmos is heavily client-rendered (Next.js) and applies
anti-bot. StealthyFetcher may still fail to receive populated HTML. On failure
this scraper returns an empty result rather than raising.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import typer

from tools.scrapers import _cache
from tools.scrapers._models import ScraperItem, ScraperResult
from tools.scrapers._slug import slugify_url

SOURCE = "cosmos"
SEARCH_URL = "https://www.cosmos.so/search"
MAX_LIMIT = 50
# Cosmos cards: <a href="/e/<id>"><img src="..." alt="..." /></a>
_CARD_RE = re.compile(
    r'<a[^>]+href="(/(?:e|c|p)/[a-z0-9\-]+)"[^>]*>\s*<img\b([^>]*)>',
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


def fetch_cosmos(query: str, limit: int = 20, use_cache: bool = True) -> ScraperResult:
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = f"{query}|{limit}"

    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    items: list[ScraperItem] = []
    url = f"{SEARCH_URL}?q={query}"
    html = _stealth_get(url) or ""

    seen_urls: set[str] = set()
    for path, img_attrs in _CARD_RE.findall(html):
        full_url = f"https://www.cosmos.so{path}"
        if full_url in seen_urls:
            continue
        src_m = _SRC_RE.search(img_attrs)
        if not src_m:
            continue
        img = src_m.group(1)
        alt_m = _ALT_RE.search(img_attrs)
        alt = alt_m.group(1) if alt_m else ""
        seen_urls.add(full_url)
        slug = slugify_url(full_url)
        items.append(
            ScraperItem(
                id=f"cosmos_{slug}",
                title=alt or None,
                url=full_url,
                image_url=img,
                tags=[],
                channel="Cosmos",
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


app = typer.Typer(add_completion=False, help="Cosmos.so scraper.")


@app.command()
def main(
    query: str = typer.Option(..., "--query", "-q"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_cosmos(query=query, limit=limit, use_cache=not no_cache)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
