"""Tests for tools.audit._heuristics."""
from __future__ import annotations

from tools.audit._heuristics import run_heuristics, run_pagespeed_heuristics

GOOD_HTML = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width">
  <script type="application/ld+json">{"@type":"Restaurant"}</script>
</head>
<body>
  <h1>Joe's Pizza</h1>
  <a href="/book">Book a table</a>
  <p>Call (212) 555-1212</p>
  <p>123 Main Street, NY</p>
  <p>4.8 stars from 200 reviews</p>
  <p>Menu and reservation available.</p>
</body>
</html>
"""

GOOD_MD = """
# Joe's Pizza

Call (212) 555-1212.
Visit us at 123 Main Street.
Read our reviews — 4.8 stars.

Menu and reservation available.
"""


def _codes(problems):
    return {p.code for p in problems}


def test_clean_site_has_minimal_problems():
    probs = run_heuristics(GOOD_MD, GOOD_HTML, "restaurant", url="https://x.com")
    codes = _codes(probs)
    for must_pass in ("no_h1", "weak_cta", "no_phone", "no_address",
                      "no_mobile_meta", "no_schema_org", "no_https",
                      "no_social_proof", "no_menu", "no_reservation"):
        assert must_pass not in codes, f"unexpected: {must_pass}"


def test_bad_site_flags_everything():
    bad_html = "<html><body><table><tr><td>old</td></tr></table></body></html>"
    bad_md = "Welcome"
    probs = run_heuristics(bad_md, bad_html, "restaurant", url="http://x.com")
    codes = _codes(probs)
    for must in ("no_h1", "weak_cta", "no_phone", "no_address",
                 "no_mobile_meta", "no_schema_org", "no_https",
                 "dated_design_signals", "no_social_proof",
                 "no_menu", "no_reservation"):
        assert must in codes, f"missing: {must}"


def test_dental_vertical_checks():
    probs = run_heuristics("Smile clinic. Insurance accepted.",
                           "<h1>Dental</h1>", "dental", url="https://x.com")
    codes = _codes(probs)
    assert "no_booking" in codes
    assert "no_insurance_info" not in codes


def test_realtor_vertical_checks():
    probs = run_heuristics("MLS home search idx widget here. listings galore",
                           "<h1>Realty</h1>", "realtor", url="https://x.com")
    codes = _codes(probs)
    assert "no_listings" not in codes
    assert "no_idx_widget" not in codes


def test_fnb_vertical_checks():
    probs = run_heuristics("Order online via DoorDash. menu inside",
                           "<h1>Cafe</h1>", "fnb", url="https://x.com")
    codes = _codes(probs)
    assert "no_menu" not in codes
    assert "no_order_online" not in codes


def test_https_check_positive():
    probs = run_heuristics("", "<h1>x</h1>", "restaurant", url="http://insecure.com")
    assert "no_https" in _codes(probs)


def test_cta_fallback_for_vertical():
    md = "Our menu has great pizza."
    html = "<h1>x</h1>"
    probs = run_heuristics(md, html, "restaurant", url="https://x.com")
    assert "weak_cta" not in _codes(probs)


def test_pagespeed_heuristics_flags_slow_lcp_and_perf():
    ps = {"lcp_ms": 3401, "tbt_ms": 780, "inp_ms": 236, "cls": 0.035, "performance_score": 0.63}
    codes = _codes(run_pagespeed_heuristics(ps))
    assert "slow_lcp" in codes
    assert "slow_tbt" in codes
    assert "slow_inp" in codes
    assert "low_perf_score" in codes
    assert "layout_shift" not in codes  # 0.035 < 0.1


def test_pagespeed_heuristics_clean_when_good():
    ps = {"lcp_ms": 1800, "tbt_ms": 100, "inp_ms": 120, "cls": 0.05, "performance_score": 0.95}
    assert run_pagespeed_heuristics(ps) == []


def test_pagespeed_heuristics_handles_none_and_error():
    assert run_pagespeed_heuristics(None) == []
    assert run_pagespeed_heuristics({"error": "boom"}) == []
