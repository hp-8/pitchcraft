"""Animation agent — picks motion primitives per page, scoped by genre.

10 primitives required by the Design Quality Bar (PLAN.md):
  smooth_scroll, kinetic_typography, scroll_reveals, page_transition,
  hover_micro, marquee, lazy_reveal, modern_typography, depth, intro_loader.
"""
from __future__ import annotations

from typing import Any

ALL_PRIMITIVES = {
    "smooth_scroll",
    "kinetic_typography",
    "scroll_reveals",
    "page_transition",
    "hover_micro",
    "marquee",
    "lazy_reveal",
    "modern_typography",
    "depth",
    "intro_loader",
}

# Per-page baseline allocation.
_BASE = {
    "landing": [
        "smooth_scroll",
        "kinetic_typography",
        "scroll_reveals",
        "marquee",
        "intro_loader",
        "hover_micro",
        "modern_typography",
        "depth",
    ],
    "services": [
        "scroll_reveals",
        "hover_micro",
        "lazy_reveal",
        "modern_typography",
    ],
    "about": [
        "scroll_reveals",
        "lazy_reveal",
        "page_transition",
        "modern_typography",
    ],
    "contact": [
        "hover_micro",
        "page_transition",
    ],
}

# Lib mapping.
_PRIMITIVE_LIBS = {
    "smooth_scroll": "lenis",
    "kinetic_typography": "splitting",
    "scroll_reveals": "gsap",
    "page_transition": "framer-motion",
    "hover_micro": "framer-motion",
    "marquee": "gsap",
    "lazy_reveal": "gsap",
    "intro_loader": "gsap",
    "depth": "three",
}


def pick_motion_primitives(
    genre: str,
    theme: str | None = None,
    moodboard_libs: dict[str, int] | None = None,
    per_page: bool = True,
) -> dict[str, Any]:
    """Allocate primitives per page, scoped by genre.

    - atmospheric: allow depth (3d) + parallax.
    - modern-minimal: cap each page at 3 primitives (motion-cut discipline).
    - playful: trim depth/three.
    - editorial: default allocation.
    """
    pages = {p: list(prims) for p, prims in _BASE.items()}

    if genre == "atmospheric":
        # Boost depth across landing/about.
        for page in ("landing", "about"):
            if "depth" not in pages[page]:
                pages[page].append("depth")
    elif genre == "modern-minimal":
        # Motion-cut: cap each page at 3 primitives, drop depth/intro_loader/kinetic.
        cut = {"depth", "intro_loader", "kinetic_typography", "marquee"}
        for page in pages:
            pages[page] = [p for p in pages[page] if p not in cut][:3]
    elif genre == "playful":
        # Trim depth (no three), keep hover/marquee/reveal.
        for page in pages:
            pages[page] = [p for p in pages[page] if p != "depth"]
    # editorial: leave defaults.

    # Determine libs.
    libs_needed: set[str] = set()
    for prims in pages.values():
        for p in prims:
            lib = _PRIMITIVE_LIBS.get(p)
            if lib:
                libs_needed.add(lib)

    # Boost from moodboard signals.
    if moodboard_libs:
        if any(k.lower() == "lenis" for k in moodboard_libs):
            libs_needed.add("lenis")
        if any(k.lower() == "gsap" for k in moodboard_libs):
            libs_needed.add("gsap")

    return {
        "per_page": pages,
        "libs_required": sorted(libs_needed),
        "reduced_motion_fallback": True,
        "reduced_motion_note": "prefers-reduced-motion: reduce -> opacity crossfade <=150ms only",
        "genre": genre,
    }
