"""react-bits.dev component scraper.

Scrapes the site for component slugs and fetches source TSX from the
DavidHDev/react-bits GitHub repo via raw.githubusercontent.com.

KNOWN_LIMITATION: Repo layout heuristic — if a component file isn't found
at the expected path, the item is still returned without a components_tsx_path.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
import typer

from tools.scrapers import _cache
from tools.scrapers._models import ScraperItem, ScraperResult
from tools.scrapers._slug import slugify

SOURCE = "react-bits"
BASE = "https://www.reactbits.dev"
REPO_RAW = "https://raw.githubusercontent.com/DavidHDev/react-bits/main"
MAX_LIMIT = 50
ARTIFACT_ROOT = Path("data/cache/refs")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Component links: /default/Components/<Name>/... or /default/TextAnimations/<Name>
_LINK_RE = re.compile(r'href="(/default/([A-Za-z0-9]+)/([A-Za-z0-9]+))"', re.IGNORECASE)
_IMG_RE = re.compile(
    r'href="/default/[A-Za-z0-9]+/[A-Za-z0-9]+"[^>]*>.*?<img[^>]+src="([^"]+)"',
    re.IGNORECASE | re.DOTALL,
)


def _fetch_site(url: str) -> str | None:
    try:
        from scrapling.fetchers import Fetcher  # type: ignore

        resp = Fetcher().fetch(url)
    except Exception:  # noqa: BLE001
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            return r.text if r.status_code == 200 else None
        except requests.RequestException:
            return None
    if resp is None:
        return None
    for attr in ("html_content", "text", "content", "body"):
        val = getattr(resp, attr, None)
        if val:
            return val if isinstance(val, str) else val.decode("utf-8", errors="ignore")
    return None


def _fetch_raw_tsx(category: str, name: str) -> str | None:
    candidates = [
        f"{REPO_RAW}/src/content/Components/{category}/{name}/{name}.tsx",
        f"{REPO_RAW}/src/content/Components/{category}/{name}/{name}.jsx",
        f"{REPO_RAW}/src/ts-default/{category}/{name}/{name}.tsx",
        f"{REPO_RAW}/src/jsx-default/{category}/{name}/{name}.jsx",
    ]
    for url in candidates:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        except requests.RequestException:
            continue
        if r.status_code == 200 and r.text.strip():
            return r.text
    return None


def fetch_react_bits(
    query: str,
    limit: int = 20,
    use_cache: bool = True,
    artifact_root: Path = ARTIFACT_ROOT,
) -> ScraperResult:
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = f"{query}|{limit}"

    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    html = _fetch_site(BASE) or ""
    items: list[ScraperItem] = []
    q_lower = (query or "").lower()

    seen: set[str] = set()
    for href, category, name in _LINK_RE.findall(html):
        key = f"{category}/{name}"
        if key in seen:
            continue
        seen.add(key)
        if q_lower and q_lower not in key.lower():
            continue
        slug = slugify(key)
        full_url = f"{BASE}{href}"
        tsx_source = _fetch_raw_tsx(category, name)
        tsx_path: str | None = None
        if tsx_source:
            dest = Path(artifact_root) / SOURCE / slug
            dest.mkdir(parents=True, exist_ok=True)
            comp_file = dest / "components.tsx"
            comp_file.write_text(tsx_source, encoding="utf-8")
            tsx_path = str(comp_file)
        items.append(
            ScraperItem(
                id=f"react_bits_{slug}",
                title=name,
                url=full_url,
                image_url=None,
                tags=[category],
                channel="react-bits",
                source=SOURCE,
                libs_detected=["framer-motion", "gsap"],
                has_animation=True,
                components_tsx_path=tsx_path,
            )
        )
        if len(items) >= limit:
            break

    # Fill image_urls best-effort.
    img_matches = _IMG_RE.findall(html)
    for item, img in zip(items, img_matches):
        item.image_url = img

    result = ScraperResult(
        source=SOURCE,
        query=query,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )
    _cache.set(SOURCE, cache_key, result.model_dump())
    return result


app = typer.Typer(add_completion=False, help="react-bits scraper.")


@app.command()
def main(
    query: str = typer.Option("", "--query", "-q"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_react_bits(query=query, limit=limit, use_cache=not no_cache)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
