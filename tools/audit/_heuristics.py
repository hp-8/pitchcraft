"""Heuristic checks on a scraped page (markdown + html + vertical context)."""
from __future__ import annotations

import re

from tools.audit._models import Problem

CTA_PATTERN = re.compile(
    r"\b(book|reserve|order|call|schedule|get\s*(a\s*)?quote|contact|sign\s*up|buy)\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(\+?\d{1,2}\s*[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
)
ADDRESS_PATTERN = re.compile(
    r"\b\d{1,6}\s+\w+(\s+\w+)*\s+"
    r"(street|st\.?|avenue|ave\.?|road|rd\.?|blvd\.?|boulevard|lane|ln\.?|drive|dr\.?|way|court|ct\.?|place|pl\.?|hwy|highway)\b",
    re.IGNORECASE,
)
VIEWPORT_PATTERN = re.compile(r"<meta[^>]+name=[\"']?viewport[\"']?", re.IGNORECASE)
H1_PATTERN = re.compile(r"<h1[\s>]", re.IGNORECASE)
LDJSON_PATTERN = re.compile(
    r"<script[^>]+type=[\"']?application/ld\+json[\"']?",
    re.IGNORECASE,
)
ITEMSCOPE_PATTERN = re.compile(r"itemscope", re.IGNORECASE)
TABLE_LAYOUT_PATTERN = re.compile(r"<table[\s>]", re.IGNORECASE)
INLINE_FONT_PATTERN = re.compile(r"style=[\"'][^\"']*font\s*:", re.IGNORECASE)
DATED_FRAMEWORK_PATTERN = re.compile(
    r"(wix-image|godaddy|weebly|squarespace-v6|frontpage|geocities)",
    re.IGNORECASE,
)
SOCIAL_PROOF_PATTERN = re.compile(
    r"\b(review|testimonial|rating|stars?|⭐|★)\b",
    re.IGNORECASE,
)

VERTICAL_CTA_FALLBACK = {
    "restaurant": re.compile(r"\b(menu|reservation|order)\b", re.IGNORECASE),
    "dental": re.compile(r"\b(appointment|booking|consultation)\b", re.IGNORECASE),
    "realtor": re.compile(r"\b(listing|tour|showing|home\s*search)\b", re.IGNORECASE),
    "fnb": re.compile(r"\b(order|delivery|pickup|menu)\b", re.IGNORECASE),
}


def _evidence(text: str, n: int = 140) -> str:
    text = text.strip().replace("\n", " ")
    return text[:n] + ("…" if len(text) > n else "")


def _has(pattern: re.Pattern[str], text: str) -> bool:
    return bool(pattern.search(text or ""))


def _no_h1(html: str) -> Problem | None:
    if _has(H1_PATTERN, html):
        return None
    return Problem(
        code="no_h1",
        severity="high",
        message="Page has no <h1> tag; weak for SEO and accessibility.",
    )


def _weak_cta(markdown: str, html: str, vertical: str) -> Problem | None:
    blob = f"{markdown}\n{html}"
    if _has(CTA_PATTERN, blob):
        return None
    fallback = VERTICAL_CTA_FALLBACK.get(vertical)
    if fallback and _has(fallback, blob):
        return None
    return Problem(
        code="weak_cta",
        severity="critical",
        message="No clear call-to-action (book/reserve/order/call/contact).",
    )


def _no_phone(markdown: str) -> Problem | None:
    if _has(PHONE_PATTERN, markdown):
        return None
    return Problem(
        code="no_phone",
        severity="high",
        message="No phone number visible on the page.",
    )


def _no_address(markdown: str) -> Problem | None:
    if _has(ADDRESS_PATTERN, markdown):
        return None
    return Problem(
        code="no_address",
        severity="medium",
        message="No street address visible (number + street keyword).",
    )


