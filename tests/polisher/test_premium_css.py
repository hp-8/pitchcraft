"""Premium CSS tests."""
from tools.polisher._html import parse
from tools.polisher._models import BriefSummary
from tools.polisher._premium_css import build_css, inject_premium_css


def test_build_css_includes_tokens_and_focus_visible():
    css = build_css(BriefSummary(paper_band="light", accent_hue="warm"))
    assert "--color-bg" in css
    assert "oklch" in css
    assert ":focus-visible" in css
    assert "overflow-wrap: anywhere" in css
    assert "overflow-x: clip" in css
    assert "prefers-reduced-motion" in css


def test_build_css_dark_theme():
    css = build_css(BriefSummary(paper_band="dark", accent_hue="cool"))
    # dark cool palette has lightness 0.16
    assert "0.16" in css


def test_inject_premium_css_adds_block_and_fonts():
    soup = parse("<html><head><title>x</title></head><body></body></html>")
    inject_premium_css(soup, BriefSummary(paper_band="light", accent_hue="warm"))
    style = soup.find("style", attrs={"data-polisher-css": "1"})
    assert style is not None
    assert "--color-bg" in style.string
    assert soup.find("link", attrs={"data-polisher-fonts": "1"}) is not None


def test_inject_premium_css_idempotent():
    soup = parse("<html><head></head><body></body></html>")
    inject_premium_css(soup, BriefSummary())
    inject_premium_css(soup, BriefSummary())
    assert len(soup.find_all("style", attrs={"data-polisher-css": "1"})) == 1


def test_gradient_mesh_adds_body_class():
    soup = parse("<html><head></head><body></body></html>")
    inject_premium_css(soup, BriefSummary(gradient_mesh=True))
    body = soup.find("body")
    cls = body.get("class") or []
    assert "has-mesh" in cls
