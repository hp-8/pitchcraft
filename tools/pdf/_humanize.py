"""Translate audit problem codes into plain-English copy + a 'why it matters' line."""
from __future__ import annotations

from typing import Any

# code → (plain-English headline, why-it-matters, recommended-fix)
PROBLEM_COPY: dict[str, tuple[str, str, str]] = {
    "slow_lcp": (
        "The site takes too long to show its main content.",
        "Google's threshold is 2.5s. Anything above roughly doubles bounce, visitors leave before the page paints.",
        "Compress hero images, cut unused JS, defer non-critical scripts, move to a faster host or CDN.",
    ),
    "slow_tbt": (
        "The site is locked up during page load.",
        "Heavy JS keeps the browser busy for a full second instead of letting visitors click or scroll.",
        "Reduce third-party scripts, split JS bundles, defer non-critical work.",
    ),
    "slow_inp": (
        "Interactions feel laggy.",
        "Buttons take >200ms to respond after a tap, visibly slow on real phones.",
        "Audit click handlers, reduce main-thread work, replace large libs with lighter alternatives.",
    ),
    "low_perf_score": (
        "Overall mobile performance score is poor.",
        "PageSpeed gives the site a near-failing grade. This hurts both Google ranking and visitor patience.",
        "End-to-end performance pass: images, JS, fonts, render-blocking CSS.",
    ),
    "no_mobile_meta": (
        "Mobile rendering is broken.",
        "The viewport meta tag is missing, so the site renders at desktop width on phones, most visitors never see usable content.",
        "Add `<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">` plus a mobile-first CSS pass.",
    ),
    "no_schema_org": (
        "Google can't read the site's business info cleanly.",
        "No JSON-LD / Schema.org markup means Google can't generate rich result cards, you lose the visual treatment in search.",
        "Add LocalBusiness + Product + Organization schema. ~1 afternoon.",
    ),
    "no_address": (
        "No physical address on the homepage.",
        "Hurts local SEO and trust. Visitors don't immediately see whether the business serves them.",
        "Surface the address in the footer + dedicated contact block with map embed.",
    ),
    "no_phone": (
        "No phone number visible.",
        "B2B and hospitality visitors want a phone to call. Missing it kills the warmest leads.",
        "Add a click-to-call link in nav + footer.",
    ),
    "no_order_online": (
        "No online ordering / inquiry path.",
        "For this category, online orders or trade inquiries usually account for 20 to 40% of revenue.",
        "Add a checkout flow or trade inquiry form with allocation/quantity capture.",
    ),
    "no_social_proof": (
        "No reviews or testimonials shown.",
        "First-time buyers and trade accounts both anchor on social proof. Without it, conversion drops.",
        "Add a 3-4 quote testimonial block + a press/accounts strip.",
    ),
    "no_h1": (
        "Page has no top-level heading.",
        "Google uses the H1 as the page's primary subject. Missing H1 weakens ranking + accessibility.",
        "Add one clear H1 per page describing what the page is for.",
    ),
    "dated_design_signals": (
        "The site looks dated.",
        "Visitors form a trust judgment in <1 second. Outdated visuals push them to a competitor before content even loads.",
        "Modern editorial layout, current font stack, generous whitespace, real photography.",
    ),
    "layout_shift": (
        "Page jumps around as it loads.",
        "High Cumulative Layout Shift means buttons move just as visitors tap them, frustrating and Google penalizes it.",
        "Reserve image/iframe heights up front; load fonts with `font-display: optional`.",
    ),
}


def humanize_problem(p: dict[str, Any]) -> dict[str, str]:
    code = p.get("code", "")
    severity = p.get("severity", "medium")
    evidence = p.get("evidence") or ""
    headline, why, fix = PROBLEM_COPY.get(
        code,
        (
            p.get("message", "Site issue detected.").rstrip("."),
            "Issue impacts visibility, trust, or conversion.",
            "Manual review recommended.",
        ),
    )
    return {
        "code": code,
        "severity": severity,
        "evidence": evidence,
        "headline": headline,
        "why": why,
        "fix": fix,
    }
