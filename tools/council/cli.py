"""Typer CLI for the design council."""
from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

import typer

from tools.council.orchestrator import run_council
from tools.stitch._models import LeadContext

app = typer.Typer(add_completion=False, help="Design council — produce design_brief.md per lead.")


class VerticalChoice(str, Enum):
    restaurant = "restaurant"
    dental = "dental"
    realtor = "realtor"
    fnb = "fnb"


@app.command("run")
def run(
    lead_id: str = typer.Option(..., "--lead-id"),
    business: str = typer.Option(..., "--business"),
    vertical: VerticalChoice = typer.Option(..., "--vertical"),
    location: str | None = typer.Option(None, "--location"),
    service: list[str] = typer.Option([], "--service", help="repeatable"),
    phone: str | None = typer.Option(None, "--phone"),
    booking_provider: str | None = typer.Option(None, "--booking-provider"),
    tagline: str | None = typer.Option(None, "--tagline"),
    audit_json: Path | None = typer.Option(None, "--audit-json"),
    moodboard: Path | None = typer.Option(None, "--moodboard"),
    design_md: Path | None = typer.Option(None, "--design-md"),
    out_dir: Path = typer.Option(Path("data/outputs"), "--out-dir"),
    skip_llm: bool = typer.Option(False, "--skip-llm"),
    no_sheet: bool = typer.Option(False, "--no-sheet"),
    log_path: Path = typer.Option(Path(".hallmark/log.json"), "--log-path"),
) -> None:
    """Run the council for a single lead. Prints brief path."""
    lead = LeadContext(
        lead_id=lead_id,
        business=business,
        vertical=vertical.value,  # type: ignore[arg-type]
        tagline=tagline,
        services=list(service),
        location=location,
        phone=phone,
        booking_provider=booking_provider,
    )

    sheets_client = None
    if not no_sheet:
        try:
            from tools.sheets.client import SheetsClient
            sheets_client = SheetsClient()
        except Exception as exc:
            typer.echo(f"# sheets disabled: {exc}", err=True)
            sheets_client = None

    result = run_council(
        lead=lead,
        audit_json_path=audit_json,
        moodboard_path=moodboard,
        design_md_path=design_md,
        out_dir=out_dir,
        sheets_client=sheets_client,
        skip_llm=skip_llm,
        log_path=log_path,
    )
    typer.echo(result.brief_path)


@app.command("list-runs")
def list_runs(
    out_dir: Path = typer.Option(Path("data/outputs"), "--out-dir"),
) -> None:
    """List all design_brief.md files w/ chosen macrostructure + theme summary."""
    macro_re = re.compile(r"\*\*([^*]+)\*\*\s+—\s+page shape")
    theme_re = re.compile(r"- Name: \*\*([^*]+)\*\*")
    for brief in sorted(Path(out_dir).glob("*/design_brief.md")):
        text = brief.read_text(encoding="utf-8", errors="replace")
        m = macro_re.search(text)
        t = theme_re.search(text)
        macro = m.group(1) if m else "?"
        theme = t.group(1) if t else "?"
        typer.echo(f"{brief}\tmacro={macro}\ttheme={theme}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
