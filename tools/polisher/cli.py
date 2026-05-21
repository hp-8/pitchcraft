"""Typer CLI for the polisher."""
from __future__ import annotations

import json
from pathlib import Path

import typer

from tools.polisher.polish import polish_prototype

app = typer.Typer(
    add_completion=False,
    help="Polisher — Stitch HTML + design_brief.md → production HTML.",
    no_args_is_help=True,
)


@app.command("polish")
def polish_cmd(
    lead_id: str = typer.Option(..., "--lead-id"),
    brief: Path = typer.Option(..., "--brief", help="Path to design_brief.md"),
    design_md: Path | None = typer.Option(None, "--design-md"),
    lead_dir: Path | None = typer.Option(None, "--lead-dir"),
    approved: Path | None = typer.Option(None, "--approved"),
    out_dir: Path | None = typer.Option(None, "--out-dir"),
    no_sheet: bool = typer.Option(False, "--no-sheet"),
) -> None:
    """Polish approved Stitch HTML into production-ready site."""
    resolved_dir = lead_dir or Path("data/outputs") / lead_id
    sheets = None
    if not no_sheet:
        try:
            from tools.sheets.client import SheetsClient

            sheets = SheetsClient()
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"warning: sheets disabled ({exc})", err=True)
            sheets = None

    result = polish_prototype(
        lead_id=lead_id,
        lead_dir=resolved_dir,
        brief_path=brief,
        design_md_path=design_md,
        approved_path=approved,
        out_dir=out_dir,
        sheets_client=sheets,
    )
    typer.echo(json.dumps(result.model_dump(), indent=2))
    if result.errors and not result.pages:
        raise typer.Exit(code=1)


@app.command("report")
def report_cmd(
    lead_id: str = typer.Option(..., "--lead-id"),
    lead_dir: Path | None = typer.Option(None, "--lead-dir"),
) -> None:
    """Print prior polish_report.json for a lead."""
    resolved = lead_dir or Path("data/outputs") / lead_id
    report = resolved / "polish_report.json"
    if not report.exists():
        typer.echo(f"no polish_report.json at {report}", err=True)
        raise typer.Exit(code=1)
    typer.echo(report.read_text(encoding="utf-8"))
