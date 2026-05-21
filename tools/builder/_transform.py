"""HTML transformation — inject animation hooks, rewrite nav, add SEO meta.

Pure string/regex operations to keep deps minimal. Idempotent: re-running
transform on already-transformed HTML produces the same output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from tools.builder._assets import CDN_HEAD_TAGS, INJECTION_MARKER

PAGE_ROUTES: dict[str, str] = {
    "landing": "/",
    "home": "/",
    "services": "/services",
    "menu": "/services",  # restaurants tend to call this menu
    "about": "/about",
    "contact": "/contact",
}

# Tokens we look for inside anchor text or hrefs to remap to local routes.
_NAV_TOKEN_RE = re.compile(
    r"\b(landing|home|services|menu|about|contact)\b",
    re.IGNORECASE,
)
_ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_HREF_RE = re.compile(r'href\s*=\s*"([^"]*)"', re.IGNORECASE)
_VIEWPORT_RE = re.compile(r'<meta\b[^>]*name\s*=\s*"viewport"', re.IGNORECASE)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_DESCRIPTION_RE = re.compile(r'<meta\b[^>]*name\s*=\s*"description"', re.IGNORECASE)
_HEAD_OPEN_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
_HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
_BODY_CLOSE_RE = re.compile(r"</body>", re.IGNORECASE)


@dataclass
class TransformContext:
    page: str  # landing | services | about | contact
    business: str
    vertical: str


def _route_for_token(token: str) -> str | None:
    return PAGE_ROUTES.get(token.lower())


def _rewrite_anchor(match: re.Match[str]) -> str:
    attrs = match.group(1)
    inner = match.group(2)
    text = re.sub(r"<[^>]+>", " ", inner).strip()
    # Prefer text match; fall back to existing href match.
    href_match = _HREF_RE.search(attrs)
    existing_href = href_match.group(1) if href_match else ""

    target_route: str | None = None
    token_match = _NAV_TOKEN_RE.search(text) if text else None
    if token_match is None and existing_href:
        token_match = _NAV_TOKEN_RE.search(existing_href)
    if token_match:
        target_route = _route_for_token(token_match.group(1))

    if not target_route:
        return match.group(0)

    # Skip external links (different host) entirely.
    if existing_href.startswith(("http://", "https://", "mailto:", "tel:")):
        return match.group(0)

    if href_match:
        new_attrs = _HREF_RE.sub(f'href="{target_route}"', attrs, count=1)
    else:
        new_attrs = attrs.rstrip() + f' href="{target_route}"'
    return f"<a{new_attrs}>{inner}</a>"


def rewrite_nav_links(html: str) -> str:
    """Best-effort: anchors whose visible text or href contains a nav token get
    their href rewritten to the local route. External links left alone.
    """
    return _ANCHOR_RE.sub(_rewrite_anchor, html)


def ensure_viewport(html: str) -> str:
    if _VIEWPORT_RE.search(html):
        return html
    tag = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    return _HEAD_OPEN_RE.sub(lambda m: m.group(0) + "\n" + tag, html, count=1)


def ensure_seo(html: str, ctx: TransformContext) -> str:
    page_label = ctx.page.capitalize()
    fallback_title = f"{ctx.business} — {page_label}"
    if _TITLE_RE.search(html):
        # Leave existing title (Stitch usually produces a good one).
        pass
    else:
        tag = f"<title>{fallback_title}</title>"
        html = _HEAD_OPEN_RE.sub(lambda m: m.group(0) + "\n" + tag, html, count=1)

    if not _DESCRIPTION_RE.search(html):
        desc = (
            f"{ctx.business} — {ctx.vertical} business. "
            f"{page_label} page."
        ).replace('"', "'")
        tag = f'<meta name="description" content="{desc}">'
        html = _HEAD_OPEN_RE.sub(lambda m: m.group(0) + "\n" + tag, html, count=1)
    return html


def inject_animation_primitives(html: str) -> str:
    """Inject CDN tags into <head>. Idempotent via INJECTION_MARKER sentinel."""
    if INJECTION_MARKER in html:
        return html
    if _HEAD_CLOSE_RE.search(html):
        return _HEAD_CLOSE_RE.sub(CDN_HEAD_TAGS + "</head>", html, count=1)
    # No </head>; append before </body> as a fallback.
    if _BODY_CLOSE_RE.search(html):
        return _BODY_CLOSE_RE.sub(CDN_HEAD_TAGS + "</body>", html, count=1)
    return html + CDN_HEAD_TAGS


def transform_html(html: str, ctx: TransformContext, rewrite_nav: bool = True) -> str:
    """Apply all transforms in order. Idempotent end-to-end."""
    out = html
    out = ensure_viewport(out)
    out = ensure_seo(out, ctx)
    if rewrite_nav:
        out = rewrite_nav_links(out)
    out = inject_animation_primitives(out)
    return out
