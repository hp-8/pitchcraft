"""Typer CLI for prototype builder."""
from __future__ import annotations

import json
from pathlib import Path

import typer

from tools.builder.prototype import build_prototype

app = typer.Typer(
    add_completion=False,
    help="Prototype builder (Stitch HTML → site → Vercel).",
    no_args_is_help=True,
)


@app.command("build")
def build_cmd(
    lead_id: str = typer.Option(..., "--lead-id"),
    business: str = typer.Option(..., "--business"),
    vertical: str = typer.Option(..., "--vertical"),
    lead_dir: Path | None = typer.Option(
        None, "--lead-dir", help="Default: data/outputs/<lead-id>"
    ),
    skip_deploy: bool = typer.Option(False, "--skip-deploy", help="Build site, no deploy"),
    no_sheet: bool = typer.Option(False, "--no-sheet", help="Skip SheetsClient updates"),
) -> None:
    """Build (and optionally deploy) the static prototype for one lead."""
    resolved_dir = lead_dir or Path("data/outputs") / lead_id
    sheets = None
    if not no_sheet:
        try:
            from tools.sheets.client import SheetsClient

            sheets = SheetsClient()
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"warning: sheets disabled ({exc})", err=True)
            sheets = None

    result = build_prototype(
        lead_id=lead_id,
        lead_dir=resolved_dir,
        business=business,
        vertical=vertical,
        sheets_client=sheets,
        skip_deploy=skip_deploy,
    )
    typer.echo(json.dumps(result.model_dump(), indent=2))
    if result.errors and not result.pages:
        raise typer.Exit(code=1)


@app.command("info")
def info_cmd() -> None:
    """Print builder info (keeps `build` as a named subcommand)."""
    typer.echo("tools.builder — static prototype builder + Vercel deploy")
