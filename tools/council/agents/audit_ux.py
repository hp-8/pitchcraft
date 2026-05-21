"""Audit-UX agent — maps audit problems to required sections per page."""
from __future__ import annotations

import logging
from typing import Any

from tools.audit._models import AuditResult

logger = logging.getLogger(__name__)

# code -> {must_section, pages: [...], requirement}
_PROBLEM_MAP: dict[str, dict[str, Any]] = {
    "weak_cta": {
        "section": "primary CTA above fold + repeated in footer band",
        "pages": ["landing", "services"],
        "requirement": "primary CTA mandatory above fold; repeat in footer band",
    },
    "no_phone": {
        "section": "phone in header + footer",
        "pages": ["landing", "services", "about", "contact"],
        "requirement": "phone number visible in header and footer",
    },
    "no_reservation": {
        "section": "reservation widget block",
        "pages": ["landing", "contact"],
        "requirement": "reservation widget anchored above the fold on contact, callout on landing",
    },
    "slow_lcp": {
        "section": "lazy-load below-fold imagery",
        "pages": ["landing"],
        "requirement": "lazy-load below-fold imagery; ship one optimised hero image",
    },
    "no_social_proof": {
        "section": "testimonial section before final CTA band",
        "pages": ["landing", "about"],
        "requirement": "real testimonial block (name + role + 1-line quote) before CTA",
    },
    "no_menu": {
        "section": "menu / services index callout",
        "pages": ["landing", "services"],
        "requirement": "menu / services index callout linked from landing",
    },
    "no_hours": {
        "section": "hours block in contact + footer",
        "pages": ["contact", "landing"],
        "requirement": "hours block in contact and footer",
    },
    "no_address": {
        "section": "address + map in contact",
        "pages": ["contact"],
        "requirement": "address + embedded or static map on contact",
    },
    "no_about": {
        "section": "about page founder note",
        "pages": ["about"],
        "requirement": "founder note + 1 candid photo on about",
    },
    "weak_seo_title": {
        "section": "concrete <title> with location + service",
        "pages": ["landing"],
        "requirement": "concrete <title> + meta description with location + primary service",
    },
}


def map_audit_to_sections(
    audit: AuditResult | None,
    vertical: str,
    skip_llm: bool = True,  # narrative path could call LLM; default off for determinism.
) -> dict[str, Any]:
    """Return {must_have_sections, per_page_requirements, priority_problems}."""
    if audit is None:
        return {
            "must_have_sections": [],
            "per_page_requirements": {"landing": [], "services": [], "about": [], "contact": []},
            "priority_problems": [],
            "narrative": "No audit supplied; UX requirements are minimal.",
        }

    must: list[str] = []
    per_page: dict[str, list[str]] = {"landing": [], "services": [], "about": [], "contact": []}
    priorities: list[str] = []

    # Severity ranking.
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    problems = sorted(audit.problems, key=lambda p: sev_rank.get(p.severity, 9))

    for p in problems:
        spec = _PROBLEM_MAP.get(p.code)
        if not spec:
            continue
        if spec["section"] not in must:
            must.append(spec["section"])
        for page in spec["pages"]:
            if spec["requirement"] not in per_page.get(page, []):
                per_page.setdefault(page, []).append(spec["requirement"])
        if p.severity in {"critical", "high"}:
            priorities.append(p.code)

    # Vertical-specific minimums.
    if vertical == "restaurant":
        for s in ("hours block in contact + footer", "menu / services index callout"):
            if s not in must:
                must.append(s)
    elif vertical == "dental":
        for s in ("hours block in contact + footer", "testimonial section before final CTA band"):
            if s not in must:
                must.append(s)

    narrative = (
        f"Top audit pressures: {', '.join(priorities) or 'none'}. "
        f"Brief enforces {len(must)} structural requirements drawn from the audit."
    )

    return {
        "must_have_sections": must,
        "per_page_requirements": per_page,
        "priority_problems": priorities,
        "narrative": narrative,
    }
