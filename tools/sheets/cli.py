"""Typer CLI for the master Sheets tracking layer."""
from __future__ import annotations

import json
from pathlib import Path

import typer

from tools.sheets._schema import PHASES
from tools.sheets.client import SheetsClient

app = typer.Typer(add_completion=False, help="Master Sheet ops.")


def _parse_fields(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in pairs:
        if "=" not in p:
            raise typer.BadParameter(f"--field must be key=value, got {p!r}")
        k, v = p.split("=", 1)
        out[k.strip()] = v
    return out


@app.command("ensure-schema")
def ensure_schema() -> None:
    """Create worksheet if missing and write/repair header row."""
    sc = SheetsClient()
    sc.ensure_schema()
    typer.echo("schema ok")


@app.command("get-lead")
def get_lead(
    lead_id: str = typer.Argument(...),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    sc = SheetsClient()
    row = sc.get_lead(lead_id)
    if row is None:
        typer.echo("null")
        raise typer.Exit(code=1)
    typer.echo(json.dumps(row, indent=2 if pretty else None, ensure_ascii=False))


@app.command("upsert-lead")
def upsert_lead(
    lead_id: str = typer.Argument(...),
    field: list[str] = typer.Option([], "--field", help="key=value, repeatable"),
) -> None:
    sc = SheetsClient()
    sc.upsert_lead(lead_id, _parse_fields(field))
    typer.echo(f"upserted {lead_id}")


@app.command("update-status")
def update_status(
    lead_id: str = typer.Argument(...),
    phase: str = typer.Option(..., "--phase", help=f"one of {sorted(PHASES)}"),
    status: str = typer.Option(..., "--status"),
    note: str = typer.Option("", "--note"),
) -> None:
    sc = SheetsClient()
    sc.update_status(lead_id, phase, status, note=note)
    typer.echo(f"{lead_id} {phase}={status}")


@app.command("bulk-import")
def bulk_import(
    csv_path: Path = typer.Argument(..., exists=True, readable=True),
    dedupe_by: str = typer.Option("email", "--dedupe-by"),
) -> None:
    sc = SheetsClient()
    n = sc.bulk_import_csv(csv_path, dedupe_by=dedupe_by)
    typer.echo(f"inserted {n} new leads")


@app.command("find")
def find(
    vertical: str = typer.Option(None, "--vertical"),
    audit_status: str = typer.Option(None, "--audit-status"),
    email_status: str = typer.Option(None, "--email-status"),
    deal_status: str = typer.Option(None, "--deal-status"),
    limit: int = typer.Option(0, "--limit", min=0),
) -> None:
    filters = {
        k: v
        for k, v in {
            "vertical": vertical,
            "audit_status": audit_status,
            "email_status": email_status,
            "deal_status": deal_status,
        }.items()
        if v is not None
    }
    sc = SheetsClient()
    rows = sc.find_leads(**filters)
    if limit:
        rows = rows[:limit]
    typer.echo(json.dumps(rows, ensure_ascii=False))


@app.command("test")
def test() -> None:
    """Write a test row, read back, assert shape, delete. Smoke test."""
    sc = SheetsClient()
    sc.ensure_schema()
    test_id = "__test__"
    sc.upsert_lead(test_id, {"name": "Test User", "vertical": "other"})
    row = sc.get_lead(test_id)
    assert row is not None, "test row not found after upsert"
    assert row["lead_id"] == test_id
    assert row["name"] == "Test User"
    assert row["last_updated"], "last_updated not set"
    sc.delete_lead(test_id)
    assert sc.get_lead(test_id) is None, "test row not deleted"
    typer.echo("ok")
