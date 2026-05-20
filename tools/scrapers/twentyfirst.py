"""21st.dev component-registry scraper.

NOTE: Module is named ``twentyfirst`` because ``21st`` is not a valid Python
identifier. CLI source name is "twentyfirst".

KNOWN_LIMITATION: 21st.dev's listing / component-source endpoints may sit
behind auth or rendering. We try plain Fetcher; if no TSX source can be
retrieved we still emit a card with image + URL (no components_tsx_path).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import typer

from tools.scrapers import _cache
from tools.scrapers._models import ScraperItem, ScraperResult
from tools.scrapers._slug import slugify_url

SOURCE = "twentyfirst"
BASE = "https://21st.dev"
SEARCH_URL = f"{BASE}/components"
MAX_LIMIT = 30
ARTIFACT_ROOT = Path("data/cache/refs")

_CARD_RE = re.compile(
    r'<a[^>]+href="(/components?/[^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)"',
    re.IGNORECASE | re.DOTALL,
)
_TSX_RE = re.compile(
    r'<pre[^>]+class="[^"]*language-(?:tsx|jsx)[^"]*"[^>]*>(.*?)</pre>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _fetch(url: str) -> str | None:
    try:
        from scrapling import fetchers as _f  # type: ignore
    except ImportError:
        return None
    for fetcher_cls_name in ("Fetcher", "StealthyFetcher"):
        cls = getattr(_f, fetcher_cls_name, None)
        if cls is None:
            continue
        try:
            resp = cls().fetch(url)
        except Exception:  # noqa: BLE001
            continue
        if resp is None:
            continue
        for attr in ("html_content", "text", "content", "body"):
            val = getattr(resp, attr, None)
            if val:
                return val if isinstance(val, str) else val.decode("utf-8", errors="ignore")
    return None


def _extract_tsx(html: str) -> str | None:
    m = _TSX_RE.search(html)
    if not m:
        return None
    body = _TAG_RE.sub("", m.group(1))
    return body.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").strip() or None


def fetch_twentyfirst(
    query: str,
    limit: int = 10,
    use_cache: bool = True,
    artifact_root: Path = ARTIFACT_ROOT,
) -> ScraperResult:
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = f"{query}|{limit}"

    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    items: list[ScraperItem] = []
    list_url = f"{SEARCH_URL}?q={query}" if query else SEARCH_URL
    html = _fetch(list_url) or ""

    seen: set[str] = set()
    for href, img in _CARD_RE.findall(html):
        if href in seen:
            continue
        seen.add(href)
        full_url = href if href.startswith("http") else f"{BASE}{href}"
        slug = slugify_url(full_url)
        tsx_path: str | None = None
        detail = _fetch(full_url)
        if detail:
            tsx = _extract_tsx(detail)
            if tsx:
                dest = Path(artifact_root) / SOURCE / slug
                dest.mkdir(parents=True, exist_ok=True)
                comp_file = dest / "components.tsx"
                comp_file.write_text(tsx, encoding="utf-8")
                tsx_path = str(comp_file)
        items.append(
            ScraperItem(
                id=f"twentyfirst_{slug}",
                title=slug.replace("-", " ").title(),
                url=full_url,
                image_url=img,
                tags=["component"],
                channel="21st.dev",
                source=SOURCE,
                libs_detected=[],
                has_animation=True,
                components_tsx_path=tsx_path,
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


app = typer.Typer(add_completion=False, help="21st.dev scraper.")


@app.command()
def main(
    query: str = typer.Option("", "--query", "-q"),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=MAX_LIMIT),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_twentyfirst(query=query, limit=limit, use_cache=not no_cache)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
