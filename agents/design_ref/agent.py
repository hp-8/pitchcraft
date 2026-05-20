"""Design-ref agent — moodboard JSON → DESIGN.md + Stitch request envelope.

CLI:
    uv run python -m agents.design_ref.agent --moodboard data/outputs/restaurant-modern.json

Importable:
    from agents.design_ref.agent import build_design_system
    result = build_design_system(moodboard_path="...", out_dir="...", skip_llm=False)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import typer
from dotenv import load_dotenv

from tools.stitch import stitch_runner

from ._color_extract import aggregate_palettes, kmeans_palette
from ._llm import synthesize_design_notes
from ._models import (
    ColorPalette,
    DesignSpec,
    Moodboard,
    MoodboardItem,
    TypographySpec,
)
from ._render import render_design_md

logger = logging.getLogger(__name__)

TOP_N_FOR_COLORS = 8
HTTP_TIMEOUT = 15


def _slug(vertical: str, style: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{vertical}-{style}-{ts}".lower().replace(" ", "-")


def _load_moodboard(path: Path) -> Moodboard:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Moodboard.model_validate(raw)


def _extract_colors(items: List[MoodboardItem]) -> List[str]:
    """Pull dominant colors from the top-N items that have an image."""
    palettes: list[list[str]] = []
    candidates = [it for it in items if it.image_url][:TOP_N_FOR_COLORS]
    for item in candidates:
        try:
            url = item.image_url or ""
            if url.startswith(("http://", "https://")):
                resp = requests.get(url, timeout=HTTP_TIMEOUT)
                resp.raise_for_status()
                palettes.append(kmeans_palette(resp.content, k=5))
            else:
                palettes.append(kmeans_palette(url, k=5))
        except Exception as exc:  # network/decoder errors shouldn't kill the run
            logger.warning("color extraction failed for %s: %s", item.id, exc)
    return aggregate_palettes(palettes)


def _palette_from_hexes(hexes: List[str]) -> ColorPalette:
    """Pick a palette out of an aggregated hex list with sensible fallbacks."""
    base = ColorPalette()
    if not hexes:
        return base
    base.primary = hexes[0]
    if len(hexes) > 1:
        base.accent = hexes[1]
    if len(hexes) > 2:
        base.neutral_500 = hexes[2]
    if len(hexes) > 3:
        base.neutral_900 = hexes[3]
    return base


def _default_mood(vertical: str, style: str) -> str:
    return (
        f"A {style} {vertical} brand that feels confident, current, and human. "
        "Editorial typography, restrained color, intentional motion."
    )


def _default_image_dir(vertical: str) -> str:
    return (
        f"Natural daylight, shallow depth-of-field, candid moments inside the "
        f"{vertical}. Avoid stock-photo gloss; favor texture and warmth."
    )


def _spec_from_inputs(
    moodboard: Moodboard,
    slug: str,
    palette: ColorPalette,
    notes: Optional[Dict[str, Any]],
) -> DesignSpec:
    notes = notes or {}
    typo_block = notes.get("typography_block")
    typography = (
        TypographySpec(display=typo_block, body="", mono=None)
        if typo_block and "\n" not in typo_block
        else TypographySpec()
    )
    patterns = notes.get("component_patterns") or []
    return DesignSpec(
        vertical=moodboard.vertical,
        style=moodboard.style,
        slug=slug,
        brand_mood=notes.get("mood") or _default_mood(moodboard.vertical, moodboard.style),
        palette=palette,
        typography=typography,
        component_patterns=list(patterns) if isinstance(patterns, list) else [],
        motion_references=[it for it in moodboard.items if it.has_animation],
        image_direction=notes.get("image_direction") or _default_image_dir(moodboard.vertical),
        all_references=moodboard.items,
    )


def _write_stitch_request(out_dir: Path, slug: str, design_md_path: Path) -> Path:
    payload = {
        "tool": "create_design_system_from_design_md",
        "args": {
            "name": f"{slug}",
            "design_md_path": str(design_md_path),
        },
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "fulfilled": False,
    }
    path = out_dir / "stitch_request.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_stitch_record(
    out_dir: Path,
    slug: str,
    design_md_path: Path,
    stitch_id: Optional[str],
    error: Optional[str],
) -> Path:
    record = {
        "id": stitch_id,
        "name": slug,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_design_md_path": str(design_md_path),
        "error": error,
    }
    path = out_dir / "stitch_design_system.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return path


def build_design_system(
    moodboard_path: str | Path,
    out_dir: str | Path = "data/outputs",
    skip_llm: bool = False,
    skip_colors: bool = False,
) -> Dict[str, Any]:
    """End-to-end: moodboard → DESIGN.md + stitch envelopes. Returns artifact paths."""
    load_dotenv()
    moodboard_path = Path(moodboard_path)
    moodboard = _load_moodboard(moodboard_path)

    slug = _slug(moodboard.vertical, moodboard.style)
    slug_dir = Path(out_dir) / slug
    slug_dir.mkdir(parents=True, exist_ok=True)

    hexes = [] if skip_colors else _extract_colors(moodboard.items)
    palette = _palette_from_hexes(hexes)

    llm_notes: Optional[Dict[str, Any]] = None
    if not skip_llm:
        libs = sorted({lib for it in moodboard.items for lib in it.libs_detected})
        payload = {
            "vertical": moodboard.vertical,
            "style": moodboard.style,
            "palette": hexes,
            "libs": libs,
            "items": [it.model_dump() for it in moodboard.items],
        }
        llm_notes = synthesize_design_notes(payload)

    spec = _spec_from_inputs(moodboard, slug, palette, llm_notes)
    design_md = render_design_md(spec)
    design_md_path = slug_dir / "DESIGN.md"
    design_md_path.write_text(design_md, encoding="utf-8")

    request_path = _write_stitch_request(slug_dir, slug, design_md_path)

    stitch_id: Optional[str] = None
    stitch_error: Optional[str] = None
    try:
        result = stitch_runner.create_design_system(
            name=slug, design_md_path=str(design_md_path)
        )
        stitch_id = result.get("id") if isinstance(result, dict) else None
    except NotImplementedError as exc:
        stitch_error = str(exc)
        logger.info("stitch call deferred to orchestrator: %s", exc)
    except Exception as exc:  # any other failure — still record
        stitch_error = repr(exc)
        logger.warning("stitch call failed: %s", exc)

    record_path = _write_stitch_record(slug_dir, slug, design_md_path, stitch_id, stitch_error)

    return {
        "slug": slug,
        "out_dir": str(slug_dir),
        "design_md_path": str(design_md_path),
        "stitch_request_path": str(request_path),
        "stitch_record_path": str(record_path),
        "extracted_colors": hexes,
    }


app = typer.Typer(add_completion=False, help="Design-ref agent.")


@app.command()
def main(
    moodboard: Path = typer.Option(..., "--moodboard", "-m", help="Moodboard JSON path."),
    out_dir: Path = typer.Option(Path("data/outputs"), "--out-dir", "-o"),
    skip_llm: bool = typer.Option(False, "--skip-llm", help="Skip Gemini call."),
    skip_colors: bool = typer.Option(False, "--skip-colors", help="Skip Pillow extraction."),
) -> None:
    """Run the design-ref agent and emit a summary to stdout."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = build_design_system(
        moodboard_path=moodboard,
        out_dir=out_dir,
        skip_llm=skip_llm,
        skip_colors=skip_colors,
    )
    typer.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    app()
