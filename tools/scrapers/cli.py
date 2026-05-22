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
    behance_rss,
    codrops,
    cosmos,
    dribbble_rss,
    gsap_showcase,
    pexels,
    pinterest,
    r3f_examples,
    react_bits,
    twentyfirst,
    unsplash,
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
    "unsplash": unsplash.fetch_unsplash,
    "pexels": pexels.fetch_pexels,
    "behance": behance_rss.fetch_behance,
    "dribbble": dribbble_rss.fetch_dribbble,
}

# Per-vertical seed terms. Drives query generation + tuning per vertical.
VERTICAL_SEEDS: dict[str, list[str]] = {
    "fnb": ["wine", "winery", "vineyard", "cellar", "bottle photography", "hospitality"],
    "restaurant": ["restaurant menu", "fine dining", "hospitality brand", "bistro", "chef"],
    "dental": ["dental clinic", "healthcare brand", "medical UI", "wellness studio"],
    "realtor": ["luxury real estate", "architecture", "property brochure", "interior"],
}

# Per-vertical source weights. 0 = exclude. >1 = boost (fetch wider).
# Demote r3f for non-3D verticals (cosmic palette derails wine/restaurant brands).
SOURCE_WEIGHTS: dict[str, dict[str, float]] = {
    "fnb": {
        "arena": 1.0, "codrops": 0.5, "behance": 0.0, "dribbble": 0.0,
        "unsplash": 1.5, "pexels": 1.0,
        "r3f-examples": 0.0, "gsap-showcase": 0.3,
        "awwwards": 0.5, "cosmos": 0.5, "pinterest": 0.5,
        "twentyfirst": 0.3, "react-bits": 0.3,
    },
    "restaurant": {
        "arena": 1.0, "codrops": 0.5, "behance": 0.0, "dribbble": 0.0,
        "unsplash": 1.5, "pexels": 1.0,
        "r3f-examples": 0.0, "gsap-showcase": 0.3,
        "awwwards": 0.5, "cosmos": 0.5, "pinterest": 0.8,
        "twentyfirst": 0.3, "react-bits": 0.3,
    },
    "dental": {
        "arena": 0.7, "codrops": 0.3, "behance": 0.0, "dribbble": 0.0,
        "unsplash": 1.5, "pexels": 1.0,
        "r3f-examples": 0.0, "gsap-showcase": 0.3,
        "awwwards": 0.5, "cosmos": 0.5, "pinterest": 0.8,
        "twentyfirst": 0.5, "react-bits": 0.5,
    },
    "realtor": {
        "arena": 1.0, "codrops": 0.3, "behance": 0.0, "dribbble": 0.0,
        "unsplash": 1.5, "pexels": 1.0,
        "r3f-examples": 0.0, "gsap-showcase": 0.3,
        "awwwards": 0.5, "cosmos": 0.5, "pinterest": 0.8,
        "twentyfirst": 0.3, "react-bits": 0.3,
    },
}


def _weight_for(vertical: str, source: str) -> float:
    return SOURCE_WEIGHTS.get(vertical, {}).get(source, 1.0)


def build_queries(
    vertical: str,
    style: str,
    keywords_path: str | None = None,
) -> list[str]:
    """Per-vertical seed terms + style modifier.

    If `keywords_path` is provided and the file exists, prefer NLP-extracted
    keywords (with style prefix). Falls back to static `VERTICAL_SEEDS`.
    """
    v = vertical.strip().lower()
    s = (style or "modern").strip()

    nlp_keywords: list[str] = []
    if keywords_path:
        try:
            import json as _json
            kpath = __import__("pathlib").Path(keywords_path)
            if kpath.exists():
                data = _json.loads(kpath.read_text(encoding="utf-8"))
                nlp_keywords = [
                    k.strip().lower()
                    for k in (data.get("keywords") or [])
                    if isinstance(k, str) and k.strip()
                ]
                bucket_extra = [
                    t.strip().lower()
                    for t in (data.get("bucket_tokens") or [])
                    if isinstance(t, str) and t.strip()
                ]
                # Promote bucket tokens to the front
                nlp_keywords = bucket_extra + nlp_keywords
        except Exception as exc:  # noqa: BLE001
            log.warning("keywords.json load failed: %s — falling back to seeds", exc)

    seeds: list[str]
    if nlp_keywords:
        seeds = nlp_keywords
    else:
        seeds = VERTICAL_SEEDS.get(v) or [v]

    queries: list[str] = []
    for seed in seeds[:8]:
        queries.append(f"{s} {seed}")
        queries.append(f"{seed} brand")
    queries.append(f"{s} {v} website")
    # Dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        ql = q.lower().strip()
        if not ql or ql in seen:
            continue
        seen.add(ql)
        out.append(q)
    return out


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
    keywords_path: str | None = None,
) -> dict:
    """Programmatic entry point; returns the final combined payload dict.

    Per-vertical source weights govern whether a source runs and how wide:
    - weight 0 → source skipped entirely (e.g. r3f for non-3D verticals)
    - weight >=1 → fetches at least 1 query; ~max(1, weight*queries_count)
    """
    queries = build_queries(vertical, style, keywords_path=keywords_path)
    sources = {source_only: SOURCES[source_only]} if source_only else dict(SOURCES)

    all_items: list[ScraperItem] = []
    by_source: dict[str, int] = {name: 0 for name in sources}

    for name, fn in sources.items():
        w = _weight_for(vertical, name) if not source_only else 1.0
        if w <= 0:
            continue
        # Scale how many query variants this source consumes.
        per_source_queries = queries if w >= 1.0 else queries[:max(1, int(len(queries) * w))]
        # Per-query item cap scales with weight (mild boost for heavy weights)
        per_query_limit = max(8, int(limit * min(w, 1.5)))
        for q in per_source_queries:
            try:
                result = fn(query=q, limit=per_query_limit, use_cache=use_cache)
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
