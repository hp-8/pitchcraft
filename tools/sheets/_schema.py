"""Master sheet schema definitions.

Header order MUST exactly match PLAN.md "Master Sheet Columns".
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

# Header row, in exact order. Source of truth for the worksheet schema.
COLUMNS: tuple[str, ...] = (
    "lead_id",
    "name",
    "business",
    "vertical",
    "email",
    "site_url",
    "audit_status",
    "audit_url",
    "audit_problems",
    "audit_dollar_impact",
    "ref_status",
    "moodboard_url",
    "stitch_status",
    "stitch_variants_url",
    "approved_variant",
    "prototype_status",
    "prototype_url",
    "deployed_at",
    "email_status",
    "email_sent_at",
    "email_subject",
    "email_body",
    "open_count",
    "click_count",
    "reply_status",
    "reply_text",
    "call_booked",
    "call_date",
    "proposal_status",
    "proposal_url",
    "proposal_sent_at",
    "deal_status",
    "amount_usd",
    "payment_method",
    "paid_at",
    "notes",
    "last_updated",
    "error_log",
)

# Valid phases for update_status().
PHASES: frozenset[str] = frozenset(
    {"audit", "ref", "stitch", "prototype", "email", "proposal", "deal"}
)


class Lead(BaseModel):
    """Pydantic model mirroring a master-sheet row. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    lead_id: Optional[str] = None
    name: Optional[str] = None
    business: Optional[str] = None
    vertical: Optional[str] = None
    email: Optional[str] = None
    site_url: Optional[str] = None
    audit_status: Optional[str] = None
    audit_url: Optional[str] = None
    audit_problems: Optional[str] = None
    audit_dollar_impact: Optional[float] = None
    ref_status: Optional[str] = None
    moodboard_url: Optional[str] = None
    stitch_status: Optional[str] = None
    stitch_variants_url: Optional[str] = None
    approved_variant: Optional[str] = None
    prototype_status: Optional[str] = None
    prototype_url: Optional[str] = None
    deployed_at: Optional[str] = None
    email_status: Optional[str] = None
    email_sent_at: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    open_count: Optional[int] = None
    click_count: Optional[int] = None
    reply_status: Optional[str] = None
    reply_text: Optional[str] = None
    call_booked: Optional[str] = None
    call_date: Optional[str] = None
    proposal_status: Optional[str] = None
    proposal_url: Optional[str] = None
    proposal_sent_at: Optional[str] = None
    deal_status: Optional[str] = None
    amount_usd: Optional[float] = None
    payment_method: Optional[str] = None
    paid_at: Optional[str] = None
    notes: Optional[str] = None
    last_updated: Optional[str] = None
    error_log: Optional[str] = None
