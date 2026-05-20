"""react-three-fiber examples scraper.

Scrapes the pmndrs docs examples page and pulls CodeSandbox embeds.
Each item links to the sandbox URL with the auto-generated screenshot.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import requests
import typer

from tools.scrapers import _cache
from tools.scrapers._models import ScraperItem, ScraperResult

SOURCE = "r3f-examples"
EXAMPLES_URL = "https://docs.pmnd.rs/react-three-fiber/getting-started/examples"
MAX_LIMIT = 50
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# CodeSandbox URL patterns
_SANDBOX_RE = re.compile(
    r'https?://codesandbox\.io/(?:s|p/sandbox|embed)/(?:[a-z0-9\-]+/)?([a-z0-9\-]+)',
    re.IGNORECASE,
)
_LINK_TITLE_RE = re.compile(
    r'<a[^>]+href="(https?://codesandbox\.io/[^"]+)"[^>]*>([^<]+)</a>',
    re.IGNORECASE,
)


def _fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        return r.text if r.status_code == 200 else None
    except requests.RequestException:
        return None


def fetch_r3f_examples(
    query: str = "",
    limit: int = 20,
    use_cache: bool = True,
) -> ScraperResult:
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = f"{query}|{limit}"

    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    html = _fetch(EXAMPLES_URL) or ""
    items: list[ScraperItem] = []
    q_lower = (query or "").lower()

    titled: list[tuple[str, str]] = _LINK_TITLE_RE.findall(html)
    seen: set[str] = set()
    for url, title in titled:
        m = _SANDBOX_RE.search(url)
        if not m:
            continue
        sandbox_id = m.group(1)
        if sandbox_id in seen:
            continue
        seen.add(sandbox_id)
        if q_lower and q_lower not in (title.lower() + sandbox_id.lower()):
            continue
        items.append(
            ScraperItem(
                id=f"r3f_{sandbox_id}",
                title=title.strip() or sandbox_id,
                url=url,
                image_url=f"https://codesandbox.io/api/v1/sandboxes/{sandbox_id}/screenshot.png",
                tags=["3d", "r3f"],
                channel="react-three-fiber",
                source=SOURCE,
                libs_detected=["three", "react-three-fiber"],
                has_animation=True,
            )
        )
        if len(items) >= limit:
            break

    if not items:
        # Fallback: untitled sandbox links anywhere on the page.
        for m in _SANDBOX_RE.finditer(html):
            sandbox_id = m.group(1)
            if sandbox_id in seen:
                continue
            seen.add(sandbox_id)
            items.append(
                ScraperItem(
                    id=f"r3f_{sandbox_id}",
                    title=sandbox_id,
                    url=f"https://codesandbox.io/s/{sandbox_id}",
                    image_url=f"https://codesandbox.io/api/v1/sandboxes/{sandbox_id}/screenshot.png",
                    tags=["3d", "r3f"],
                    channel="react-three-fiber",
                    source=SOURCE,
                    libs_detected=["three", "react-three-fiber"],
                    has_animation=True,
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


app = typer.Typer(add_completion=False, help="r3f examples scraper.")


@app.command()
def main(
    query: str = typer.Option("", "--query", "-q"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_r3f_examples(query=query, limit=limit, use_cache=not no_cache)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
