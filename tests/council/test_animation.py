"""Tests for the animation agent."""
from __future__ import annotations

from tools.council.agents.animation import pick_motion_primitives


def test_per_page_allocation_editorial() -> None:
    out = pick_motion_primitives("editorial")
    pp = out["per_page"]
    assert "smooth_scroll" in pp["landing"]
    assert "kinetic_typography" in pp["landing"]
    assert "marquee" in pp["landing"]
    assert "intro_loader" in pp["landing"]
    assert "page_transition" in pp["about"]
    assert "page_transition" in pp["contact"]
    assert out["reduced_motion_fallback"] is True


def test_atmospheric_adds_depth() -> None:
    out = pick_motion_primitives("atmospheric")
    assert "depth" in out["per_page"]["landing"]
    assert "depth" in out["per_page"]["about"]
    assert "three" in out["libs_required"]


def test_modern_minimal_motion_cut() -> None:
    out = pick_motion_primitives("modern-minimal")
    for page, prims in out["per_page"].items():
        assert len(prims) <= 3, f"{page} has too many primitives: {prims}"
    landing = out["per_page"]["landing"]
    assert "depth" not in landing
    assert "intro_loader" not in landing
    assert "kinetic_typography" not in landing
    assert "marquee" not in landing


def test_playful_no_depth() -> None:
    out = pick_motion_primitives("playful")
    for prims in out["per_page"].values():
        assert "depth" not in prims
    assert "three" not in out["libs_required"]


def test_moodboard_libs_boost() -> None:
    out = pick_motion_primitives(
        "editorial", moodboard_libs={"Lenis": 3, "gsap": 5}
    )
    assert "lenis" in out["libs_required"]
    assert "gsap" in out["libs_required"]


def test_reduced_motion_always_on() -> None:
    for genre in ("editorial", "atmospheric", "modern-minimal", "playful"):
        out = pick_motion_primitives(genre)
        assert out["reduced_motion_fallback"] is True
        assert "prefers-reduced-motion" in out["reduced_motion_note"]
