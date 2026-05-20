"""Tests for tools.stitch.screens prompt builder + envelope writer."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from tools.stitch._models import LeadContext, ScreenRequest
from tools.stitch.cli import app as cli_app
from tools.stitch.screens import (
    PAGES,
    VARIANT_DIRECTIONS,
    build_screen_prompts,
    write_screens_request,
)

FIXTURE_AUDIT = Path(__file__).resolve().parents[1] / "fixtures" / "audit_sample.json"


@pytest.fixture
def lead() -> LeadContext:
    return LeadContext(
        lead_id="lead_test_1",
        business="Joe's Pizza",
        vertical="restaurant",
        tagline="Brooklyn since 1975",
        services=["pizza", "delivery", "private events"],
        location="Brooklyn, NY",
        phone="(212) 555-1212",
        booking_provider="OpenTable",
    )


def test_build_screen_prompts_produces_12(lead: LeadContext) -> None:
    prompts = build_screen_prompts(lead, "ds_abc")
    assert len(prompts) == 12
    pairs = {(p.page, p.variant_idx) for p in prompts}
    assert len(pairs) == 12
    expected = {(page, i) for page in PAGES for i in range(3)}
    assert pairs == expected
    # each prompt is a valid ScreenRequest with expected target path
    for p in prompts:
        assert isinstance(p, ScreenRequest)
        assert p.design_system_id == "ds_abc"
        assert p.variant_direction == VARIANT_DIRECTIONS[p.page][p.variant_idx]
        assert f"{p.page}-v{p.variant_idx}.json" in p.target_path
        assert lead.lead_id in p.target_path


def test_prompts_mention_business_and_vertical(lead: LeadContext) -> None:
    for p in build_screen_prompts(lead, "ds_abc"):
        assert "Joe's Pizza" in p.prompt
        assert "restaurant" in p.prompt
        assert "ds_abc" in p.prompt
        assert p.variant_direction in p.prompt


def test_audit_problem_mapping(lead: LeadContext) -> None:
    problems = ["no_reservation", "slow_lcp", "no_menu"]
    prompts = build_screen_prompts(lead, "ds_abc", audit_problems=problems)
    by_page = {(p.page, p.variant_idx): p for p in prompts}

    landing0 = by_page[("landing", 0)].prompt
    # slow_lcp -> landing only
    assert "lazy-load below-fold imagery" in landing0
    # no_reservation -> landing/services
    assert "reservation widget" in landing0
    # no_menu -> landing/services
    assert "Menu CTA" in landing0

    contact0 = by_page[("contact", 0)].prompt
    assert "lazy-load below-fold imagery" not in contact0
    assert "reservation widget" not in contact0
    assert "Menu CTA" not in contact0
    # no audit notes mapped to contact -> placeholder line shows
    assert "no audit-flagged pain points map to this page" in contact0

    services0 = by_page[("services", 0)].prompt
    assert "reservation widget" in services0
    assert "lazy-load below-fold imagery" not in services0


def test_unknown_problem_codes_are_ignored(lead: LeadContext) -> None:
    prompts = build_screen_prompts(lead, "ds_abc", audit_problems=["totally_unknown"])
    for p in prompts:
        assert "totally_unknown" not in p.prompt


def test_envelope_schema(lead: LeadContext, tmp_path: Path) -> None:
    envelope = write_screens_request(lead, "ds_abc", out_root=tmp_path)
    assert envelope.exists()
    data = json.loads(envelope.read_text(encoding="utf-8"))
    assert data["lead_id"] == lead.lead_id
    assert data["business"] == lead.business
    assert data["vertical"] == "restaurant"
    assert data["design_system_id"] == "ds_abc"
    assert "created_at" in data
    assert len(data["screens"]) == 12
    for s in data["screens"]:
        assert s["tool"] == "mcp__stitch__generate_screen_from_text"
        assert s["fulfilled"] is False
        assert set(s["args"]) == {"prompt", "design_system_id", "name"}
        assert s["args"]["name"].startswith(f"{lead.lead_id}-")
        # Round-trip prompt block through ScreenRequest model
        ScreenRequest(
            page=s["page"],
            variant_idx=s["variant_idx"],
            variant_direction=s["variant_direction"],
            prompt=s["args"]["prompt"],
            design_system_id=s["args"]["design_system_id"],
            target_path=s["target_path"],
        )


def test_sheets_integration_optional(lead: LeadContext, tmp_path: Path) -> None:
    # default: no sheets_client -> no calls
    write_screens_request(lead, "ds_abc", out_root=tmp_path)  # must not raise

    mock_client = MagicMock()
    envelope = write_screens_request(
        lead, "ds_abc", out_root=tmp_path, sheets_client=mock_client
    )
    mock_client.upsert_lead.assert_called_once()
    args, _ = mock_client.upsert_lead.call_args
    assert args[0] == lead.lead_id
    assert args[1]["stitch_status"] == "queued"
    assert args[1]["stitch_variants_url"] == str(envelope)
    mock_client.update_status.assert_called_once_with(
        lead.lead_id, "stitch", "queued", note="queued 12 variants"
    )


def test_cli_smoke(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_app,
        [
            "build-screens",
            "--lead-id",
            "lead_cli_1",
            "--business",
            "Joe's Pizza",
            "--vertical",
            "restaurant",
            "--design-system-id",
            "ds_xyz",
            "--service",
            "pizza",
            "--service",
            "delivery",
            "--location",
            "Brooklyn, NY",
            "--audit-json",
            str(FIXTURE_AUDIT),
            "--out-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    envelope_path = Path(result.stdout.strip().splitlines()[-1])
    assert envelope_path.exists()
    data = json.loads(envelope_path.read_text(encoding="utf-8"))
    assert len(data["screens"]) == 12
    # audit fixture includes no_reservation -> appears in landing prompt
    landing = next(s for s in data["screens"] if s["page"] == "landing" and s["variant_idx"] == 0)
    assert "reservation widget" in landing["args"]["prompt"]


def test_cli_list_envelopes(tmp_path: Path) -> None:
    # seed two envelopes
    lead_a = LeadContext(lead_id="lead_a", business="A", vertical="dental")
    lead_b = LeadContext(lead_id="lead_b", business="B", vertical="realtor")
    write_screens_request(lead_a, "ds_a", out_root=tmp_path)
    write_screens_request(lead_b, "ds_b", out_root=tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli_app, ["list-envelopes", "--out-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "lead_a" in result.stdout
    assert "lead_b" in result.stdout
    assert "fulfilled=0/12" in result.stdout


def test_cli_rejects_bad_vertical(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_app,
        [
            "build-screens",
            "--lead-id",
            "lead_x",
            "--business",
            "X",
            "--vertical",
            "bogus",
            "--design-system-id",
            "ds_x",
            "--out-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0
