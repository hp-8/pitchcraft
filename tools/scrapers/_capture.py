"""Shared Playwright capture utility for design-reference scrapers.

Loads a URL in headless Chromium, records a scroll-through video, detects
animation libraries, extracts CSS @keyframes counts, captures a thumbnail,
and persists artifacts to ``{artifact_root}/{source}/{slug}/``.

Video output is WebM (Playwright's native format). MP4 conversion would
require ffmpeg; we skip that dep and keep the WebM. The file is saved as
``preview.mp4`` per spec when the source is actually MP4, else ``preview.webm``.

CLI:
    uv run python -m tools.scrapers._capture \\
        --url https://gsap.com --slug gsap-home --source gsap-showcase \\
        --scroll-seconds 8
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer

from tools.scrapers._models import CaptureResult

# JS injected to read animation signals before any scroll-driven unload.
DETECT_JS = r"""
() => ({
  libs: {
    gsap: typeof window.gsap !== "undefined" || !!document.querySelector('script[src*="gsap"]'),
    lenis: typeof window.Lenis !== "undefined" || !!document.querySelector('script[src*="lenis"]') || document.documentElement.hasAttribute("data-lenis"),
    three: typeof window.THREE !== "undefined" || !!document.querySelector('script[src*="three"]'),
    motion: typeof window.motion !== "undefined" || !!document.querySelector('script[src*="motion"]') || !!document.querySelector('script[src*="framer-motion"]'),
    lottie: typeof window.lottie !== "undefined" || !!document.querySelector('script[src*="lottie"]'),
    locomotive: !!document.querySelector('script[src*="locomotive-scroll"]') || !!document.querySelector('[data-scroll-container]'),
    barba: typeof window.barba !== "undefined",
  },
  keyframes_count: Array.from(document.styleSheets).reduce((acc, s) => {
    try { return acc + Array.from(s.cssRules || []).filter(r => r.type === 7).length; } catch (e) { return acc; }
  }, 0),
  has_smooth_scroll_attr: document.documentElement.hasAttribute('data-scroll') || document.documentElement.hasAttribute('data-lenis'),
})
"""


class CaptureError(RuntimeError):
    """Raised when Playwright itself is unavailable / browser uninstalled."""


def derive_has_animation(
    libs_detected: list[str], keyframes_count: int, has_scroll_attr: bool
) -> bool:
    """Pure helper: animation present if any lib, keyframe, or scroll attr."""
    return bool(libs_detected) or keyframes_count > 0 or bool(has_scroll_attr)


def extract_libs(raw: dict[str, Any]) -> list[str]:
    """Pure helper: convert ``{libs: {name: bool}}`` into list of truthy names."""
    libs = (raw or {}).get("libs") or {}
    return sorted(name for name, present in libs.items() if present)


def _artifact_dir(artifact_root: str, source: str, slug: str) -> Path:
    return Path(artifact_root) / source / slug


def _import_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: WPS433
    except ImportError as exc:  # pragma: no cover - environment issue
        raise CaptureError(
            "Playwright not installed. Run: uv add playwright && uv run playwright install chromium"
        ) from exc
    return sync_playwright


def _auto_scroll_js(scroll_seconds: int) -> str:
    return f"""
    async () => {{
      const totalMs = {scroll_seconds * 1000};
      const stepMs = 33;
      const steps = Math.max(1, Math.floor(totalMs / stepMs));
      const max = () => Math.max(
        document.body.scrollHeight, document.documentElement.scrollHeight
      ) - window.innerHeight;
      for (let i = 1; i <= steps; i++) {{
        const target = Math.floor(max() * (i / steps));
        window.scrollTo(0, target);
        await new Promise(r => setTimeout(r, stepMs));
      }}
      await new Promise(r => setTimeout(r, 500));
      window.scrollTo({{top: 0, behavior: 'smooth'}});
      await new Promise(r => setTimeout(r, 1000));
    }}
    """


def capture_url(
    url: str,
    slug: str,
    source: str,
    artifact_root: str = "data/cache/refs",
    scroll_seconds: int = 10,
    viewport: tuple[int, int] = (1440, 900),
    timeout_ms: int = 45000,
) -> CaptureResult:
    """Capture a URL: video + thumbnail + animation signals + meta.json."""
    sync_playwright = _import_playwright()
    artifact_dir = _artifact_dir(artifact_root, source, slug)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    captured_at = datetime.now(timezone.utc).isoformat()

    error: str | None = None
    libs_detected: list[str] = []
    keyframes_count = 0
    has_scroll_attr = False
    video_path: Path | None = None
    thumbnail_path: Path | None = None

    width, height = viewport

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(artifact_dir),
            record_video_size={"width": width, "height": height},
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="load", timeout=timeout_ms)
            page.wait_for_timeout(1500)

            try:
                raw = page.evaluate(DETECT_JS)
            except Exception as exc:  # noqa: BLE001
                raw = {}
                error = f"detect_js_failed: {exc}"
            libs_detected = extract_libs(raw)
            keyframes_count = int(raw.get("keyframes_count") or 0)
            has_scroll_attr = bool(raw.get("has_smooth_scroll_attr"))

            thumb = artifact_dir / "thumbnail.jpg"
            try:
                page.screenshot(path=str(thumb), full_page=False, type="jpeg", quality=80)
                thumbnail_path = thumb
            except Exception as exc:  # noqa: BLE001
                error = error or f"screenshot_failed: {exc}"

            try:
                page.evaluate(_auto_scroll_js(scroll_seconds))
            except Exception as exc:  # noqa: BLE001
                error = error or f"scroll_failed: {exc}"
        except Exception as exc:  # noqa: BLE001
            error = error or f"page_error: {exc}"
        finally:
            video_handle = page.video
            for closer in (page.close, context.close, browser.close):
                try:
                    closer()
                except Exception:  # noqa: BLE001
                    pass
            if video_handle is not None:
                try:
                    raw_video = Path(video_handle.path())
                    if raw_video.exists():
                        target = "preview.mp4" if raw_video.suffix.lower() == ".mp4" else "preview.webm"
                        dest = artifact_dir / target
                        shutil.move(str(raw_video), str(dest))
                        video_path = dest
                except Exception as exc:  # noqa: BLE001
                    error = error or f"video_finalize_failed: {exc}"

    has_animation = derive_has_animation(libs_detected, keyframes_count, has_scroll_attr)
    result = CaptureResult(
        url=url,
        source=source,
        slug=slug,
        captured_at=captured_at,
        artifact_dir=str(artifact_dir),
        video_path=str(video_path) if video_path else None,
        thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
        libs_detected=libs_detected,
        keyframes_count=keyframes_count,
        has_animation=has_animation,
        error=error,
    )

    meta = {
        "url": url,
        "source": source,
        "slug": slug,
        "captured_at": captured_at,
        "viewport": [width, height],
        "scroll_seconds": scroll_seconds,
        "libs_detected": libs_detected,
        "keyframes_count": keyframes_count,
        "has_smooth_scroll_attr": has_scroll_attr,
        "has_animation": has_animation,
        "video_filename": video_path.name if video_path else None,
        "thumbnail_filename": thumbnail_path.name if thumbnail_path else None,
        "error": error,
    }
    (artifact_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return result


app = typer.Typer(add_completion=False, help="Playwright capture utility.")


def _parse_viewport(value: str) -> tuple[int, int]:
    try:
        w, h = value.lower().split("x")
        return int(w), int(h)
    except Exception as exc:  # noqa: BLE001
        raise typer.BadParameter("viewport must be WIDTHxHEIGHT, e.g. 1440x900") from exc


@app.command()
def main(
    url: str = typer.Option(..., "--url"),
    slug: str = typer.Option(..., "--slug"),
    source: str = typer.Option(..., "--source"),
    artifact_root: str = typer.Option("data/cache/refs", "--artifact-root"),
    scroll_seconds: int = typer.Option(10, "--scroll-seconds", min=1, max=60),
    viewport: str = typer.Option("1440x900", "--viewport"),
) -> None:
    """Capture a single URL and emit the CaptureResult as JSON."""
    vp = _parse_viewport(viewport)
    result = capture_url(
        url=url,
        slug=slug,
        source=source,
        artifact_root=artifact_root,
        scroll_seconds=scroll_seconds,
        viewport=vp,
    )
    typer.echo(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
