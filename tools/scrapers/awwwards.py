"""Awwwards reference scraper (Scrapling StealthyFetcher + Playwright capture).

KNOWN_LIMITATION: Awwwards aggressively rate-limits and Cloudflare-protects.
If StealthyFetcher cannot retrieve the listing page, this scraper returns an
empty result rather than raising. Also, detail-page external URL extraction is
best-effort; we may fall back to capturing the Awwwards detail page itself.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import typer

from tools.scrapers import _cache, _capture
from tools.scrapers._models import ScraperItem, ScraperResult
from tools.scrapers._slug import slugify_url

SOURCE = "awwwards"
LIST_URL = "https://www.awwwards.com/websites/"
MAX_LIMIT = 30
_DETAIL_RE = re.compile(r'href="(/sites/[a-z0-9\-]+)"', re.IGNORECASE)
_EXTERNAL_RE = re.compile(r'href="(https?://[^"\']+)"[^>]*class="[^"]*website-button', re.I)
_IMG_RE = re.compile(r'<img[^>]+(?:data-src|src)="([^"]+)"', re.IGNORECASE)


def _stealth_get(url: str) -> str | None:
    try:
        from scrapling.fetchers import StealthyFetcher  # type: ignore
    except ImportError:
        return None
    try:
        fetcher = StealthyFetcher()
        resp = fetcher.fetch(url)
    except Exception:  # noqa: BLE001
        return None
    if resp is None:
        return None
    for attr in ("html_content", "text", "content", "body"):
        val = getattr(resp, attr, None)
        if val:
            return val if isinstance(val, str) else val.decode("utf-8", errors="ignore")
    return None


def _parse_list(html: str, limit: int) -> list[str]:
    seen: list[str] = []
    for match in _DETAIL_RE.findall(html):
        full = f"https://www.awwwards.com{match}"
        if full not in seen:
            seen.append(full)
        if len(seen) >= limit:
            break
    return seen


def _extract_external(html: str) -> str | None:
    m = _EXTERNAL_RE.search(html)
    return m.group(1) if m else None


def _extract_thumbnail(html: str) -> str | None:
    m = _IMG_RE.search(html)
    return m.group(1) if m else None


def fetch_awwwards(
    query: str,
    limit: int = 10,
    use_cache: bool = True,
    do_capture: bool = False,
) -> ScraperResult:
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = f"{query}|{limit}|cap={int(do_capture)}"

    if use_cache:
        cached = _cache.get(SOURCE, cache_key)
        if cached is not None:
            return ScraperResult.model_validate(cached)

    items: list[ScraperItem] = []
    list_url = f"{LIST_URL}?text={query}" if query else LIST_URL
    html = _stealth_get(list_url)

    if html:
        detail_urls = _parse_list(html, limit)
        for detail_url in detail_urls:
            detail_html = _stealth_get(detail_url) or ""
            external = _extract_external(detail_html) or detail_url
            thumb = _extract_thumbnail(detail_html)
            slug = slugify_url(detail_url)
            preview_path: str | None = None
            libs: list[str] = []
            has_animation = True
            if do_capture:
                try:
                    cap = _capture.capture_url(
                        external, slug=slug, source=SOURCE, scroll_seconds=10
                    )
                    preview_path = cap.video_path
                    if not thumb:
                        thumb = cap.thumbnail_path
                    libs = cap.libs_detected
                    has_animation = cap.has_animation
                except Exception:  # noqa: BLE001
                    pass
            items.append(
                ScraperItem(
                    id=f"awwwards_{slug}",
                    title=slug.replace("-", " ").title(),
                    url=detail_url,
                    image_url=thumb,
                    tags=[],
                    channel="Awwwards",
                    source=SOURCE,
                    libs_detected=libs,
                    has_animation=has_animation,
                    preview_mp4_path=preview_path,
                )
            )

    result = ScraperResult(
        source=SOURCE,
        query=query,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )
    _cache.set(SOURCE, cache_key, result.model_dump())
    return result


app = typer.Typer(add_completion=False, help="Awwwards scraper.")


@app.command()
def main(
    query: str = typer.Option("", "--query", "-q"),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=MAX_LIMIT),
    capture: bool = typer.Option(False, "--capture", help="Run Playwright capture per site."),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_awwwards(query=query, limit=limit, use_cache=not no_cache, do_capture=capture)
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
