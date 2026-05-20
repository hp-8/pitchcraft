"""Are.na reference scraper.

CLI:
    uv run python -m tools.scrapers.arena --query "modern restaurant landing" --limit 20

Importable:
    from tools.scrapers.arena import fetch_arena
    result = fetch_arena(query="...", limit=20, use_cache=True)
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

SOURCE = "arena"
API_URL = "https://api.are.na/v2/search"
MAX_LIMIT = 100


class ArenaAPIError(RuntimeError):
    """Raised when Are.na API returns a non-200 response."""


def _get_token() -> str:
    load_dotenv()
    token = os.getenv("ARENA_ACCESS_TOKEN")
    if not token:
        raise RuntimeError(
            "ARENA_ACCESS_TOKEN missing. Set it in .env (see .env.example)."
        )
    return token


def _best_image(block: dict[str, Any]) -> str | None:
    image = block.get("image") or {}
    for key in ("large", "original", "display", "square", "thumb"):
        node = image.get(key) or {}
        url = node.get("url")
        if url:
            return url
    src = block.get("source") or {}
    return src.get("url")


def _block_to_item(block: dict[str, Any]) -> ScraperItem | None:
    block_id = block.get("id")
    if block_id is None:
        return None
    image_url = _best_image(block)
    if not image_url:
        return None
    channel = None
    connections = block.get("connections") or []
    if connections:
        channel = connections[0].get("title")
    return ScraperItem(
        id=f"arena_{block_id}",
        title=block.get("title") or block.get("generated_title"),
        url=f"https://www.are.na/block/{block_id}",
        image_url=image_url,
        tags=[],
        channel=channel,
        source=SOURCE,
    )


def fetch_arena(query: str, limit: int = 20, use_cache: bool = True) -> ScraperResult:
    """Fetch design references from Are.na, with optional SQLite cache."""
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = f"{query}|{limit}"

    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    token = _get_token()
    resp = requests.get(
        API_URL,
        params={"q": query, "per": limit},
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": "application/json",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        snippet = resp.text[:200]
        raise ArenaAPIError(f"Are.na API {resp.status_code}: {snippet}")

    data = resp.json()
    blocks = data.get("blocks") or data.get("results") or []
    items: list[ScraperItem] = []
    for block in blocks:
        item = _block_to_item(block)
        if item is not None:
            items.append(item)

    result = ScraperResult(
        source=SOURCE,
        query=query,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )
    _cache.set(SOURCE, cache_key, result.model_dump())
    return result


app = typer.Typer(add_completion=False, help="Are.na reference scraper.")


@app.command()
def main(
    query: str = typer.Option(..., "--query", "-q", help="Search query."),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass SQLite cache."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    """Run the scraper and emit JSON to stdout."""
    result = fetch_arena(query=query, limit=limit, use_cache=not no_cache)
    payload = result.model_dump()
    indent = 2 if pretty else None
    typer.echo(json.dumps(payload, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    app()
