"""Unsplash search scraper.

CLI:
    uv run python -m tools.scrapers.unsplash --query "wine cellar" --limit 20

Importable:
    from tools.scrapers.unsplash import fetch_unsplash
    result = fetch_unsplash(query="...", limit=20)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests
import typer
from dotenv import load_dotenv

from tools.scrapers import _cache
from tools.scrapers._models import ScraperItem, ScraperResult

SOURCE = "unsplash"
API_URL = "https://api.unsplash.com/search/photos"
MAX_LIMIT = 30


class UnsplashAPIError(RuntimeError):
    pass


def _get_key() -> str:
    load_dotenv()
    key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not key:
        raise RuntimeError("UNSPLASH_ACCESS_KEY missing. Set it in .env.")
    return key


def _photo_to_item(p: dict[str, Any]) -> ScraperItem | None:
    pid = p.get("id")
    if not pid:
        return None
    urls = p.get("urls") or {}
    image = urls.get("regular") or urls.get("small") or urls.get("full")
    if not image:
        return None
    return ScraperItem(
        id=f"unsplash_{pid}",
        title=p.get("alt_description") or p.get("description") or "",
        url=(p.get("links") or {}).get("html") or f"https://unsplash.com/photos/{pid}",
        image_url=image,
        tags=[t.get("title", "") for t in (p.get("tags") or []) if t.get("title")],
        channel=(p.get("user") or {}).get("username"),
        source=SOURCE,
    )


def fetch_unsplash(query: str, limit: int = 20, use_cache: bool = True) -> ScraperResult:
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = f"{query}|{limit}"
    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    key = _get_key()
    resp = requests.get(
        API_URL,
        params={"query": query, "per_page": limit, "orientation": "landscape"},
        headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise UnsplashAPIError(f"Unsplash API {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    items: list[ScraperItem] = []
    for p in (data.get("results") or []):
        item = _photo_to_item(p)
        if item is not None:
            items.append(item)

    result = ScraperResult(
        source=SOURCE, query=query,
        fetched_at=datetime.now(timezone.utc).isoformat(), items=items,
    )
    _cache.set(SOURCE, cache_key, result.model_dump())
    return result


app = typer.Typer(add_completion=False, help="Unsplash reference scraper.")


@app.command()
def main(
    query: str = typer.Option(..., "--query", "-q"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_unsplash(query=query, limit=limit, use_cache=not no_cache)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
