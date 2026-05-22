"""Email agent — orchestrates template + optional LLM polish + Gmail send.

Single-lead entry: `build_and_send(lead, audit, preview_url, dry_run, use_llm)`.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.email.gmail_send import send as gmail_send
from tools.email.llm import polish as llm_polish
from tools.email.template import build_email

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _socials_block() -> str:
    return (
        "Portfolio: https://harshpatadia.dev\n"
        "LinkedIn: https://linkedin.com/in/harshpatadia"
    )


def build_and_send(
    lead: dict[str, Any],
    audit: dict[str, Any],
    preview_url: str,
    sender_name: str = "Harsh Patadia",
    sender_socials: str | None = None,
    use_llm: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Build + (optionally polish) + send. Returns {subject, body, sent_at, to, dry_run}."""
    socials = sender_socials or _socials_block()
    base = build_email(lead, audit, preview_url, sender_name, socials)
    subject = base["subject"]
    body = base["body"]

    if use_llm:
        subject, body = llm_polish(subject, body, lead)

    out: dict[str, Any] = {
        "lead_id": lead.get("lead_id"),
        "to": lead.get("email"),
        "subject": subject,
        "body": body,
        "dry_run": dry_run,
        "polished_by_llm": use_llm,
    }
    if dry_run:
        return out

    if not lead.get("email"):
        raise RuntimeError(f"missing email for lead_id={lead.get('lead_id')}")

    sent = gmail_send(
        to_address=lead["email"],
        subject=subject,
        body_text=body,
        from_name=sender_name,
    )
    out["sent_at"] = _utc_now()
    out["sent"] = sent
    return out
