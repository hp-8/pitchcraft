"""Email template — audit-driven swap blocks, deterministic, human-tone.

Three concerns:
1. Subject rotation: 3 templates × audit hooks, picked by hash of lead_id.
2. Body sections: greeting, hook (problem-specific), $impact, preview link, CTA, sign-off.
3. Swap blocks: keyed on audit problem `code`, e.g. `slow_lcp`, `no_mobile_meta`.

LLM polish is an optional second pass (see llm.py).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# ---- Subject lines (rotate via hash) ---------------------------------------

SUBJECT_TEMPLATES: tuple[str, ...] = (
    "Quick note on {business}'s site",
    "Saw something on {business}.com worth flagging",
    "A 2-min audit of {business}.com — ${low}-${high}/mo at risk",
    "{business} — three site issues quietly costing you",
)


def _pick_subject(lead_id: str, business: str, low: int, high: int) -> str:
    h = int(hashlib.sha256(lead_id.encode()).hexdigest()[:8], 16)
    tmpl = SUBJECT_TEMPLATES[h % len(SUBJECT_TEMPLATES)]
    return tmpl.format(business=business, low=low, high=high)


# ---- Hook swap blocks (audit problem code → one-liner) ---------------------

HOOK_BLOCKS: dict[str, str] = {
    "slow_lcp": "Your site's largest content takes {evidence} to render — Google's threshold is 2.5s. That alone roughly doubles bounce.",
    "low_perf_score": "Your PageSpeed score sits at {evidence} (mobile). Anything under 0.5 actively hurts both rankings and conversion.",
    "slow_tbt": "Total blocking time is {evidence} — anything over 300ms makes the page feel sluggish.",
    "slow_inp": "Interaction delay is {evidence}; >200ms feels laggy and visibly drives drop-off.",
    "no_mobile_meta": "There's no viewport meta tag — the mobile version of the site renders broken at most screen sizes.",
    "no_schema_org": "No Schema.org / JSON-LD markup. Google can't generate rich results for you, so you miss the visual cards in search.",
    "no_order_online": "There's no online ordering flow. For your category, that's usually 20–40% of revenue lost on the table.",
    "no_address": "No business address surfaced on the homepage — hurts local SEO and trust signals.",
    "no_social_proof": "No reviews or testimonials are visible. For hospitality, social proof drives most first-time bookings.",
}


def _hook_for(problems: list[dict[str, Any]]) -> str:
    """Pick first matching block from problems list."""
    for p in problems:
        code = p.get("code", "")
        block = HOOK_BLOCKS.get(code)
        if block:
            ev = p.get("evidence") or ""
            return block.format(evidence=ev)
    return ""


# ---- Body assembly ---------------------------------------------------------


BODY_TEMPLATE = """\
Hi{name_clause},

I was running a quick audit on {business}.com{location_clause} and noticed a few things worth flagging.

{hook}

Based on the issues stacked up, the site is quietly leaking somewhere between CA${low} and CA${high} per month in missed inquiries and conversions. That's a rough range, but the math behind it is in the attached audit if useful.

I put together a redesigned prototype showing how the homepage and trade-facing pages could feel — it's live here:
{preview_url}

If any of it lands, happy to walk through it on a quick call — no obligation.

— {sender_name}
{sender_socials}
"""


def build_email(
    lead: dict[str, Any],
    audit: dict[str, Any],
    preview_url: str,
    sender_name: str = "Harsh Patadia",
    sender_socials: str | None = None,
) -> dict[str, str]:
    """Returns {subject, body}. Deterministic — no LLM."""
    business = lead.get("business") or "your business"
    name = (lead.get("name") or "").strip()
    location = lead.get("location") or ""
    name_clause = f" {name.split()[0]}" if name else ""
    location_clause = f" (you're in {location})" if location else ""

    impact = audit.get("dollar_impact") or {}
    low = int(impact.get("monthly_loss_low") or 0)
    high = int(impact.get("monthly_loss_high") or 0)
    problems = audit.get("problems") or []

    hook = _hook_for(problems) or (
        "A few small things are quietly hurting search visibility and conversion — easy fixes that compound."
    )

    body = BODY_TEMPLATE.format(
        name_clause=name_clause,
        business=business,
        location_clause=location_clause,
        hook=hook,
        low=low,
        high=high,
        preview_url=preview_url,
        sender_name=sender_name,
        sender_socials=sender_socials or "",
    ).strip() + "\n"

    subject = _pick_subject(lead.get("lead_id", "x"), business, low, high)
    return {"subject": subject, "body": body}


def load_inputs(lead_dir: Path, lead_row: dict[str, Any]) -> tuple[dict, dict]:
    """Convenience: load audit.json from disk; return (lead_row, audit_dict)."""
    audit_path = Path(lead_dir) / "audit.json"
    audit = {}
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    return lead_row, audit
