"""Honesty scan tests."""
from tools.polisher._honest_copy import scan
from tools.polisher._html import parse


def test_flags_plus_percent():
    soup = parse("<html><body><p>Boost revenue +47% today!</p></body></html>")
    flags = scan(soup)
    assert any("invented-percent" in f for f in flags)


def test_flags_trusted_by_banner():
    soup = parse("<html><body><p>Trusted by 5000+ teams worldwide.</p></body></html>")
    flags = scan(soup)
    assert any("trusted-by-banner" in f for f in flags)


def test_flags_nx_claim():
    soup = parse("<html><body><p>10x faster than the competition.</p></body></html>")
    flags = scan(soup)
    assert any("nx-claim" in f for f in flags)


def test_no_flag_for_promo_percent():
    # "47% off" is a promo, not a perf claim — should NOT flag (no +sign, no perf word)
    soup = parse("<html><body><p>47% off summer menu.</p></body></html>")
    flags = scan(soup)
    assert not any("invented-percent" in f for f in flags)
    assert not any("perf-claim" in f for f in flags)


def test_flags_placeholder_names():
    soup = parse("<html><body><blockquote>— Jane Doe, founder</blockquote></body></html>")
    flags = scan(soup)
    assert any("placeholder-name" in f for f in flags)


def test_clean_copy_no_flags():
    soup = parse("<html><body><p>Brooklyn pizzeria since 1975.</p></body></html>")
    flags = scan(soup)
    assert flags == []
