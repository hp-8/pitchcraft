"""Animation wiring tests."""
from tools.polisher._animation_wire import build_prototype_js, inject_cdn
from tools.polisher._html import parse
from tools.polisher._models import BriefSummary


def test_inject_cdn_adds_scripts_and_idempotent():
    soup = parse("<html><head></head><body></body></html>")
    libs = inject_cdn(soup)
    assert "lenis" in libs and "gsap" in libs and "splitting" in libs
    html = str(soup)
    assert "lenis.min.js" in html
    assert "gsap.min.js" in html
    assert "ScrollTrigger.min.js" in html
    assert "splitting.min.js" in html
    assert "/assets/prototype.js" in html
    # idempotent
    inject_cdn(soup)
    assert str(soup).count("lenis.min.js") == 1


def test_prototype_js_has_reduced_motion_guard():
    js = build_prototype_js(BriefSummary())
    assert "prefers-reduced-motion" in js
    assert "Lenis" in js
    assert "ScrollTrigger" in js
    assert "data-magnetic" in js
    assert "data-reveal" in js
    assert "data-marquee" in js


def test_prototype_js_page_transitions_flag():
    js_on = build_prototype_js(BriefSummary(page_transitions=True))
    js_off = build_prototype_js(BriefSummary(page_transitions=False))
    assert "pageTransitions = true" in js_on
    assert "pageTransitions = false" in js_off
