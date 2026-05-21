"""Moderator — renders design_brief.md from agent outputs."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools.stitch._models import LeadContext

_PAGES = ("landing", "services", "about", "contact")


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body.strip()}\n"


def _bullets(items: list[str], empty: str = "(none)") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {it}" for it in items)


def _quote_design_md(design_md_path: Path | None) -> str:
    if design_md_path is None or not design_md_path.exists():
        return "(no Phase 3 DESIGN.md supplied — palette/typography to be inherited from theme defaults)"
    text = design_md_path.read_text(encoding="utf-8")
    chunks: list[str] = []
    for header in ("Palette", "Typography", "Motion"):
        m = re.search(rf"^##\s+{header}\b.*?(?=^##\s+|\Z)", text, re.MULTILINE | re.DOTALL)
        if m:
            block = m.group(0).strip()
            if len(block) > 1200:
                block = block[:1200] + "\n…(truncated)"
            chunks.append(block)
    if not chunks:
        return f"(See `{design_md_path}` — sections Palette/Typography/Motion not found by heading match.)"
    return "\n\n".join(chunks) + f"\n\n_Source: `{design_md_path}`_"


def _refs_table(refs: list[dict[str, Any]]) -> str:
    if not refs:
        return "_(no references — moodboard empty or not supplied)_"
    lines = ["| # | Title | Source | URL |", "|---|-------|--------|-----|"]
    for i, r in enumerate(refs, 1):
        title = (r.get("title") or "(untitled)").replace("|", "/")
        src = (r.get("source") or "?").replace("|", "/")
        url = (r.get("url") or "").replace("|", "/")
        lines.append(f"| {i} | {title} | {src} | {url} |")
    return "\n".join(lines)


def _motion_table(per_page: dict[str, list[str]]) -> str:
    lines = ["| Page | Primitives |", "|------|------------|"]
    for page in _PAGES:
        prims = per_page.get(page, [])
        lines.append(f"| {page} | {', '.join(prims) or '(none)'} |")
    return "\n".join(lines)


def fuse(
    agent_outputs: dict[str, dict[str, Any]],
    lead: LeadContext,
    out_dir: Path,
    design_md_path: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Render `design_brief.md` from agent outputs. Returns (path, summary_dict)."""
    bv = agent_outputs.get("brand_voice", {})
    insp = agent_outputs.get("inspiration", {})
    hp = agent_outputs.get("hallmark_picker", {})
    ux = agent_outputs.get("audit_ux", {})
    motion = agent_outputs.get("animation", {})

    lead_dir = Path(out_dir) / lead.lead_id
    lead_dir.mkdir(parents=True, exist_ok=True)
    brief_path = lead_dir / "design_brief.md"

    axes = hp.get("axes", {})
    per_page_req: dict[str, list[str]] = ux.get("per_page_requirements", {})
    per_page_motion: dict[str, list[str]] = motion.get("per_page", {})

    parts: list[str] = [f"# Design Brief: {lead.business}\n"]
    parts.append(_section("Pre-flight context", "\n".join([
        f"- Lead ID: {lead.lead_id}",
        f"- Vertical: {lead.vertical}",
        f"- Location: {lead.location or '(unspecified)'}",
        f"- Services: {', '.join(lead.services) or '(unspecified)'}",
        f"- Phone: {lead.phone or '(unspecified)'}",
        f"- Booking provider: {lead.booking_provider or '(unspecified)'}",
    ])))

    parts.append(_section("Audience", bv.get("audience", "(unspecified)")))
    parts.append(_section("Use case", bv.get("use_case", "(unspecified)")))
    parts.append(_section(
        "Tone",
        f"**{bv.get('tone', 'editorial')}** — "
        f"voice attributes: {', '.join(bv.get('voice_attributes') or []) or '(none)'}.\n\n"
        f"One-liner: _{bv.get('one_liner', '')}_"
    ))

    parts.append(_section("Genre", hp.get("genre", "editorial")))

    parts.append(_section(
        "Macrostructure",
        f"**{hp.get('macrostructure', '(unspecified)')}** — page shape inherited from Hallmark catalogue. "
        "Refer to the matching `references/macrostructures/<slug>.md` for hero composition rules."
    ))

    parts.append(_section("Theme", "\n".join([
        f"- Name: **{hp.get('theme', '(unspecified)')}**",
        f"- Paper band: {axes.get('paper_band', '?')}",
        f"- Display style: {axes.get('display_style', '?')}",
        f"- Accent hue: {axes.get('accent_hue', '?')}",
        f"- Rotation note: {hp.get('rotation_note', '(none)')}",
    ])))

    parts.append(_section("Nav archetype", hp.get("nav", "(unspecified)")))
    parts.append(_section("Footer archetype", hp.get("footer", "(unspecified)")))

    must = ux.get("must_have_sections", [])
    parts.append(_section("Must-have sections (drawn from audit + vertical minimums)", _bullets(must)))

    page_sections: list[str] = []
    for page in _PAGES:
        reqs = per_page_req.get(page, [])
        page_sections.append(f"### {page.capitalize()}\n{_bullets(reqs, empty='(no audit-driven requirements)')}")
    parts.append(_section("Page-specific requirements", "\n\n".join(page_sections)))

    motion_body = (
        f"{_motion_table(per_page_motion)}\n\n"
        f"- Libraries to load: {', '.join(motion.get('libs_required') or []) or '(none)'}\n"
        f"- `prefers-reduced-motion`: {motion.get('reduced_motion_note', 'collapse to opacity crossfade <=150ms')}\n"
    )
    parts.append(_section("Motion plan", motion_body))

    parts.append(_section(
        "Inspirational references (top 12)",
        f"By source: {insp.get('by_source', {})}\n\n"
        f"Motion-lib distribution: {insp.get('motion_lib_distribution', {})}\n\n"
        f"{_refs_table(insp.get('top_refs', []))}"
    ))

    parts.append(_section("Phase 3 DESIGN.md handoff (palette / typography / motion)",
                          _quote_design_md(design_md_path)))

    parts.append(_section("Honesty constraints", _bullets([
        "No fabricated metrics (count, percentage, dollar figure)",
        '"Trusted by N+ teams" / "N happy customers" banned unless supplied by lead',
        "Testimonials and stats placeholdered if not supplied — never invented",
        "No 'Jane Doe' / 'John Smith' placeholder names",
    ])))

    parts.append(_section("Hallmark slop-test gates to enforce post-build", _bullets([
        "Mobile-correct at 320 / 375 / 414 / 768 px (gate: responsive)",
        "Locked design tokens (no inline OKLCH literals in markup)",
        "No re-drawn UI chrome (no fake browser bars, fake macOS windows)",
        "No invented metrics (gate: honesty)",
        "2+1 font discipline (display + body, optional mono)",
        "No glassmorphism, no gradient text",
        "Respect prefers-reduced-motion",
    ])))

    audit_narr = ux.get("narrative")
    if audit_narr:
        parts.append(_section("Audit narrative", audit_narr))

    warnings = []
    for name, out in agent_outputs.items():
        for w in out.get("warnings", []) if isinstance(out, dict) else []:
            warnings.append(f"[{name}] {w}")
    if warnings:
        parts.append(_section("Warnings", _bullets(warnings)))

    brief_path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")

    summary = {
        "macrostructure": hp.get("macrostructure"),
        "theme": hp.get("theme"),
        "nav": hp.get("nav"),
        "footer": hp.get("footer"),
        "genre": hp.get("genre"),
        "must_have_sections": must,
        "motion_per_page": per_page_motion,
        "warnings": warnings,
    }
    return brief_path, summary
