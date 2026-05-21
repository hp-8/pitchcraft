"""Hallmark picker — deterministic macrostructure/theme/nav/footer diversifier.

Reads `.hallmark/log.json` for past picks and enforces diversification rules.
After picking, appends a new entry (trimmed to last 20).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 21 macrostructures (Hallmark canonical, references/macrostructures.md).
MACROSTRUCTURES: list[str] = [
    "Bento Grid",
    "Long Document",
    "Marquee Hero",
    "Stat-Led",
    "Workbench",
    "Conversational FAQ",
    "Manifesto",
    "Photographic",
    "Quote-Led",
    "Specimen",
    "Catalogue",
    "Letter",
    "Index-First",
    "Narrative Workflow",
    "Split Studio",
    "Feature Stack",
    "Type Specimen",
    "Portfolio Grid",
    "Map / Diagram",
    "Ecosystem Index",
    "Component Playground",
]

# 22 themes with three diversification axes.
# paper_band: light | warm | dark
# display_style: italic-serif | serif | mono | sans | display-serif | slab | grotesk
# accent_hue: warm | cool | red | green | indigo | coral | violet | aurora | none
THEMES: dict[str, dict[str, str]] = {
    "Specimen":   {"paper_band": "light", "display_style": "italic-serif", "accent_hue": "warm"},
    "Atelier":    {"paper_band": "warm",  "display_style": "serif",        "accent_hue": "warm"},
    "Brutal":     {"paper_band": "light", "display_style": "grotesk",      "accent_hue": "red"},
    "Salon":      {"paper_band": "warm",  "display_style": "display-serif","accent_hue": "warm"},
    "Newsprint":  {"paper_band": "light", "display_style": "serif",        "accent_hue": "none"},
    "Linen":      {"paper_band": "warm",  "display_style": "serif",        "accent_hue": "warm"},
    "Studio":     {"paper_band": "light", "display_style": "grotesk",      "accent_hue": "cool"},
    "Manifesto":  {"paper_band": "light", "display_style": "slab",         "accent_hue": "red"},
    "Terminal":   {"paper_band": "dark",  "display_style": "mono",         "accent_hue": "green"},
    "Midnight":   {"paper_band": "dark",  "display_style": "serif",        "accent_hue": "indigo"},
    "Almanac":    {"paper_band": "warm",  "display_style": "serif",        "accent_hue": "warm"},
    "Garden":     {"paper_band": "warm",  "display_style": "italic-serif", "accent_hue": "green"},
    "Quiet":      {"paper_band": "light", "display_style": "sans",         "accent_hue": "none"},
    "Riso":       {"paper_band": "warm",  "display_style": "grotesk",      "accent_hue": "coral"},
    "Sport":      {"paper_band": "light", "display_style": "grotesk",      "accent_hue": "red"},
    "Bloom":      {"paper_band": "dark",  "display_style": "display-serif","accent_hue": "violet"},
    "Coral":      {"paper_band": "warm",  "display_style": "sans",         "accent_hue": "coral"},
    "Violet":     {"paper_band": "light", "display_style": "serif",        "accent_hue": "violet"},
    "Aurora":     {"paper_band": "dark",  "display_style": "sans",         "accent_hue": "aurora"},
    "Halo":       {"paper_band": "light", "display_style": "display-serif","accent_hue": "cool"},
    "Plume":      {"paper_band": "warm",  "display_style": "sans",         "accent_hue": "indigo"},
    "Editorial":  {"paper_band": "warm",  "display_style": "italic-serif", "accent_hue": "warm"},
}

# Per-genre theme rotations (matches Hallmark genre files).
GENRE_THEMES: dict[str, list[str]] = {
    "atmospheric":   ["Bloom", "Midnight", "Terminal"],
    "modern-minimal":["Quiet"],
    "playful":       ["Plume"],
    "editorial":     ["Specimen", "Atelier", "Brutal", "Salon", "Newsprint", "Linen",
                      "Studio", "Manifesto", "Almanac", "Garden", "Riso", "Sport",
                      "Coral", "Violet", "Aurora", "Halo", "Editorial"],
}

# Nav archetypes (N1..N10) from component-cookbook.
NAVS: list[tuple[str, str]] = [
    ("N1",  "Wordmark + 2 links"),
    ("N2",  "Wordmark + tabbed links"),
    ("N3",  "Side-rail numbered"),
    ("N4",  "Editorial masthead"),
    ("N5",  "Floating pill"),
    ("N6",  "Newspaper masthead"),
    ("N7",  "Brutal slab"),
    ("N8",  "Minimal cluster"),
    ("N9",  "Underline drawer"),
    ("N10", "Centered serif"),
]

# Footer archetypes (Ft1..Ft8).
FOOTERS: list[tuple[str, str]] = [
    ("Ft1", "Tabular index"),
    ("Ft2", "Compact links"),
    ("Ft3", "Index columns"),
    ("Ft4", "Quiet brand line"),
    ("Ft5", "Statement"),
    ("Ft6", "Letter close"),
    ("Ft7", "Logo wall"),
    ("Ft8", "Marquee scroll"),
]


def infer_genre(tone: str | None, vertical: str | None = None) -> str:
    """Map a brand-voice tone (Hallmark vocab) to a genre."""
    t = (tone or "").strip().lower()
    if t in {"editorial", "luxury", "austere", "brutalist"}:
        return "editorial"
    if t in {"utilitarian", "technical"}:
        return "modern-minimal"
    if t in {"playful", "soft"}:
        # soft is editorial-leaning; but `playful` token shortest path is playful.
        return "playful" if t == "playful" else "editorial"
    # vertical fallback
    if vertical in {"dental"}:
        return "modern-minimal"
    return "editorial"


def _load_log(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    try:
        data = json.loads(log_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("could not parse %s: %s", log_path, exc)
    return []


def _save_log(log_path: Path, entries: list[dict[str, Any]]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(entries[-20:], indent=2), encoding="utf-8")


def _theme_differs(candidate: str, prev: str | None) -> bool:
    if prev is None or prev not in THEMES or candidate not in THEMES:
        return True
    c = THEMES[candidate]
    p = THEMES[prev]
    diffs = sum(1 for k in ("paper_band", "display_style", "accent_hue") if c[k] != p[k])
    return diffs >= 1


def pick_macrostructure_and_theme(
    genre: str,
    log_path: str | Path = ".hallmark/log.json",
    append: bool = True,
) -> dict[str, Any]:
    """Deterministically pick macrostructure + theme + nav + footer.

    Rules:
    - Macrostructure must differ from last 3 entries in log.
    - Theme must differ from last theme on >=1 axis and stay within genre.
    - Nav and footer must differ from last entry.
    """
    log_p = Path(log_path)
    entries = _load_log(log_p)
    recent_macros = [e.get("macrostructure") for e in entries[-3:]]
    last = entries[-1] if entries else None
    last_theme = (last or {}).get("theme")
    last_nav = (last or {}).get("nav")
    last_footer = (last or {}).get("footer")

    if genre not in GENRE_THEMES:
        genre = "editorial"

    # Macrostructure: first one not in last 3.
    macro = next((m for m in MACROSTRUCTURES if m not in recent_macros), MACROSTRUCTURES[0])

    # Theme: walk genre rotation, prefer one that differs on >=1 axis from last_theme
    # and is not equal to last_theme.
    genre_pool = GENRE_THEMES[genre]
    # rotate pool by len(entries) for variety, then filter.
    offset = len(entries) % len(genre_pool)
    rotated = genre_pool[offset:] + genre_pool[:offset]
    theme = next(
        (t for t in rotated if t != last_theme and _theme_differs(t, last_theme)),
        rotated[0],
    )

    # Nav: deterministic walk by genre + entry count, must differ from last_nav.
    nav_offset = len(entries) % len(NAVS)
    nav = next(((c, n) for c, n in (NAVS[nav_offset:] + NAVS[:nav_offset]) if c != last_nav), NAVS[0])
    foot_offset = len(entries) % len(FOOTERS)
    foot = next(((c, n) for c, n in (FOOTERS[foot_offset:] + FOOTERS[:foot_offset]) if c != last_footer), FOOTERS[0])

    axes = THEMES.get(theme, {"paper_band": "?", "display_style": "?", "accent_hue": "?"})
    rotation_note = (
        f"Recent macrostructures: {recent_macros or 'none'}. "
        f"Previous theme: {last_theme or 'none'}. "
        f"Pool: {genre_pool}."
    )

    result = {
        "macrostructure": macro,
        "theme": theme,
        "nav": f"{nav[0]} {nav[1]}",
        "footer": f"{foot[0]} {foot[1]}",
        "genre": genre,
        "axes": axes,
        "rotation_note": rotation_note,
    }

    if append:
        entries.append({
            "macrostructure": macro,
            "theme": theme,
            "nav": nav[0],
            "footer": foot[0],
            "genre": genre,
        })
        _save_log(log_p, entries)

    return result
