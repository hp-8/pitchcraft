"""Typer CLI for Stitch screen envelope generation."""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

import typer

from tools.audit._models import AuditResult
from tools.stitch._models import LeadContext
from tools.stitch.fulfiller import (
    finalize_envelope,
    iter_pending_envelopes,
    iter_pending_screens,
    mark_screen_error,
    mark_screen_fulfilled,
)
from tools.stitch.screens import write_screens_request

app = typer.Typer(add_completion=False, help="Stitch screen envelope ops.")


class VerticalChoice(str, Enum):
    restaurant = "restaurant"
    dental = "dental"
    realtor = "realtor"
    fnb = "fnb"


def _load_audit_problems(path: Path | None) -> list[str] | None:
    if path is None:
        return None
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    audit = AuditResult.model_validate(raw)
    return [p.code for p in audit.problems]


@app.command("build-screens")
def build_screens(
    lead_id: str = typer.Option(..., "--lead-id"),
    business: str = typer.Option(..., "--business"),
    vertical: VerticalChoice = typer.Option(..., "--vertical"),
    design_system_id: str = typer.Option(..., "--design-system-id"),
    tagline: str | None = typer.Option(None, "--tagline"),
    service: list[str] = typer.Option([], "--service", help="repeatable"),
    location: str | None = typer.Option(None, "--location"),
    phone: str | None = typer.Option(None, "--phone"),
    booking_provider: str | None = typer.Option(None, "--booking-provider"),
    extra_context: str | None = typer.Option(None, "--extra-context"),
    audit_json: Path | None = typer.Option(
        None, "--audit-json", exists=True, readable=True, dir_okay=False
    ),
    out_dir: Path = typer.Option(Path("data/outputs"), "--out-dir"),
) -> None:
    """Build the 12-screen Stitch request envelope for a lead."""
    lead = LeadContext(
        lead_id=lead_id,
        business=business,
        vertical=vertical.value,  # type: ignore[arg-type]
        tagline=tagline,
        services=list(service),
        location=location,
        phone=phone,
        booking_provider=booking_provider,
        extra_context=extra_context,
    )
    problems = _load_audit_problems(audit_json)
    envelope = write_screens_request(
        lead, design_system_id, audit_problems=problems, out_root=out_dir
    )
    typer.echo(str(envelope))


@app.command("list-envelopes")
def list_envelopes(
    out_dir: Path = typer.Option(Path("data/outputs"), "--out-dir"),
) -> None:
    """List all stitch_screens_request.json envelopes and their fulfilled count."""
    for env_path in sorted(Path(out_dir).glob("*/stitch_screens_request.json")):
        try:
            data = json.loads(env_path.read_text(encoding="utf-8"))
            screens = data.get("screens", [])
            fulfilled = sum(1 for s in screens if s.get("fulfilled"))
            typer.echo(f"{env_path}\tfulfilled={fulfilled}/{len(screens)}")
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"{env_path}\tERROR {exc}")


@app.command("pending")
def pending(
    out_dir: Path = typer.Option(Path("data/outputs"), "--out-dir"),
) -> None:
    """Emit JSONL of pending screens for orchestrator dispatch."""
    for env_path in iter_pending_envelopes(out_dir):
        for idx, screen in iter_pending_screens(env_path):
            typer.echo(
                json.dumps(
                    {
                        "envelope": str(env_path),
                        "idx": idx,
                        "tool": screen["tool"],
                        "args": screen["args"],
                        "target_path": screen["target_path"],
                        "page": screen["page"],
                        "variant_idx": screen["variant_idx"],
                    }
                )
            )


@app.command("fulfill")
def fulfill(
    envelope: Path = typer.Option(..., "--envelope", exists=True, dir_okay=False),
    idx: int = typer.Option(..., "--idx"),
    result_file: Path = typer.Option(
        ..., "--result-file", exists=True, dir_okay=False,
        help="JSON file with the Stitch tool's return payload.",
    ),
    html_file: Path | None = typer.Option(
        None, "--html-file", exists=True, dir_okay=False,
        help="Optional sibling HTML to save next to target_path.",
    ),
) -> None:
    """Mark screen fulfilled with Stitch return payload."""
    payload = json.loads(result_file.read_text(encoding="utf-8"))
    html = html_file.read_text(encoding="utf-8") if html_file else None
    mark_screen_fulfilled(envelope, idx, payload, html_content=html)
    typer.echo(f"ok envelope={envelope} idx={idx}")


@app.command("fulfill-error")
def fulfill_error_cmd(
    envelope: Path = typer.Option(..., "--envelope", exists=True, dir_okay=False),
    idx: int = typer.Option(..., "--idx"),
    error: str = typer.Option(..., "--error"),
) -> None:
    """Mark screen fulfilled with an error (so batch keeps moving)."""
    mark_screen_error(envelope, idx, error)
    typer.echo(f"error_recorded envelope={envelope} idx={idx}")


@app.command("finalize")
def finalize(
    envelope: Path = typer.Option(..., "--envelope", exists=True, dir_okay=False),
) -> None:
    """Stamp final status (queued|partial|ready) onto envelope."""
    status = finalize_envelope(envelope)
    typer.echo(status)
