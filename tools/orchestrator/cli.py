"""Orchestrator CLI — run-batch, resume, status, probe-stitch."""
from __future__ import annotations

import asyncio
import csv
import json
import logging
from pathlib import Path
from typing import Optional

import typer

from tools.orchestrator._models import LeadJob
from tools.orchestrator.runner import resume_post_stitch, run_batch

app = typer.Typer(add_completion=False, help="Pipeline orchestrator.")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _load_jobs_csv(path: Path) -> list[LeadJob]:
    """Minimal CSV: lead_id,business,vertical,site_url,email,location,name,tagline."""
    jobs: list[LeadJob] = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            services_raw = row.get("services") or ""
            services = [s.strip() for s in services_raw.split("|") if s.strip()]
            jobs.append(LeadJob(
                lead_id=row["lead_id"], business=row["business"],
                vertical=row["vertical"], site_url=row["site_url"],
                email=row.get("email") or None, name=row.get("name") or None,
                location=row.get("location") or None, tagline=row.get("tagline") or None,
                services=services, phone=row.get("phone") or None,
            ))
    return jobs


def _load_jobs_json(path: Path) -> list[LeadJob]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("leads", [])
    return [LeadJob.model_validate(d) for d in data]


def _load_jobs(path: Path) -> list[LeadJob]:
    if path.suffix.lower() == ".csv":
        return _load_jobs_csv(path)
    return _load_jobs_json(path)


@app.command("run-batch")
def run_batch_cmd(
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False,
                               help="CSV or JSON listing leads."),
    design_system_id: str = typer.Option(..., "--design-system-id",
                                         help="Shared Stitch design system asset ID."),
    no_sheet: bool = typer.Option(False, "--no-sheet"),
    skip_deploy: bool = typer.Option(False, "--skip-deploy"),
    pause_at_stitch: bool = typer.Option(True, "--pause-at-stitch/--no-pause"),
) -> None:
    """Run pre-stitch phases (scrape, audit, design_ref, council fire-and-forget,
    stitch envelope) for all leads in parallel. Pauses before MCP fulfillment."""
    jobs = _load_jobs(leads)
    sc = None
    if not no_sheet:
        try:
            from tools.sheets.client import SheetsClient
            sc = SheetsClient()
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"sheets unavailable: {exc}", err=True)
    result = asyncio.run(run_batch(jobs, design_system_id, sheets_client=sc,
                                   skip_deploy=skip_deploy, pause_at_stitch=pause_at_stitch))
    typer.echo(json.dumps(result.model_dump(), indent=2))


@app.command("resume")
def resume_cmd(
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False),
    no_sheet: bool = typer.Option(False, "--no-sheet"),
    skip_deploy: bool = typer.Option(False, "--skip-deploy"),
) -> None:
    """After Stitch fulfillment, drive polish + build/deploy in parallel."""
    jobs = _load_jobs(leads)
    sc = None
    if not no_sheet:
        try:
            from tools.sheets.client import SheetsClient
            sc = SheetsClient()
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"sheets unavailable: {exc}", err=True)
    result = asyncio.run(resume_post_stitch(jobs, sheets_client=sc, skip_deploy=skip_deploy))
    typer.echo(json.dumps(result.model_dump(), indent=2))


@app.command("status")
def status_cmd() -> None:
    """Print last batch state."""
    p = Path(".orchestrator/last_batch.json")
    if not p.exists():
        typer.echo("no prior batch")
        raise typer.Exit(code=1)
    typer.echo(p.read_text())


@app.command("set-stitch-cap")
def set_stitch_cap_cmd(
    n: int = typer.Option(..., "--n", min=1, max=20),
    note: str = typer.Option("", "--note"),
) -> None:
    """Manually set Stitch fulfillment concurrency cap.

    Writes .orchestrator/stitch_caps.json. Replace with a probe later.
    """
    p = Path(".orchestrator")
    p.mkdir(parents=True, exist_ok=True)
    out = p / "stitch_caps.json"
    out.write_text(json.dumps({
        "recommended_concurrency": n,
        "note": note or "manually set",
    }, indent=2), encoding="utf-8")
    typer.echo(f"wrote {out}")


@app.command("pending-screens")
def pending_screens_cmd(
    out_dir: Path = typer.Option(Path("data/outputs"), "--out-dir"),
) -> None:
    """Emit JSONL of all pending Stitch screens across envelopes.

    Consumed by the CC-side /stitch-batch skill which calls MCP per row.
    Output: {envelope, idx, tool, args, target_path, lead_id}
    """
    for env_path in sorted(out_dir.glob("*/stitch_screens_request.json")):
        try:
            data = json.loads(env_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for idx, screen in enumerate(data.get("screens", [])):
            if screen.get("fulfilled"):
                continue
            typer.echo(json.dumps({
                "envelope": str(env_path),
                "lead_id": data.get("lead_id"),
                "idx": idx,
                "tool": screen.get("tool"),
                "args": screen.get("args"),
                "target_path": screen.get("target_path"),
            }))
