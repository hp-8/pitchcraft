"""End-to-end polish_prototype test."""
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.polisher.polish import polish_prototype

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _setup_lead(tmp_path: Path) -> Path:
    lead_dir = tmp_path / "lead"
    stitch = lead_dir / "stitch"
    stitch.mkdir(parents=True)
    # Map fixture filenames -> page filenames; all use v0 for simplicity
    mapping = {
        "stitch_landing_v0.html": "landing-v0.html",
        "stitch_services_v1.html": "services-v0.html",
        "stitch_about_v0.html": "about-v0.html",
        "stitch_contact_v2.html": "contact-v0.html",
    }
    for src_name, dst_name in mapping.items():
        shutil.copy(FIXTURES / src_name, stitch / dst_name)
    (lead_dir / "approved.json").write_text(
        json.dumps({"lead_id": "t", "approved": {"landing": 0, "services": 0, "about": 0,
                                                  "contact": 0}}),
        encoding="utf-8",
    )
    return lead_dir


def test_polish_end_to_end(tmp_path: Path):
    lead_dir = _setup_lead(tmp_path)
    result = polish_prototype(
        lead_id="test-lead",
        lead_dir=lead_dir,
        brief_path=FIXTURES / "design_brief_sample.md",
    )
    assert result.lead_id == "test-lead"
    assert len(result.pages) == 4
    assert result.theme_name == "Specimen"
    assert "lenis" in result.libs_loaded
    site = Path(result.site_dir)
    assert (site / "index.html").exists()
    assert (site / "services.html").exists()
    assert (site / "about.html").exists()
    assert (site / "contact.html").exists()
    assert (site / "assets" / "prototype.js").exists()
    assert (site / "assets" / "prototype.css").exists()
    assert (site / "vercel.json").exists()
    # polish_report.json written
    report = lead_dir / "polish_report.json"
    assert report.exists()
    parsed = json.loads(report.read_text())
    assert parsed["lead_id"] == "test-lead"

    # Output HTML contains expected artefacts
    index_html = (site / "index.html").read_text()
    assert "data-reveal" in index_html
    assert "lenis.min.js" in index_html
    assert "gsap" in index_html
    assert "viewport" in index_html
    assert ":focus-visible" in index_html


def test_polish_missing_source_records_error(tmp_path: Path):
    lead_dir = tmp_path / "lead"
    (lead_dir / "stitch").mkdir(parents=True)
    (lead_dir / "approved.json").write_text(
        json.dumps({"lead_id": "x", "approved": {}}), encoding="utf-8"
    )
    result = polish_prototype(
        lead_id="x",
        lead_dir=lead_dir,
        brief_path=FIXTURES / "design_brief_sample.md",
    )
    assert len(result.pages) == 0
    assert any("missing source HTML" in e for e in result.errors)


def test_polish_sheets_client_called(tmp_path: Path):
    lead_dir = _setup_lead(tmp_path)
    sheets = MagicMock()
    polish_prototype(
        lead_id="test",
        lead_dir=lead_dir,
        brief_path=FIXTURES / "design_brief_sample.md",
        sheets_client=sheets,
    )
    sheets.upsert_lead.assert_called_once()
    sheets.update_status.assert_called_once()


@pytest.mark.parametrize("page", ["index.html", "services.html"])
def test_polish_pages_have_premium_css(tmp_path: Path, page: str):
    lead_dir = _setup_lead(tmp_path)
    result = polish_prototype(
        lead_id="t",
        lead_dir=lead_dir,
        brief_path=FIXTURES / "design_brief_sample.md",
    )
    html = (Path(result.site_dir) / page).read_text()
    assert "--color-bg" in html
    assert "oklch" in html
