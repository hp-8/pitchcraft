"""Variant direction catalog + audit-problem mapping for screen prompts.

Kept separate from screens.py to keep that file focused on prompt assembly
+ envelope IO.
"""
from __future__ import annotations

from typing import Literal

Page = Literal["landing", "services", "about", "contact"]

PAGES: tuple[Page, ...] = ("landing", "services", "about", "contact")

VARIANT_DIRECTIONS: dict[str, list[str]] = {
    "landing": [
        "hero-video-parallax",
        "split-screen-bold-typography",
        "scroll-driven-narrative",
    ],
    "services": [
        "bento-grid",
        "horizontal-scroll-cards",
        "kinetic-list",
    ],
    "about": [
        "editorial-magazine",
        "team-collage",
        "timeline-with-imagery",
    ],
    "contact": [
        "map-first-form-right",
        "fullscreen-form",
        "callout-cards-with-form",
    ],
}

_DIRECTION_PARAGRAPHS: dict[str, str] = {
    "hero-video-parallax": (
        "Full-bleed hero with an autoplaying muted background video. Headline sits "
        "over the video with parallax offset on scroll. Sticky transparent nav "
        "becomes solid after 100vh. Secondary CTA pinned bottom-right on mobile."
    ),
    "split-screen-bold-typography": (
        "50/50 vertical split. Left: oversized variable-weight display headline "
        "with kerning that snaps on scroll. Right: single product/lifestyle image "
        "that crossfades between 3 frames. Tight type, generous whitespace."
    ),
    "scroll-driven-narrative": (
        "Long single-column narrative hero. Each scroll tick reveals a new pinned "
        "moment (GSAP ScrollTrigger style). Background color shifts with each beat. "
        "Ends with the primary CTA pinned center."
    ),
    "bento-grid": (
        "Asymmetric bento layout: 6-9 tiles of varying sizes. Each tile is a "
        "service card with hover lift, image reveal, and short outcome copy. "
        "Featured tile spans 2x2 with bolder treatment."
    ),
    "horizontal-scroll-cards": (
        "Horizontal scroll section locked to viewport. 5-7 service cards slide in "
        "with snap-scroll. Progress indicator across the top. Vertical scroll "
        "resumes after the section."
    ),
    "kinetic-list": (
        "Vertical list of services as huge type rows. Each row hover reveals an "
        "inline thumbnail and short blurb. Smooth height transitions. Numbered "
        "(01, 02, 03...) with monospaced counters."
    ),
    "editorial-magazine": (
        "Magazine-style about page: pull quote, drop cap, two-column body in one "
        "section. Founder image flows around text. Sidebar with timeline ticks."
    ),
    "team-collage": (
        "Asymmetric photo collage of team members. Hover any portrait to expand "
        "bio inline. Subtle parallax on individual photos. Mission statement "
        "block sits above the collage."
    ),
    "timeline-with-imagery": (
        "Vertical scroll-triggered timeline. Each milestone has a year, short "
        "story, and a paired image that fades in from alternating sides. Sticky "
        "year ticker on the left."
    ),
    "map-first-form-right": (
        "Two-column layout: interactive map (or static map asset) fills the left "
        "60%, contact form sits on the right. Address, hours, and phone in a "
        "card pinned above the form."
    ),
    "fullscreen-form": (
        "Single centered conversational form. One question at a time, animated "
        "transitions between steps. Brand mark top-left, contact details "
        "(phone, address) in footer ribbon."
    ),
    "callout-cards-with-form": (
        "Three callout cards at the top (visit, call, book). Each card has an "
        "icon, one-line value prop, and a CTA. Contact form sits below in a "
        "constrained 640px column."
    ),
}

# Audit problem code -> (guidance line, pages where it applies).
_AUDIT_PROBLEM_NOTES: dict[str, tuple[str, tuple[Page, ...]]] = {
    "weak_cta": (
        "Place a primary CTA above the fold with a verb-first label.",
        ("landing", "services", "about", "contact"),
    ),
    "no_phone": (
        "Surface phone number in header and footer; tap-to-call on mobile.",
        ("landing", "contact", "about", "services"),
    ),
    "no_reservation": (
        "Add a reservation widget block to the hero or services area.",
        ("landing", "services"),
    ),
    "slow_lcp": (
        "Use a single optimized hero asset; lazy-load below-fold imagery.",
        ("landing",),
    ),
    "no_menu": (
        "Add a Menu CTA + section preview with featured items.",
        ("landing", "services"),
    ),
    "no_hours": (
        "Show hours of operation prominently with today's hours highlighted.",
        ("contact", "landing"),
    ),
    "no_address": (
        "Display the street address with a map link near the top.",
        ("contact", "landing"),
    ),
    "no_social_proof": (
        "Include testimonials or review pull-quotes with source attribution.",
        ("landing", "about"),
    ),
    "no_about": (
        "Add a short founder/story block with a portrait.",
        ("about", "landing"),
    ),
    "no_services": (
        "Enumerate core services with concrete outcomes, not jargon.",
        ("services", "landing"),
    ),
}


def direction_paragraph(direction: str) -> str:
    return _DIRECTION_PARAGRAPHS.get(
        direction,
        f"Layout direction: {direction}. Distinct visual treatment, mobile-first.",
    )


def audit_to_page_notes(problems: list[str] | None, page: Page) -> list[str]:
    """Map audit problem codes to page-relevant guidance lines."""
    if not problems:
        return []
    notes: list[str] = []
    for code in problems:
        entry = _AUDIT_PROBLEM_NOTES.get(code)
        if entry is None:
            continue
        note, pages = entry
        if page in pages:
            notes.append(note)
    return notes
