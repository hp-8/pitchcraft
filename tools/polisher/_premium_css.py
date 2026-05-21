"""Theme-aware premium CSS layer injected into <head>."""
from __future__ import annotations

from bs4 import BeautifulSoup

from tools.polisher._html import ensure_head
from tools.polisher._models import BriefSummary

# OKLCH palettes by paper_band + accent_hue. All values inside oklch() are
# perceptually-uniform lightness/chroma/hue. Kept conservative.
_PALETTES: dict[tuple[str, str], dict[str, str]] = {
    ("light", "warm"): {
        "bg": "oklch(0.985 0.005 80)",
        "fg": "oklch(0.18 0.02 60)",
        "muted": "oklch(0.55 0.02 70)",
        "accent": "oklch(0.62 0.18 45)",
        "focus": "oklch(0.50 0.22 50)",
    },
    ("light", "cool"): {
        "bg": "oklch(0.985 0.005 230)",
        "fg": "oklch(0.20 0.03 240)",
        "muted": "oklch(0.55 0.02 230)",
        "accent": "oklch(0.55 0.18 240)",
        "focus": "oklch(0.50 0.22 240)",
    },
    ("dark", "warm"): {
        "bg": "oklch(0.16 0.01 60)",
        "fg": "oklch(0.96 0.01 70)",
        "muted": "oklch(0.72 0.02 70)",
        "accent": "oklch(0.74 0.18 50)",
        "focus": "oklch(0.78 0.20 55)",
    },
    ("dark", "cool"): {
        "bg": "oklch(0.16 0.02 240)",
        "fg": "oklch(0.96 0.01 230)",
        "muted": "oklch(0.72 0.02 230)",
        "accent": "oklch(0.74 0.18 240)",
        "focus": "oklch(0.78 0.20 240)",
    },
}

_FONT_BY_DISPLAY = {
    "italic-serif": (
        '"Fraunces", "Playfair Display", Georgia, serif',
        '"Inter", system-ui, sans-serif',
    ),
    "modern-sans": (
        '"Inter Tight", "Inter", system-ui, sans-serif',
        '"Inter", system-ui, sans-serif',
    ),
    "geometric": (
        '"Space Grotesk", "Inter", system-ui, sans-serif',
        '"Inter", system-ui, sans-serif',
    ),
    "stencil": (
        '"Bebas Neue", "Inter Tight", system-ui, sans-serif',
        '"Inter", system-ui, sans-serif',
    ),
}

_GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900"
    "&family=Inter:wght@300..800"
    "&family=Inter+Tight:wght@400..800"
    "&family=Space+Grotesk:wght@300..700"
    "&display=swap"
)


def _resolve_palette(brief: BriefSummary) -> dict[str, str]:
    key = (brief.paper_band, brief.accent_hue)
    return _PALETTES.get(key) or _PALETTES[("light", "warm")]


def _resolve_fonts(brief: BriefSummary) -> tuple[str, str]:
    return _FONT_BY_DISPLAY.get(brief.display_style) or _FONT_BY_DISPLAY["modern-sans"]


def build_css(brief: BriefSummary) -> str:
    palette = _resolve_palette(brief)
    display_font, body_font = _resolve_fonts(brief)
    mesh_block = ""
    if brief.gradient_mesh:
        mesh_block = (
            ".has-mesh {\n"
            "  background-image:\n"
            f"    radial-gradient(at 20% 10%, {palette['accent']} 0px, transparent 50%),\n"
            f"    radial-gradient(at 80% 40%, {palette['focus']} 0px, transparent 55%);\n"
            "  background-attachment: fixed;\n"
            "}\n"
        )
    return (
        "/* polisher: premium theme layer */\n"
        ":root {\n"
        f"  --color-bg: {palette['bg']};\n"
        f"  --color-fg: {palette['fg']};\n"
        f"  --color-muted: {palette['muted']};\n"
        f"  --color-accent: {palette['accent']};\n"
        f"  --color-focus: {palette['focus']};\n"
        f"  --font-display: {display_font};\n"
        f"  --font-body: {body_font};\n"
        "  --font-mono: ui-monospace, 'JetBrains Mono', Menlo, monospace;\n"
        "}\n"
        "html, body { overflow-x: clip; min-width: 0; }\n"
        "body { background: var(--color-bg); color: var(--color-fg); "
        "font-family: var(--font-body); }\n"
        "h1, h2, h3 { font-family: var(--font-display); overflow-wrap: anywhere; "
        "min-width: 0; }\n"
        "a, button { transition: transform .2s ease, opacity .2s ease, color .2s ease; }\n"
        ":focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }\n"
        "html.is-loading body { opacity: 0; transform: translateY(8px); }\n"
        "body { opacity: 1; transform: none; transition: opacity .4s ease, transform .4s ease; }\n"
        "@keyframes marquee { from { transform: translateX(0); } "
        "to { transform: translateX(-50%); } }\n"
        "@keyframes image-reveal { from { clip-path: inset(0 0 100% 0); } "
        "to { clip-path: inset(0 0 0 0); } }\n"
        "[data-magnetic] { display: inline-block; will-change: transform; }\n"
        "[data-reveal] { will-change: transform, opacity; }\n"
        "[data-marquee] { display: flex; gap: 2rem; overflow: hidden; }\n"
        f"{mesh_block}"
        "@media (prefers-reduced-motion: reduce) {\n"
        "  *, *::before, *::after { animation-duration: 150ms !important; "
        "transition-duration: 150ms !important; }\n"
        "  [data-reveal], [data-parallax] { transform: none !important; }\n"
        "}\n"
    )


def inject_premium_css(soup: BeautifulSoup, brief: BriefSummary) -> None:
    head = ensure_head(soup)
    # Google fonts preconnect + stylesheet (idempotent: skip if marker present)
    if not soup.find("link", attrs={"data-polisher-fonts": "1"}):
        pre1 = soup.new_tag("link", rel="preconnect", href="https://fonts.googleapis.com")
        pre2 = soup.new_tag(
            "link", rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""
        )
        link = soup.new_tag("link", rel="stylesheet", href=_GOOGLE_FONTS)
        link["data-polisher-fonts"] = "1"
        head.append(pre1)
        head.append(pre2)
        head.append(link)
    # Style block
    if not soup.find("style", attrs={"data-polisher-css": "1"}):
        style = soup.new_tag("style")
        style["data-polisher-css"] = "1"
        style.string = build_css(brief)
        head.append(style)
    # Mesh body class
    if brief.gradient_mesh:
        body = soup.find("body")
        if body is not None:
            cls = body.get("class") or []
            if isinstance(cls, str):
                cls = cls.split()
            if "has-mesh" not in cls:
                cls.append("has-mesh")
                body["class"] = cls
