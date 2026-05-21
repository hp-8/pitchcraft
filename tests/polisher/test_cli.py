"""CLI tests."""
import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from tools.polisher.cli import app

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _setup(tmp_path: Path) -> Path:
    lead_dir = tmp_path / "lead"
    stitch = lead_dir / "stitch"
    stitch.mkdir(parents=True)
    for src, dst in [
        ("stitch_landing_v0.html", "landing-v0.html"),
        ("stitch_services_v1.html", "services-v0.html"),
        ("stitch_about_v0.html", "about-v0.html"),
        ("stitch_contact_v2.html", "contact-v0.html"),
    ]:
        shutil.copy(FIXTURES / src, stitch / dst)
    (lead_dir / "approved.json").write_text(
        json.dumps({"lead_id": "t", "approved": {"landing": 0, "services": 0,
                                                  "about": 0, "contact": 0}}),
        encoding="utf-8",
    )
    return lead_dir


def test_cli_polish(tmp_path: Path):
    lead_dir = _setup(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "polish",
            "--lead-id", "test",
            "--brief", str(FIXTURES / "design_brief_sample.md"),
            "--lead-dir", str(lead_dir),
            "--no-sheet",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["lead_id"] == "test"
    assert len(data["pages"]) == 4


def test_cli_report(tmp_path: Path):
    lead_dir = _setup(tmp_path)
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "polish",
            "--lead-id", "test",
            "--brief", str(FIXTURES / "design_brief_sample.md"),
            "--lead-dir", str(lead_dir),
            "--no-sheet",
        ],
    )
    result = runner.invoke(
        app,
        ["report", "--lead-id", "test", "--lead-dir", str(lead_dir)],
    )
    assert result.exit_code == 0
    assert "test" in result.output


def test_cli_report_missing(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["report", "--lead-id", "nope", "--lead-dir", str(tmp_path / "missing")],
    )
    assert result.exit_code == 1


def test_cli_help_lists_commands():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "polish" in result.output
    assert "report" in result.output
