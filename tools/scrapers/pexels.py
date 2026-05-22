"""Pexels search scraper.

CLI:
    uv run python -m tools.scrapers.pexels --query "wine bottle" --limit 20
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

SOURCE = "pexels"
API_URL = "https://api.pexels.com/v1/search"
MAX_LIMIT = 80


class PexelsAPIError(RuntimeError):
    pass


def _get_key() -> str:
    load_dotenv()
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("PEXELS_API_KEY missing. Set it in .env.")
    return key


def _photo_to_item(p: dict[str, Any]) -> ScraperItem | None:
    pid = p.get("id")
    if not pid:
        return None
    src = p.get("src") or {}
    image = src.get("large") or src.get("medium") or src.get("original")
    if not image:
        return None
    return ScraperItem(
        id=f"pexels_{pid}",
        title=p.get("alt") or "",
        url=p.get("url") or f"https://www.pexels.com/photo/{pid}",
        image_url=image,
        tags=[],
        channel=p.get("photographer"),
        source=SOURCE,
    )


def fetch_pexels(query: str, limit: int = 20, use_cache: bool = True) -> ScraperResult:
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
        headers={"Authorization": key},
        timeout=30,
    )
    if resp.status_code != 200:
        raise PexelsAPIError(f"Pexels API {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    items: list[ScraperItem] = []
    for p in (data.get("photos") or []):
        item = _photo_to_item(p)
        if item is not None:
            items.append(item)

    result = ScraperResult(
        source=SOURCE, query=query,
        fetched_at=datetime.now(timezone.utc).isoformat(), items=items,
    )
    _cache.set(SOURCE, cache_key, result.model_dump())
    return result


app = typer.Typer(add_completion=False, help="Pexels reference scraper.")


@app.command()
def main(
    query: str = typer.Option(..., "--query", "-q"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_pexels(query=query, limit=limit, use_cache=not no_cache)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
