"""GSAP showcase scraper (with optional Playwright capture).

KNOWN_LIMITATION: GSAP showcase layout is client-rendered. We attempt Fetcher
then StealthyFetcher; if neither yields card links, returns empty result.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import typer

from tools.scrapers import _cache, _capture
from tools.scrapers._models import ScraperItem, ScraperResult
from tools.scrapers._slug import slugify_url

SOURCE = "gsap-showcase"
LIST_URL = "https://gsap.com/showcase/"
MAX_LIMIT = 30
# External-site links on the showcase page.
_LINK_RE = re.compile(r'href="(https?://(?!gsap\.com)[^"\']+)"', re.IGNORECASE)
_IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.IGNORECASE)


def _fetch(url: str) -> str | None:
    try:
        from scrapling import fetchers as f  # type: ignore
    except ImportError:
        return None
    for cls_name in ("Fetcher", "StealthyFetcher"):
        cls = getattr(f, cls_name, None)
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


def fetch_gsap_showcase(
    query: str = "",
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

    html = _fetch(LIST_URL) or ""
    items: list[ScraperItem] = []

    images = _IMG_RE.findall(html)
    seen: set[str] = set()
    for ext_url in _LINK_RE.findall(html):
        if ext_url in seen:
            continue
        seen.add(ext_url)
        slug = slugify_url(ext_url)
        if query and query.lower() not in (ext_url.lower() + slug):
            continue
        thumbnail = images[len(items)] if len(items) < len(images) else None
        preview_path: str | None = None
        libs: list[str] = ["gsap"]
        has_animation = True
        if do_capture:
            try:
                cap = _capture.capture_url(ext_url, slug=slug, source=SOURCE, scroll_seconds=10)
                preview_path = cap.video_path
                thumbnail = thumbnail or cap.thumbnail_path
                libs = sorted(set(libs) | set(cap.libs_detected))
                has_animation = cap.has_animation or has_animation
            except Exception:  # noqa: BLE001
                pass
        items.append(
            ScraperItem(
                id=f"gsap_{slug}",
                title=slug.replace("-", " ").title(),
                url=ext_url,
                image_url=thumbnail,
                tags=["gsap"],
                channel="GSAP Showcase",
                source=SOURCE,
                libs_detected=libs,
                has_animation=has_animation,
                preview_mp4_path=preview_path,
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


app = typer.Typer(add_completion=False, help="GSAP showcase scraper.")


@app.command()
def main(
    query: str = typer.Option("", "--query", "-q"),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=MAX_LIMIT),
    capture: bool = typer.Option(False, "--capture"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    result = fetch_gsap_showcase(
        query=query, limit=limit, use_cache=not no_cache, do_capture=capture
    )
    typer.echo(json.dumps(result.model_dump(), indent=2 if pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    app()
