"""End-to-end tests for build_prototype orchestrator."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.builder._models import DeployResult
from tools.builder.prototype import build_prototype

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _setup_lead_dir(tmp_path: Path) -> Path:
    lead_dir = tmp_path / "test-pizza"
    stitch = lead_dir / "stitch"
    stitch.mkdir(parents=True)
    shutil.copy(FIXTURES / "stitch_landing_v0.html", stitch / "landing-v0.html")
    shutil.copy(FIXTURES / "stitch_services_v1.html", stitch / "services-v1.html")
    shutil.copy(FIXTURES / "stitch_about_v0.html", stitch / "about-v0.html")
    shutil.copy(FIXTURES / "stitch_contact_v2.html", stitch / "contact-v2.html")
    shutil.copy(FIXTURES / "approved_sample.json", lead_dir / "approved.json")
    return lead_dir


def test_build_skip_deploy_produces_full_site(tmp_path: Path) -> None:
    lead_dir = _setup_lead_dir(tmp_path)
    result = build_prototype(
        lead_id="test-pizza",
        lead_dir=lead_dir,
        business="Joe's Pizza",
        vertical="restaurant",
        sheets_client=None,
        skip_deploy=True,
    )
    assert result.skipped_deploy is True
    assert result.deploy_url is None
    assert set(result.pages) == {"landing", "services", "about", "contact"}
    site = lead_dir / "site"
    assert (site / "index.html").exists()
    assert (site / "services.html").exists()
    assert (site / "about.html").exists()
    assert (site / "contact.html").exists()
    assert (site / "assets" / "prototype.js").exists()
    assert (site / "assets" / "prototype.css").exists()
    assert (site / "vercel.json").exists()

    index = (site / "index.html").read_text(encoding="utf-8")
    assert "lenis.min.js" in index
    assert "/assets/prototype.js" in index


def test_build_logs_errors_for_missing_html(tmp_path: Path) -> None:
    lead_dir = tmp_path / "test-pizza"
    (lead_dir / "stitch").mkdir(parents=True)
    (lead_dir / "approved.json").write_text(
        json.dumps(
            {
                "lead_id": "test-pizza",
                "approved": {"landing": 0, "services": 0, "about": 0, "contact": 0},
            }
        )
    )
    result = build_prototype(
        lead_id="test-pizza",
        lead_dir=lead_dir,
        business="Joe's Pizza",
        vertical="restaurant",
        skip_deploy=True,
    )
    assert result.pages == []
    assert len(result.errors) == 4


def test_build_missing_approved_returns_error(tmp_path: Path) -> None:
    lead_dir = tmp_path / "test-pizza"
    lead_dir.mkdir()
    result = build_prototype(
        lead_id="test-pizza",
        lead_dir=lead_dir,
        business="Joe's Pizza",
        vertical="restaurant",
        skip_deploy=True,
    )
    assert result.pages == []
    assert any("approved.json" in e for e in result.errors)


def test_build_with_mocked_deploy_success(tmp_path: Path) -> None:
    lead_dir = _setup_lead_dir(tmp_path)
    sheets = MagicMock()
    fake = DeployResult(
        url="https://joes-pizza.vercel.app",
        raw_stdout="ok",
        success=True,
    )
    with patch("tools.builder.prototype.vercel_deploy", return_value=fake):
        result = build_prototype(
            lead_id="test-pizza",
            lead_dir=lead_dir,
            business="Joe's Pizza",
            vertical="restaurant",
            sheets_client=sheets,
            skip_deploy=False,
        )
    assert result.deploy_url == "https://joes-pizza.vercel.app"
    assert result.deployed_at is not None
    assert result.skipped_deploy is False
    # sheet was updated
    assert sheets.upsert_lead.called
    assert sheets.update_status.called
    args, kwargs = sheets.update_status.call_args
    assert args[1] == "prototype"
    assert args[2] == "deployed"


def test_build_with_mocked_deploy_failure(tmp_path: Path) -> None:
    lead_dir = _setup_lead_dir(tmp_path)
    fake = DeployResult(url="", raw_stdout="", success=False, error="boom")
    with patch("tools.builder.prototype.vercel_deploy", return_value=fake):
        result = build_prototype(
            lead_id="test-pizza",
            lead_dir=lead_dir,
            business="Joe's Pizza",
            vertical="restaurant",
            skip_deploy=False,
        )
    assert result.deploy_url is None
    assert any("deploy failed" in e for e in result.errors)


def test_build_skip_deploy_updates_sheet_built(tmp_path: Path) -> None:
    lead_dir = _setup_lead_dir(tmp_path)
    sheets = MagicMock()
    build_prototype(
        lead_id="test-pizza",
        lead_dir=lead_dir,
        business="Joe's Pizza",
        vertical="restaurant",
        sheets_client=sheets,
        skip_deploy=True,
    )
    sheets.upsert_lead.assert_called_once()
    args, kwargs = sheets.upsert_lead.call_args
    assert args[1]["prototype_status"] == "built"


@pytest.mark.parametrize("page,filename", [
    ("landing", "index.html"),
    ("services", "services.html"),
    ("about", "about.html"),
    ("contact", "contact.html"),
])
def test_each_page_has_animation_primitives(tmp_path: Path, page: str, filename: str) -> None:
    lead_dir = _setup_lead_dir(tmp_path)
    build_prototype(
        lead_id="test-pizza",
        lead_dir=lead_dir,
        business="Joe's Pizza",
        vertical="restaurant",
        skip_deploy=True,
    )
    html = (lead_dir / "site" / filename).read_text(encoding="utf-8")
    assert "/assets/prototype.js" in html
    assert "/assets/prototype.css" in html
