"""CLI smoke test for tools.builder."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from tools.builder.cli import app

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _setup(tmp_path: Path) -> Path:
    lead_dir = tmp_path / "test-pizza"
    stitch = lead_dir / "stitch"
    stitch.mkdir(parents=True)
    shutil.copy(FIXTURES / "stitch_landing_v0.html", stitch / "landing-v0.html")
    shutil.copy(FIXTURES / "stitch_services_v1.html", stitch / "services-v1.html")
    shutil.copy(FIXTURES / "stitch_about_v0.html", stitch / "about-v0.html")
    shutil.copy(FIXTURES / "stitch_contact_v2.html", stitch / "contact-v2.html")
    shutil.copy(FIXTURES / "approved_sample.json", lead_dir / "approved.json")
    return lead_dir


def test_cli_build_skip_deploy(tmp_path: Path) -> None:
    lead_dir = _setup(tmp_path)
    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            "build",
            "--lead-id", "test-pizza",
            "--business", "Joe's Pizza",
            "--vertical", "restaurant",
            "--lead-dir", str(lead_dir),
            "--skip-deploy",
            "--no-sheet",
        ],
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["skipped_deploy"] is True
    assert set(payload["pages"]) == {"landing", "services", "about", "contact"}
    assert (lead_dir / "site" / "index.html").exists()


def test_cli_help_lists_build() -> None:
    runner = CliRunner()
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "build" in res.output
