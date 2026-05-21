"""Inspiration agent — rank moodboard items, motion-first.

Pure Python, no LLM. Reads a moodboard JSON (Phase 1 schema) and emits a
top-N ranked list plus source / lib distribution.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Higher = ranked earlier.
_SOURCE_QUALITY: dict[str, int] = {
    "codrops": 100,
    "awwwards": 95,
    "gsap_showcase": 90,
    "react_bits": 85,
    "r3f_examples": 85,
    "twentyfirst": 80,
    "cosmos": 70,
    "arena": 60,
    "pinterest": 40,
}


def _load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("moodboard JSON must be an object")
    return raw


def _sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    libs = item.get("libs_detected") or []
    has_anim = bool(item.get("has_animation"))
    motion_score = 2 if (has_anim and libs) else (1 if (has_anim or libs) else 0)
    src_quality = _SOURCE_QUALITY.get(str(item.get("source", "")), 0)
    score_field = item.get("score")
    score_int = int(round(float(score_field) * 100)) if isinstance(score_field, (int, float)) else 0
    # negative so higher motion/quality ranks earlier under natural sort
    return (-motion_score, -src_quality, -score_int, str(item.get("id", "")))


def rank_moodboard(
    moodboard_path: str | Path | None,
    vertical: str,
    style: str | None = None,
    top_n: int = 12,
) -> dict[str, Any]:
    """Rank moodboard items motion-first; return top-N + stats.

    Returns dict with keys: top_refs, by_source, motion_lib_distribution, warnings.
    """
    warnings: list[str] = []
    if moodboard_path is None:
        return {
            "top_refs": [],
            "by_source": {},
            "motion_lib_distribution": {},
            "warnings": ["moodboard_path not supplied — inspiration empty"],
        }
    path = Path(moodboard_path)
    if not path.exists():
        return {
            "top_refs": [],
            "by_source": {},
            "motion_lib_distribution": {},
            "warnings": [f"moodboard path not found: {path}"],
        }

    try:
        data = _load(path)
    except Exception as exc:
        return {
            "top_refs": [],
            "by_source": {},
            "motion_lib_distribution": {},
            "warnings": [f"failed to read moodboard: {exc}"],
        }

    items = list(data.get("items") or [])
    # dedupe by image_url then url
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for it in items:
        key = str(it.get("image_url") or it.get("url") or it.get("id") or "")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    deduped.sort(key=_sort_key)
    top = deduped[:top_n]

    by_source: dict[str, int] = {}
    libs: dict[str, int] = {}
    for it in deduped:
        src = str(it.get("source", "unknown"))
        by_source[src] = by_source.get(src, 0) + 1
        for lib in it.get("libs_detected") or []:
            libs[str(lib)] = libs.get(str(lib), 0) + 1

    if not top:
        warnings.append("moodboard contained no items")

    return {
        "top_refs": top,
        "by_source": by_source,
        "motion_lib_distribution": libs,
        "vertical": vertical,
        "style": style,
        "warnings": warnings,
    }
