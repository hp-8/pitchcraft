"""Tests for HTML transformation."""
from __future__ import annotations

from pathlib import Path

from tools.builder._assets import INJECTION_MARKER
from tools.builder._transform import (
    TransformContext,
    ensure_seo,
    ensure_viewport,
    inject_animation_primitives,
    rewrite_nav_links,
    transform_html,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _ctx(page: str = "landing") -> TransformContext:
    return TransformContext(page=page, business="Joe's Pizza", vertical="restaurant")


def test_inject_animation_primitives_inserts_cdn_tags() -> None:
    html = (FIXTURES / "stitch_landing_v0.html").read_text(encoding="utf-8")
    out = inject_animation_primitives(html)
    assert INJECTION_MARKER in out
    assert "lenis.min.js" in out
    assert "ScrollTrigger.min.js" in out
    assert "/assets/prototype.js" in out
    assert "/assets/prototype.css" in out
    assert "splitting.min.js" in out


def test_injection_is_idempotent() -> None:
    html = (FIXTURES / "stitch_landing_v0.html").read_text(encoding="utf-8")
    once = inject_animation_primitives(html)
    twice = inject_animation_primitives(once)
    assert once == twice
    assert once.count(INJECTION_MARKER) == 1


def test_full_transform_is_idempotent() -> None:
    html = (FIXTURES / "stitch_landing_v0.html").read_text(encoding="utf-8")
    once = transform_html(html, _ctx())
    twice = transform_html(once, _ctx())
    assert once == twice


def test_rewrite_nav_links_remaps_anchor_text() -> None:
    html = '<a href="#menu">Menu</a><a href="#about">About Us</a>'
    out = rewrite_nav_links(html)
    assert 'href="/services"' in out  # menu → services
    assert 'href="/about"' in out


def test_rewrite_nav_skips_external() -> None:
    html = '<a href="https://example.com/about">About</a>'
    out = rewrite_nav_links(html)
    assert 'href="https://example.com/about"' in out


def test_rewrite_nav_skips_mailto_and_tel() -> None:
    html = '<a href="mailto:hi@example.com">Contact</a><a href="tel:555">Contact</a>'
    out = rewrite_nav_links(html)
    assert "mailto:hi@example.com" in out
    assert "tel:555" in out


def test_ensure_viewport_when_missing() -> None:
    html = "<html><head><title>x</title></head><body></body></html>"
    out = ensure_viewport(html)
    assert 'name="viewport"' in out


def test_ensure_viewport_idempotent_when_present() -> None:
    html = (FIXTURES / "stitch_about_v0.html").read_text(encoding="utf-8")
    out = ensure_viewport(html)
    # only one viewport meta
    assert out.lower().count('name="viewport"') == 1


def test_ensure_seo_adds_description_when_missing() -> None:
    html = "<html><head><title>x</title></head><body></body></html>"
    out = ensure_seo(html, _ctx("landing"))
    assert 'name="description"' in out
    assert "Joe's Pizza" in out


def test_ensure_seo_adds_title_when_missing() -> None:
    html = "<html><head></head><body></body></html>"
    out = ensure_seo(html, _ctx("services"))
    assert "<title>Joe's Pizza — Services</title>" in out


def test_transform_preserves_marquee_reveal_magnetic_attrs() -> None:
    html = (FIXTURES / "stitch_landing_v0.html").read_text(encoding="utf-8")
    out = transform_html(html, _ctx())
    assert "data-marquee" in out
    assert "data-reveal" in out
    assert "data-magnetic" in out
    assert "data-split" in out
