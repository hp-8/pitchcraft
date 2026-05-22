"""PDF CLI: proposal, audit, both. Per-lead inputs from CSV + lead dir."""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer

from tools.pdf.audit import build_audit_pdf
from tools.pdf.proposal import build_proposal_pdf

app = typer.Typer(add_completion=False, help="Proposal + audit PDF generator.")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _load_lead_row(lead_id: str, leads_csv: Path) -> dict:
    with leads_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("lead_id") == lead_id:
                return row
    raise typer.BadParameter(f"lead_id {lead_id} not in {leads_csv}")


def _load_audit(lead_dir: Path) -> dict:
    p = lead_dir / "audit.json"
    if not p.exists():
        raise typer.BadParameter(f"audit.json missing in {lead_dir}")
    return json.loads(p.read_text(encoding="utf-8"))


def _slug_dir(out_root: Path, lead_row: dict) -> Path:
    host = urlparse(lead_row.get("site_url", "")).hostname or lead_row["lead_id"]
    return out_root / host.replace(".", "-")


@app.command()
def proposal(
    lead_id: str = typer.Option(..., "--lead-id"),
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False),
    lead_dir: Optional[Path] = typer.Option(None, "--lead-dir"),
    preview_url: Optional[str] = typer.Option(None, "--preview-url"),
    book_call_url: str = typer.Option("https://calendar.app.google/hqKrMkn66PddNMaS8", "--book-call-url"),
    price: str = typer.Option("$2,400", "--price"),
    out: Optional[Path] = typer.Option(None, "--out"),
    out_root: Path = typer.Option(Path("data/outputs"), "--out-root"),
) -> None:
    """Build 1-page proposal PDF for one lead."""
    row = _load_lead_row(lead_id, leads)
    ld = lead_dir or _slug_dir(out_root, row)
    audit = _load_audit(ld)
    out_path = out or ld / "proposal.pdf"
    build_proposal_pdf(
        row, audit, out_path,
        preview_url=preview_url or row.get("prototype_url"),
        book_call_url=book_call_url, price=price,
    )
    typer.echo(str(out_path))


@app.command()
def audit(
    lead_id: str = typer.Option(..., "--lead-id"),
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False),
    lead_dir: Optional[Path] = typer.Option(None, "--lead-dir"),
    out: Optional[Path] = typer.Option(None, "--out"),
    out_root: Path = typer.Option(Path("data/outputs"), "--out-root"),
) -> None:
    """Build multi-page audit PDF for one lead."""
    row = _load_lead_row(lead_id, leads)
    ld = lead_dir or _slug_dir(out_root, row)
    audit_data = _load_audit(ld)
    out_path = out or ld / "audit.pdf"
    build_audit_pdf(row, audit_data, out_path)
    typer.echo(str(out_path))


@app.command()
def both(
    lead_id: str = typer.Option(..., "--lead-id"),
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False),
    lead_dir: Optional[Path] = typer.Option(None, "--lead-dir"),
    preview_url: Optional[str] = typer.Option(None, "--preview-url"),
    book_call_url: str = typer.Option("https://calendar.app.google/hqKrMkn66PddNMaS8", "--book-call-url"),
    price: str = typer.Option("$2,400", "--price"),
    out_root: Path = typer.Option(Path("data/outputs"), "--out-root"),
) -> None:
    """Build both proposal + audit PDFs for one lead."""
    row = _load_lead_row(lead_id, leads)
    ld = lead_dir or _slug_dir(out_root, row)
    audit_data = _load_audit(ld)
    p1 = ld / "proposal.pdf"
    p2 = ld / "audit.pdf"
    build_proposal_pdf(
        row, audit_data, p1,
        preview_url=preview_url or row.get("prototype_url"),
        book_call_url=book_call_url, price=price,
    )
    build_audit_pdf(row, audit_data, p2)
    typer.echo(json.dumps({"proposal": str(p1), "audit": str(p2)}, indent=2))


@app.command()
def batch(
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False),
    out_root: Path = typer.Option(Path("data/outputs"), "--out-root"),
    preview_field: str = typer.Option("prototype_url", "--preview-field"),
    book_call_url: str = typer.Option("https://calendar.app.google/hqKrMkn66PddNMaS8", "--book-call-url"),
    price: str = typer.Option("$2,400", "--price"),
) -> None:
    """Render proposal + audit PDFs for every lead in the CSV."""
    results = []
    with leads.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                ld = _slug_dir(out_root, row)
                audit_data = _load_audit(ld)
                p1 = ld / "proposal.pdf"
                p2 = ld / "audit.pdf"
                build_proposal_pdf(
                    row, audit_data, p1,
                    preview_url=row.get(preview_field),
                    book_call_url=book_call_url, price=price,
                )
                build_audit_pdf(row, audit_data, p2)
                results.append({"lead_id": row["lead_id"], "ok": True,
                                "proposal": str(p1), "audit": str(p2)})
            except Exception as exc:  # noqa: BLE001
                results.append({"lead_id": row["lead_id"], "ok": False, "error": str(exc)})
    typer.echo(json.dumps(results, indent=2))


@app.command()
def bundle(
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False),
    out_root: Path = typer.Option(Path("data/outputs"), "--out-root"),
    deliverables_root: Path = typer.Option(Path("data/deliverables"), "--deliverables-root"),
) -> None:
    """Bundle final PDFs + index.html + README per lead into deliverables_root."""
    from tools.pdf.deliverables import bundle_lead
    results = []
    with leads.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                dst = bundle_lead(row, out_root=out_root, deliverables_root=deliverables_root)
                results.append({"lead_id": row["lead_id"], "ok": True, "dir": str(dst)})
            except Exception as exc:  # noqa: BLE001
                results.append({"lead_id": row["lead_id"], "ok": False, "error": str(exc)})
    typer.echo(json.dumps(results, indent=2))