def _no_mobile_meta(html: str) -> Problem | None:
    if _has(VIEWPORT_PATTERN, html):
        return None
    return Problem(
        code="no_mobile_meta",
        severity="high",
        message="No <meta name='viewport'>; mobile rendering will be broken.",
    )


def _no_schema_org(html: str) -> Problem | None:
    if _has(LDJSON_PATTERN, html) or _has(ITEMSCOPE_PATTERN, html):
        return None
    return Problem(
        code="no_schema_org",
        severity="medium",
        message="No Schema.org / JSON-LD markup; weaker rich-result eligibility.",
    )


def _no_https(url: str) -> Problem | None:
    if url.lower().startswith("https://"):
        return None
    return Problem(
        code="no_https",
        severity="critical",
        message="Site served over HTTP; browsers flag as insecure.",
        evidence=url,
    )


def _dated_design(html: str) -> Problem | None:
    hits = []
    if _has(TABLE_LAYOUT_PATTERN, html):
        hits.append("<table> for layout")
    if _has(INLINE_FONT_PATTERN, html):
        hits.append("inline font styles")
    m = DATED_FRAMEWORK_PATTERN.search(html or "")
    if m:
        hits.append(f"legacy builder: {m.group(0)}")
    if not hits:
        return None
    return Problem(
        code="dated_design_signals",
        severity="medium",
        message="Visual signals of dated design / legacy builder.",
        evidence="; ".join(hits),
    )


def _no_social_proof(blob: str) -> Problem | None:
    if _has(SOCIAL_PROOF_PATTERN, blob):
        return None
    return Problem(
        code="no_social_proof",
        severity="medium",
        message="No reviews / testimonials / ratings visible.",
    )


def _vertical_checks(markdown: str, html: str, vertical: str) -> list[Problem]:
    blob = (markdown + "\n" + html).lower()
    out: list[Problem] = []

    if vertical == "restaurant":
        if "menu" not in blob:
            out.append(Problem(code="no_menu", severity="critical",
                               message="No menu link/text found."))
        if not re.search(r"reserv(e|ation)|opentable|resy", blob):
            out.append(Problem(code="no_reservation", severity="high",
                               message="No reservation option (OpenTable/Resy/inline)."))
    elif vertical == "dental":
        if not re.search(r"book|appoint|schedule", blob):
            out.append(Problem(code="no_booking", severity="critical",
                               message="No online booking / appointment scheduling."))
        if "insurance" not in blob:
            out.append(Problem(code="no_insurance_info", severity="medium",
                               message="No insurance information listed."))
    elif vertical == "realtor":
        if not re.search(r"listing|propert(y|ies)|home\s*for\s*sale", blob):
            out.append(Problem(code="no_listings", severity="critical",
                               message="No property listings visible."))
        if not re.search(r"idx|mls|home\s*search", blob):
            out.append(Problem(code="no_idx_widget", severity="high",
                               message="No IDX/MLS search widget detected."))
    elif vertical == "fnb":
        if "menu" not in blob:
            out.append(Problem(code="no_menu", severity="critical",
                               message="No menu link/text found."))
        if not re.search(r"order\s*(online|now)|doordash|ubereats|grubhub", blob):
            out.append(Problem(code="no_order_online", severity="critical",
                               message="No online ordering option."))
    return out


def run_heuristics(markdown: str, html: str, vertical: str, url: str = "") -> list[Problem]:
    """Run all heuristic checks and return Problems found."""
    markdown = markdown or ""
    html = html or ""
    problems: list[Problem] = []

    for check in (
        _no_h1(html),
        _weak_cta(markdown, html, vertical),
        _no_phone(markdown),
        _no_address(markdown),
        _no_mobile_meta(html),
        _no_schema_org(html),
        _no_https(url) if url else None,
        _dated_design(html),
        _no_social_proof(markdown + "\n" + html),
    ):
        if check is not None:
            problems.append(check)

    problems.extend(_vertical_checks(markdown, html, vertical))
    return problems
