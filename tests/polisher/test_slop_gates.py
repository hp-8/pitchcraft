"""Slop gates tests."""
from tools.polisher._html import parse
from tools.polisher._slop_gates import check_gates


def test_fake_browser_chrome_detected():
    soup = parse(
        "<html><head></head><body>"
        '<div class="window-chrome">'
        '<span class="dot red"></span><span class="dot yellow"></span>'
        '<span class="dot green"></span>'
        '<span class="url-pill">https://example.com</span>'
        "</div></body></html>"
    )
    failures = check_gates(soup)
    assert "gate:fake-browser-chrome" in failures


def test_fake_phone_frame_detected():
    soup = parse(
        "<html><head></head><body>"
        '<div class="iphone-frame"><div class="notch"></div></div>'
        "<button>x</button>"
        "</body></html>"
    )
    failures = check_gates(soup)
    assert "gate:fake-phone-frame" in failures


def test_missing_focus_visible_when_buttons_present():
    soup = parse(
        "<html><head><style>body { color: red; }</style></head>"
        "<body><button>click</button></body></html>"
    )
    failures = check_gates(soup)
    assert "gate:missing-focus-visible" in failures


def test_focus_visible_present_passes():
    soup = parse(
        "<html><head><style>:focus-visible { outline: 2px solid red; }</style></head>"
        "<body><button>click</button></body></html>"
    )
    failures = check_gates(soup)
    assert "gate:missing-focus-visible" not in failures


def test_no_interactive_skips_focus_check():
    soup = parse("<html><head></head><body><p>plain</p></body></html>")
    failures = check_gates(soup)
    assert "gate:missing-focus-visible" not in failures
