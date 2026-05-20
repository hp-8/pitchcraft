"""Codrops reference scraper (WordPress REST API).

CLI:
    uv run python -m tools.scrapers.codrops --query "scroll animation" --limit 10
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import requests
import typer

from tools.scrapers import _cache
from tools.scrapers._models import ScraperItem, ScraperResult

SOURCE = "codrops"
API_URL = "https://tympanus.net/codrops/wp-json/wp/v2/posts"
MAX_LIMIT = 50
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
_GITHUB_RE = re.compile(r'href="(https://github\.com/codrops[^"]+)"', re.IGNORECASE)


def _post_to_item(post: dict[str, Any]) -> ScraperItem | None:
    post_id = post.get("id")
    link = post.get("link")
    if post_id is None or not link:
        return None
    title_obj = post.get("title") or {}
    title = title_obj.get("rendered") if isinstance(title_obj, dict) else None

    image_url: str | None = None
    embedded = post.get("_embedded") or {}
    media = embedded.get("wp:featuredmedia") or []
    if media and isinstance(media, list):
        first = media[0] or {}
        image_url = first.get("source_url") or (
            (first.get("media_details") or {}).get("sizes", {}).get("full", {}).get("source_url")
        )

    tags: list[str] = []
    terms = embedded.get("wp:term") or []
    if isinstance(terms, list):
        for group in terms:
            if isinstance(group, list):
                for term in group:
                    name = (term or {}).get("name")
                    if name:
                        tags.append(str(name))

    content = (post.get("content") or {}).get("rendered") or ""
    for match in _GITHUB_RE.findall(content):
        tags.append(f"repo:{match}")

    return ScraperItem(
        id=f"codrops_{post_id}",
        title=title,
        url=link,
        image_url=image_url,
        tags=tags,
        channel="Codrops",
        source=SOURCE,
        libs_detected=[],
        has_animation=True,
    )


def fetch_codrops(query: str, limit: int = 20, use_cache: bool = True) -> ScraperResult:
    """Fetch articles from Codrops WP REST API."""
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = f"{query}|{limit}"

    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    items: list[ScraperItem] = []
    try:
        resp = requests.get(
            API_URL,
            params={"search": query, "per_page": limit, "_embed": 1},
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                for post in data:
                    item = _post_to_item(post)
                    if item is not None:
                        items.append(item)
    except (requests.RequestException, ValueError):
        items = []

    result = ScraperResult(
        source=SOURCE,
        query=query,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )
    _cache.set(SOURCE, cache_key, result.model_dump())
    return result


app = typer.Typer(add_completion=False, help="Codrops scraper.")


@app.command()
def main(
    query: str = typer.Option(..., "--query", "-q"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_codrops(query=query, limit=limit, use_cache=not no_cache)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
