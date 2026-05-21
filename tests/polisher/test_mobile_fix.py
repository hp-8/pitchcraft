"""Mobile fix tests."""
from tools.polisher._html import parse
from tools.polisher._mobile_fix import apply_mobile_fixes


def test_viewport_injected_when_missing():
    soup = parse("<html><head></head><body></body></html>")
    fixes = apply_mobile_fixes(soup)
    assert "injected-viewport-meta" in fixes
    assert soup.find("meta", attrs={"name": "viewport"}) is not None


def test_viewport_kept_when_present():
    soup = parse(
        '<html><head><meta name="viewport" content="width=device-width">'
        "</head><body></body></html>"
    )
    fixes = apply_mobile_fixes(soup)
    assert "injected-viewport-meta" not in fixes


def test_bare_1fr_grid_warning():
    soup = parse(
        '<html><body><div style="display:grid; grid-template-columns: 1fr;">x</div>'
        "</body></html>"
    )
    fixes = apply_mobile_fixes(soup)
    assert any("warn-bare-1fr-grid" in f for f in fixes)


def test_no_warning_when_minmax_used():
    soup = parse(
        '<html><body><div style="grid-template-columns: minmax(0, 1fr);">x</div>'
        "</body></html>"
    )
    fixes = apply_mobile_fixes(soup)
    assert not any("warn-bare-1fr-grid" in f for f in fixes)


def test_long_button_text_warning():
    soup = parse(
        "<html><body><button>This is a way too long button label here</button>"
        "</body></html>"
    )
    fixes = apply_mobile_fixes(soup)
    assert any(f.startswith("warn-long-button-text") for f in fixes)
