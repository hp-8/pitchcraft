"""Email CLI — single-lead build/send + batch send w/ 15min spacing."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import typer

from tools.email.agent import build_and_send

app = typer.Typer(add_completion=False, help="Email agent — template + LLM + Gmail SMTP.")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _load_lead_row(lead_id: str, leads_csv: Path) -> dict:
    import csv
    with leads_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("lead_id") == lead_id:
                return row
    raise typer.BadParameter(f"lead_id {lead_id} not in {leads_csv}")


def _load_audit(lead_dir: Path) -> dict:
    p = lead_dir / "audit.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


@app.command()
def preview(
    lead_id: str = typer.Option(..., "--lead-id"),
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False),
    lead_dir: Path = typer.Option(..., "--lead-dir", exists=True, file_okay=False),
    preview_url: str = typer.Option(..., "--preview-url"),
    no_llm: bool = typer.Option(False, "--no-llm"),
) -> None:
    """Build email + (optionally) LLM-polish; print without sending."""
    row = _load_lead_row(lead_id, leads)
    audit = _load_audit(lead_dir)
    out = build_and_send(row, audit, preview_url, use_llm=not no_llm, dry_run=True)
    typer.echo(json.dumps(out, indent=2))


@app.command("send-one")
def send_one(
    lead_id: str = typer.Option(..., "--lead-id"),
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False),
    lead_dir: Path = typer.Option(..., "--lead-dir", exists=True, file_okay=False),
    preview_url: str = typer.Option(..., "--preview-url"),
    no_llm: bool = typer.Option(False, "--no-llm"),
) -> None:
    """Build, polish, send. Logs subject/body."""
    row = _load_lead_row(lead_id, leads)
    audit = _load_audit(lead_dir)
    out = build_and_send(row, audit, preview_url, use_llm=not no_llm, dry_run=False)
    typer.echo(json.dumps({k: v for k, v in out.items() if k != "body"}, indent=2))


@app.command("send-batch")
def send_batch(
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False),
    out_dir: Path = typer.Option(Path("data/outputs"), "--out-dir"),
    cap_per_day: int = typer.Option(35, "--cap", min=1, max=500),
    spacing_seconds: int = typer.Option(900, "--spacing", min=60,
                                        help="Seconds between sends. Default 15min."),
    no_llm: bool = typer.Option(False, "--no-llm"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Send up to `cap_per_day` leads from CSV, spaced `spacing_seconds` apart.

    Reads each lead's preview URL from `<out_dir>/<slug>/polish_report.json` or
    falls back to the `prototype_url` field in CSV.
    """
    import csv
    import time
    from urllib.parse import urlparse

    sent = 0
    with leads.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if sent >= cap_per_day:
                break
            if not row.get("email"):
                continue
            preview_url = row.get("prototype_url") or row.get("preview_url")
            if not preview_url:
                slug = urlparse(row.get("site_url", "")).hostname or row["lead_id"]
                slug = slug.replace(".", "-")
                report = out_dir / slug / "polish_report.json"
                if report.exists():
                    try:
                        data = json.loads(report.read_text(encoding="utf-8"))
                        preview_url = data.get("deploy_url") or data.get("site_dir")
                    except Exception:
                        preview_url = None
            if not preview_url:
                typer.echo(f"skip {row['lead_id']}: no preview_url")
                continue

            audit_dir = out_dir / (urlparse(row.get("site_url", "")).hostname or row["lead_id"]).replace(".", "-")
            audit = _load_audit(audit_dir)
            try:
                out = build_and_send(
                    row, audit, preview_url, use_llm=not no_llm, dry_run=dry_run,
                )
                typer.echo(json.dumps({k: v for k, v in out.items() if k != "body"}))
                sent += 1
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"ERROR {row['lead_id']}: {exc}", err=True)
                continue
            if sent < cap_per_day and not dry_run:
                time.sleep(spacing_seconds)
    typer.echo(f"done. sent={sent}")
