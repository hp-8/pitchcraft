"""Unified design-reference scraper CLI.

Usage:
    uv run python -m tools.scrapers.cli --vertical restaurant --style modern --limit 30

Runs every reference scraper across a small set of vertical+style query
variations, dedupes by image_url and url-hostname+path, optionally promotes
motion-rich items, caps to --limit, and emits a single combined JSON.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Callable, Dict
from urllib.parse import urlparse

import typer

from tools.scrapers import (
    arena,
    awwwards,
    codrops,
    cosmos,
    gsap_showcase,
    pinterest,
    r3f_examples,
    react_bits,
    twentyfirst,
)
from tools.scrapers._models import ScraperItem, ScraperResult

log = logging.getLogger("scrapers.cli")

SOURCES: Dict[str, Callable[..., ScraperResult]] = {
    "arena": arena.fetch_arena,
    "codrops": codrops.fetch_codrops,
    "awwwards": awwwards.fetch_awwwards,
    "cosmos": cosmos.fetch_cosmos,
    "pinterest": pinterest.fetch_pinterest,
    "twentyfirst": twentyfirst.fetch_twentyfirst,
    "react-bits": react_bits.fetch_react_bits,
    "gsap-showcase": gsap_showcase.fetch_gsap_showcase,
    "r3f-examples": r3f_examples.fetch_r3f_examples,
}


def build_queries(vertical: str, style: str) -> list[str]:
    """Generate 3-5 query variants for a vertical+style combo."""
    v = vertical.strip()
    s = (style or "modern").strip()
    return [
        f"{s} {v} landing page",
        f"{v} hero animation",
        f"{s} {v} website",
        f"{v} interactive design",
        f"{s} {v} brand site",
    ]


def _dedupe_key(item: ScraperItem) -> tuple[str, str]:
    img = (item.image_url or "").strip().lower()
    parsed = urlparse(item.url or "")
    url_key = f"{parsed.netloc}{parsed.path}".lower()
    return (img, url_key)


def _is_motion(item: ScraperItem) -> bool:
    return bool(item.has_animation) or bool(item.libs_detected)


def run(
    vertical: str,
    style: str = "modern",
    limit: int = 30,
    include_motion: bool = False,
    use_cache: bool = True,
    source_only: str | None = None,
) -> dict:
    """Programmatic entry point; returns the final combined payload dict."""
    queries = build_queries(vertical, style)
    sources = {source_only: SOURCES[source_only]} if source_only else SOURCES

    all_items: list[ScraperItem] = []
    by_source: dict[str, int] = {name: 0 for name in sources}

    for name, fn in sources.items():
        for q in queries:
            try:
                result = fn(query=q, limit=limit, use_cache=use_cache)
            except Exception as exc:  # noqa: BLE001
                log.warning("scraper %s failed for q=%r: %s", name, q, exc)
                continue
            for item in result.items:
                all_items.append(item)
            by_source[name] += len(result.items)

    # Dedupe preserving first occurrence.
    seen: set[tuple[str, str]] = set()
    deduped: list[ScraperItem] = []
    for item in all_items:
        key = _dedupe_key(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    # Sort: motion-rich first if requested; else stable.
    if include_motion:
        deduped.sort(key=lambda i: 0 if _is_motion(i) else 1)

    capped = deduped[: max(1, limit)]

    return {
        "vertical": vertical,
        "style": style,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "by_source": by_source,
        "items": [i.model_dump() for i in capped],
    }


app = typer.Typer(add_completion=False, help="Unified reference scraper.")


@app.command()
def main(
    vertical: str = typer.Option(..., "--vertical", help="Business vertical."),
    style: str = typer.Option("modern", "--style"),
    limit: int = typer.Option(30, "--limit", "-n", min=1, max=500),
    include_motion: bool = typer.Option(False, "--include-motion"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
    source_only: str | None = typer.Option(None, "--source-only"),
) -> None:
    if source_only and source_only not in SOURCES:
        raise typer.BadParameter(
            f"unknown source: {source_only}. one of: {', '.join(SOURCES)}"
        )
    payload = run(
        vertical=vertical,
        style=style,
        limit=limit,
        include_motion=include_motion,
        use_cache=not no_cache,
        source_only=source_only,
    )
    typer.echo(json.dumps(payload, indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
