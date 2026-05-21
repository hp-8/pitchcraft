"""Parse design_brief.md (council moderator output) into BriefSummary."""
from __future__ import annotations

import re
from pathlib import Path

from tools.polisher._models import BriefSummary

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _split_sections(text: str) -> dict[str, str]:
    """Returns {section_title: body}."""
    out: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[title] = text[start:end].strip()
    return out


def _bullet_lines(body: str) -> list[str]:
    out: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ")):
            out.append(line[2:].strip())
    return out


def _kv_in_bullets(body: str) -> dict[str, str]:
    """Extract `- Key: value` pairs (case-insensitive keys)."""
    out: dict[str, str] = {}
    for item in _bullet_lines(body):
        if ":" in item:
            k, _, v = item.partition(":")
            k = k.strip().strip("*").lower()
            v = v.strip().strip("*")
            out[k] = v
    return out


def _extract_business(text: str) -> str:
    m = re.search(r"^#\s+Design Brief:\s*(.+?)\s*$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _parse_motion_table(body: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---") or "Page" in line[:8]:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        page = cells[0].lower()
        if page not in ("landing", "services", "about", "contact"):
            continue
        prims_raw = cells[1]
        prims = [p.strip() for p in prims_raw.split(",") if p.strip() and p.strip() != "(none)"]
        out[page] = prims
    return out


def parse_brief(brief_path: str | Path) -> BriefSummary:
    """Parse the brief; tolerate missing sections."""
    path = Path(brief_path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    summary = BriefSummary()
    if not text:
        return summary

    summary.business = _extract_business(text)
    sections = _split_sections(text)

    # Pre-flight context
    pre = sections.get("Pre-flight context", "")
    kv = _kv_in_bullets(pre)
    summary.vertical = (kv.get("vertical") or "").lower()

    summary.genre = (sections.get("Genre", "editorial").strip().splitlines() or ["editorial"])[0]
    summary.genre = summary.genre.strip() or "editorial"

    macro = sections.get("Macrostructure", "")
    m = re.search(r"\*\*(.+?)\*\*", macro)
    summary.macrostructure = m.group(1).strip() if m else ""

    theme = sections.get("Theme", "")
    tkv = _kv_in_bullets(theme)
    name_raw = tkv.get("name", "")
    nm = re.search(r"\*\*(.+?)\*\*", name_raw)
    summary.theme = (nm.group(1).strip() if nm else name_raw).strip("* ")
    summary.paper_band = (tkv.get("paper band") or "light").lower()
    summary.display_style = (tkv.get("display style") or "modern-sans").lower()
    summary.accent_hue = (tkv.get("accent hue") or "warm").lower()

    summary.nav = sections.get("Nav archetype", "").strip().splitlines()[:1][0] if sections.get(
        "Nav archetype"
    ) else ""
    summary.footer = sections.get("Footer archetype", "").strip().splitlines()[:1][0] if sections.get(
        "Footer archetype"
    ) else ""

    must = sections.get("Must-have sections (drawn from audit + vertical minimums)", "")
    summary.must_have_sections = _bullet_lines(must)

    motion = sections.get("Motion plan", "")
    summary.per_page_motion = _parse_motion_table(motion)
    libs_match = re.search(r"Libraries to load:\s*(.+)", motion)
    if libs_match:
        libs_raw = libs_match.group(1).strip()
        summary.libs_required = [
            lib.strip() for lib in libs_raw.split(",") if lib.strip() and lib.strip() != "(none)"
        ]

    summary.honesty_rules = _bullet_lines(sections.get("Honesty constraints", ""))

    # Page transitions: enabled if any page lists `page_transition`
    summary.page_transitions = any(
        "page_transition" in prims for prims in summary.per_page_motion.values()
    )
    # Gradient mesh: enabled if "depth" primitive present
    summary.gradient_mesh = any(
        "depth" in prims for prims in summary.per_page_motion.values()
    )

    summary.raw_palette = sections.get("Phase 3 DESIGN.md handoff (palette / typography / motion)")
    summary.raw_typography = summary.raw_palette  # same block

    return summary
