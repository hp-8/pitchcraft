"""Tests for the council CLI."""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from tools.council.cli import app

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def test_run_smoke(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--lead-id", "test-pizza",
            "--business", "Joe's Pizza",
            "--vertical", "restaurant",
            "--location", "Brooklyn, NY",
            "--service", "pizza",
            "--service", "delivery",
            "--audit-json", str(FIX / "audit_sample.json"),
            "--moodboard", str(FIX / "moodboard_sample.json"),
            "--skip-llm",
            "--no-sheet",
            "--out-dir", str(tmp_path),
            "--log-path", str(tmp_path / "log.json"),
        ],
    )
    assert result.exit_code == 0, result.stdout
    brief = Path(result.stdout.strip().splitlines()[-1])
    assert brief.exists()
    assert brief.name == "design_brief.md"


def test_list_runs(tmp_path: Path) -> None:
    runner = CliRunner()
    # seed two briefs by running twice
    for lid in ("a", "b"):
        runner.invoke(
            app,
            [
                "run", "--lead-id", lid, "--business", lid.upper(),
                "--vertical", "restaurant", "--skip-llm", "--no-sheet",
                "--out-dir", str(tmp_path),
                "--log-path", str(tmp_path / "log.json"),
            ],
        )
    result = runner.invoke(app, ["list-runs", "--out-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "macro=" in result.stdout
    assert "theme=" in result.stdout


def test_rejects_bad_vertical(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run", "--lead-id", "x", "--business", "X",
            "--vertical", "bogus", "--skip-llm", "--no-sheet",
            "--out-dir", str(tmp_path),
        ],
    )
    assert result.exit_code != 0
