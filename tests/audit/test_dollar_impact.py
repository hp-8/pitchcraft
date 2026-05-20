"""Tests for tools.audit._dollar_impact."""
from __future__ import annotations

from tools.audit._dollar_impact import estimate_dollar_impact
from tools.audit._models import Problem


def _p(code, sev="critical"):
    return Problem(code=code, severity=sev, message="x")


def test_no_problems_means_zero():
    di = estimate_dollar_impact([], None, "restaurant")
    assert di.monthly_loss_low == 0
    assert di.monthly_loss_high == 0
    assert di.breakdown == []


def test_low_lt_high_when_problems_present():
    probs = [_p("weak_cta", "critical"), _p("no_phone", "high")]
    di = estimate_dollar_impact(probs, None, "dental")
    assert di.monthly_loss_low > 0
    assert di.monthly_loss_high > 0
    assert di.monthly_loss_low < di.monthly_loss_high
    assert {it.code for it in di.breakdown} == {"weak_cta", "no_phone"}


def test_skip_codes_excluded():
    probs = [_p("no_schema_org", "medium"), _p("dated_design_signals", "medium")]
    di = estimate_dollar_impact(probs, None, "restaurant")
    assert di.monthly_loss_low == 0
    assert di.breakdown == []


def test_slow_load_added_when_lcp_high():
    ps = {"lcp_ms": 5500}
    di = estimate_dollar_impact([_p("weak_cta")], ps, "realtor")
    codes = [it.code for it in di.breakdown]
    assert "slow_load" in codes


def test_slow_load_skipped_when_fast():
    ps = {"lcp_ms": 1800}
    di = estimate_dollar_impact([_p("weak_cta")], ps, "realtor")
    codes = [it.code for it in di.breakdown]
    assert "slow_load" not in codes


def test_pagespeed_error_skips_slow_load():
    ps = {"error": "boom", "lcp_ms": 9000}
    di = estimate_dollar_impact([_p("weak_cta")], ps, "fnb")
    codes = [it.code for it in di.breakdown]
    assert "slow_load" not in codes


def test_all_verticals_have_positive_baselines():
    for v in ("restaurant", "dental", "realtor", "fnb"):
        di = estimate_dollar_impact([_p("weak_cta", "critical")], None, v)
        assert di.monthly_loss_low > 0
        assert di.monthly_loss_high > di.monthly_loss_low
