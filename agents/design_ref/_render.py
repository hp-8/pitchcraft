"""Render DESIGN.md from a DesignSpec. Pure templating — no I/O."""
from __future__ import annotations

from collections import defaultdict
from typing import List

from ._models import DesignSpec, MoodboardItem

MOTION_REQUIREMENTS = [
    "Smooth scroll: Lenis",
    "Hero kinetic typography (Splitting.js or Framer staggered words)",
    "Scroll reveals on every section (Framer whileInView or GSAP ScrollTrigger)",
    "Page transitions (Framer AnimatePresence)",
    "Hover micro-interactions (magnetic buttons, image hover effects)",
    "At least 1 marquee",
    "Image lazy reveal (mask-clip or blur-up)",
    "Intro loader",
]


def _grouped_refs(items: List[MoodboardItem]) -> str:
    groups: dict[str, list[MoodboardItem]] = defaultdict(list)
    for item in items:
        groups[item.source].append(item)
    lines: list[str] = []
    for source in sorted(groups):
        lines.append(f"### {source}")
        for it in groups[source]:
            title = it.title or "(untitled)"
            lines.append(f"- {title} — {it.source} — {it.url}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _motion_refs(items: List[MoodboardItem]) -> str:
    if not items:
        return "_No motion-rich refs flagged in this moodboard._"
    lines = []
    for it in items:
        libs = ", ".join(it.libs_detected) if it.libs_detected else "(no libs detected)"
        lines.append(f"- {it.url} — libs: {libs}")
    return "\n".join(lines)


def render_design_md(spec: DesignSpec) -> str:
    p = spec.palette
    patterns = spec.component_patterns or [
        "Full-bleed hero with oversized display type",
        "Sticky translucent nav",
        "3-up service card grid",
        "Testimonial marquee",
        "CTA band before footer",
        "Multi-column footer with social + hours",
    ]
    patterns_md = "\n".join(f"- {pat}" for pat in patterns)
    motion_required_md = "\n".join(f"- {m}" for m in MOTION_REQUIREMENTS)

    return f"""# Design System: {spec.vertical.title()} — {spec.style.title()}

## Brand mood
{spec.brand_mood}

## Color palette
- Primary: {p.primary}
- Accent: {p.accent}
- Neutral 0: {p.neutral_0}
- Neutral 50: {p.neutral_50}
- Neutral 100: {p.neutral_100}
- Neutral 500: {p.neutral_500}
- Neutral 900: {p.neutral_900}
- Background: {p.background}
- Surface: {p.surface}

## Typography
- Display: {spec.typography.display}
- Body: {spec.typography.body}
- Mono: {spec.typography.mono or "n/a"}

## Spacing & radius
- Base unit: {spec.spacing_base}
- Radius scale: {spec.radius_scale}

## Component patterns
{patterns_md}

## Motion section (NON-NEGOTIABLE — see PLAN.md Design Quality Bar)
Required animations for every page built from this system:
{motion_required_md}

Reference motion examples (from moodboard items where `has_animation == true`):
{_motion_refs(spec.motion_references)}

## Image direction
{spec.image_direction}

## Inspirational references
{_grouped_refs(spec.all_references) or "_No references supplied._"}
"""
