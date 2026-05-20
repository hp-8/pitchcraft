"""Stitch screen prompt builder + envelope writer.

Given a lead and an approved design system ID, build 12 (4 pages x 3 variants)
Stitch screen-generation prompts and serialize them as a single envelope JSON
under ``data/outputs/<lead_id>/stitch_screens_request.json``.

The actual MCP dispatch (``mcp__stitch__generate_screen_from_text``) is the
Phase 10 orchestrator's job — this module only writes intent.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tools.stitch._directions import (
    PAGES,
    VARIANT_DIRECTIONS,
    audit_to_page_notes,
    direction_paragraph,
)
from tools.stitch._models import LeadContext, Page, ScreenRequest

if TYPE_CHECKING:
    from tools.sheets.client import SheetsClient

__all__ = [
    "PAGES",
    "VARIANT_DIRECTIONS",
    "build_screen_prompts",
    "write_screens_request",
]


_HARD_REQUIREMENTS = """Hard requirements:
- Mobile-first.
- Above-the-fold CTA visible.
- Reserve space for these animation primitives (do not author the animations; the prototype builder wires them):
  - Hero kinetic typography slot
  - Scroll-triggered reveal markers (data-reveal attrs welcome)
  - Hover micro-interactions on cards & buttons
  - Marquee region (at least one)
  - Image lazy reveal containers
  - Smooth-scroll friendly layout (no scroll hijacking)
- Typography: use design system tokens.
- No lorem ipsum - use real copy seeded from brand context above."""


def _format_brand_block(lead: LeadContext) -> str:
    lines = [
        f"- Services: {', '.join(lead.services) if lead.services else 'not provided'}",
    ]
    if lead.booking_provider:
        lines.append(f"- Booking provider: {lead.booking_provider}")
    if lead.phone:
        lines.append(f"- Phone: {lead.phone}")
    if lead.tagline:
        lines.append(f"- Tagline: {lead.tagline}")
    if lead.extra_context:
        lines.append(f"- Extra: {lead.extra_context}")
    return "\n".join(lines)


def _build_prompt(
    lead: LeadContext,
    page: Page,
    direction: str,
    design_system_id: str,
    audit_problems: list[str] | None,
) -> str:
    location = lead.location or "their local market"
    notes = audit_to_page_notes(audit_problems, page)
    audit_block = (
        "\n".join(f"- {n}" for n in notes)
        if notes
        else "- (no audit-flagged pain points map to this page)"
    )
    return (
        f"You are designing the {page} page for {lead.business}, a {lead.vertical} "
        f"business in {location}.\n"
        f"Style direction: {direction}.\n"
        f"Use design system {design_system_id}.\n\n"
        f"Brand context:\n{_format_brand_block(lead)}\n\n"
        f"Solve these pain points the audit flagged:\n{audit_block}\n\n"
        f"{_HARD_REQUIREMENTS}\n\n"
        f"Page-specific layout direction: {direction_paragraph(direction)}"
    )


def build_screen_prompts(
    lead: LeadContext,
    design_system_id: str,
    audit_problems: list[str] | None = None,
    out_root: str | Path = "data/outputs",
) -> list[ScreenRequest]:
    """Produce the canonical 12 ScreenRequests (4 pages x 3 variants) in stable order."""
    out: list[ScreenRequest] = []
    for page in PAGES:
        for idx, direction in enumerate(VARIANT_DIRECTIONS[page]):
            target = Path(out_root) / lead.lead_id / "stitch" / f"{page}-v{idx}.json"
            out.append(
                ScreenRequest(
                    page=page,
                    variant_idx=idx,
                    variant_direction=direction,
                    prompt=_build_prompt(
                        lead, page, direction, design_system_id, audit_problems
                    ),
                    design_system_id=design_system_id,
                    target_path=str(target),
                )
            )
    return out


def _screen_to_envelope_entry(lead_id: str, s: ScreenRequest) -> dict[str, Any]:
    return {
        "page": s.page,
        "variant_idx": s.variant_idx,
        "variant_direction": s.variant_direction,
        "tool": "mcp__stitch__generate_screen_from_text",
        "args": {
            "prompt": s.prompt,
            "design_system_id": s.design_system_id,
            "name": f"{lead_id}-{s.page}-v{s.variant_idx}",
        },
        "fulfilled": False,
        "target_path": s.target_path,
    }


def write_screens_request(
    lead: LeadContext,
    design_system_id: str,
    audit_problems: list[str] | None = None,
    out_root: str | Path = "data/outputs",
    sheets_client: "SheetsClient | None" = None,
) -> Path:
    """Write the envelope JSON and (optionally) update the master sheet."""
    screens = build_screen_prompts(
        lead, design_system_id, audit_problems=audit_problems, out_root=out_root
    )
    out_dir = Path(out_root) / lead.lead_id
    out_dir.mkdir(parents=True, exist_ok=True)
    envelope_path = out_dir / "stitch_screens_request.json"

    envelope = {
        "lead_id": lead.lead_id,
        "business": lead.business,
        "vertical": lead.vertical,
        "design_system_id": design_system_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "screens": [_screen_to_envelope_entry(lead.lead_id, s) for s in screens],
    }
    envelope_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")

    if sheets_client is not None:
        sheets_client.upsert_lead(
            lead.lead_id,
            {
                "stitch_status": "queued",
                "stitch_variants_url": str(envelope_path),
            },
        )
        sheets_client.update_status(
            lead.lead_id, "stitch", "queued", note="queued 12 variants"
        )

    return envelope_path
