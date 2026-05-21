"""Tests for the audit_ux agent."""
from __future__ import annotations

import json
from pathlib import Path

from tools.audit._models import AuditResult
from tools.council.agents.audit_ux import map_audit_to_sections

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "audit_sample.json"


def _audit() -> AuditResult:
    return AuditResult.model_validate(json.loads(FIXTURE.read_text()))


def test_maps_fixture_problems() -> None:
    out = map_audit_to_sections(_audit(), vertical="restaurant")
    must = out["must_have_sections"]
    assert any("CTA" in s for s in must)
    assert any("phone" in s for s in must)
    assert any("reservation" in s for s in must)
    assert any("lazy-load" in s for s in must)


def test_per_page_requirements_routed() -> None:
    out = map_audit_to_sections(_audit(), vertical="restaurant")
    pp = out["per_page_requirements"]
    landing = " ".join(pp["landing"])
    assert "lazy-load" in landing
    assert "reservation widget" in landing
    contact = " ".join(pp["contact"])
    assert "reservation widget" in contact
    # slow_lcp goes only to landing
    assert "lazy-load" not in " ".join(pp["contact"])


def test_priority_problems_only_critical_high() -> None:
    out = map_audit_to_sections(_audit(), vertical="restaurant")
    assert "weak_cta" in out["priority_problems"]
    assert "no_phone" in out["priority_problems"]
    assert "no_reservation" not in out["priority_problems"]  # medium


def test_unknown_codes_skipped() -> None:
    a = _audit()
    a.problems.append(type(a.problems[0])(code="totally_unknown", severity="high", message="x"))
    out = map_audit_to_sections(a, vertical="restaurant")
    assert "totally_unknown" not in " ".join(out["must_have_sections"])


def test_vertical_minimums_dental() -> None:
    a = AuditResult(
        url="https://x", vertical="dental", slug="x", audited_at="2026-01-01T00:00:00Z",
        problems=[], dollar_impact={"monthly_loss_low": 0, "monthly_loss_high": 0, "breakdown": []},
    )
    out = map_audit_to_sections(a, vertical="dental")
    must = " ".join(out["must_have_sections"])
    assert "hours" in must
    assert "testimonial" in must


def test_no_audit_returns_minimal() -> None:
    out = map_audit_to_sections(None, vertical="restaurant")
    assert out["must_have_sections"] == []
    assert "No audit" in out["narrative"]
