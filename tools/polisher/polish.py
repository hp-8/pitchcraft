"""Polisher orchestrator — Stitch HTML + design_brief.md → production HTML."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tools.polisher._animation_wire import CDN_LIBS, build_prototype_js, inject_cdn
from tools.polisher._autotag import autotag
from tools.polisher._brief_parser import parse_brief
from tools.polisher._honest_copy import scan as honest_scan
from tools.polisher._html import parse, render
from tools.polisher._mobile_fix import apply_mobile_fixes
from tools.polisher._models import PageReport, PolishResult
from tools.polisher._premium_css import build_css, inject_premium_css
from tools.polisher._slop_gates import check_gates

if TYPE_CHECKING:
    from tools.sheets.client import SheetsClient

logger = logging.getLogger(__name__)

_PAGE_ORDER = ("landing", "services", "about", "contact")
_PAGE_FILENAMES = {
    "landing": "index.html",
    "services": "services.html",
    "about": "about.html",
    "contact": "contact.html",
}
_VERCEL_JSON = {"cleanUrls": True, "trailingSlash": False}


def _load_approved(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    approved = data.get("approved") or {}
    return {str(k): int(v) for k, v in approved.items() if v is not None}


def _polish_page(page: str, source_path: Path, brief, out_path: Path) -> PageReport:
    raw = source_path.read_text(encoding="utf-8")
    soup = parse(raw)
    counts = autotag(soup)
    inject_premium_css(soup, brief)
    inject_cdn(soup)
    mobile_fixes = apply_mobile_fixes(soup)
    honesty = honest_scan(soup)
    gates = check_gates(soup)
    rendered = render(soup)
    out_path.write_text(rendered, encoding="utf-8")
    return PageReport(
        page=page,
        source_html=str(source_path),
        output_html=str(out_path),
        autotag_counts=counts,
        honesty_flags=honesty,
        slop_gate_failures=gates,
        mobile_fixes_applied=mobile_fixes,
    )


def polish_prototype(
    lead_id: str,
    lead_dir: str | Path,
    brief_path: str | Path,
    design_md_path: str | Path | None = None,
    approved_path: str | Path | None = None,
    out_dir: str | Path | None = None,
    sheets_client: "SheetsClient | None" = None,
) -> PolishResult:
    """Polish all 4 pages → production HTML in `<out_dir>` (default <lead_dir>/site)."""
    lead_dir_p = Path(lead_dir)
    out_dir_p = Path(out_dir) if out_dir else lead_dir_p / "site"
    approved_p = Path(approved_path) if approved_path else lead_dir_p / "approved.json"
    out_dir_p.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir_p / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    brief = parse_brief(brief_path)
    if design_md_path is not None:
        dp = Path(design_md_path)
        if dp.exists():
            brief.raw_palette = dp.read_text(encoding="utf-8")[:4000]

    approved = _load_approved(approved_p)
    errors: list[str] = []
    pages: list[PageReport] = []

    for page in _PAGE_ORDER:
        idx = approved.get(page, 0)
        candidates = [
            lead_dir_p / "stitch" / f"{page}-v{idx}.html",
            lead_dir_p / "stitch" / f"{page}-v0.html",
        ]
        src = next((c for c in candidates if c.exists()), None)
        if src is None:
            errors.append(f"missing source HTML for page={page}")
            continue
        target = out_dir_p / _PAGE_FILENAMES[page]
        try:
            report = _polish_page(page, src, brief, target)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{page}: {exc}")
            logger.exception("polish failed for %s", page)
            continue
        pages.append(report)

    # Shared assets
    (assets_dir / "prototype.js").write_text(build_prototype_js(brief), encoding="utf-8")
    (assets_dir / "prototype.css").write_text(build_css(brief), encoding="utf-8")
    (out_dir_p / "vercel.json").write_text(
        json.dumps(_VERCEL_JSON, indent=2) + "\n", encoding="utf-8"
    )

    libs_loaded = [name for name, _ in CDN_LIBS]

    result = PolishResult(
        lead_id=lead_id,
        site_dir=str(out_dir_p),
        pages=pages,
        libs_loaded=libs_loaded,
        theme_name=brief.theme,
        macrostructure=brief.macrostructure,
        errors=errors,
    )

    # Write polish_report.json
    (lead_dir_p / "polish_report.json").write_text(
        json.dumps(result.model_dump(), indent=2) + "\n", encoding="utf-8"
    )

    if sheets_client is not None:
        try:
            sheets_client.upsert_lead(lead_id, {"prototype_status": "polished"})
            honesty_count = sum(len(p.honesty_flags) for p in pages)
            gate_count = sum(len(p.slop_gate_failures) for p in pages)
            note = (
                f"[polish] {len(pages)} pages, {len(libs_loaded)} libs, "
                f"{honesty_count} honesty flags, {gate_count} slop gate failures"
            )
            sheets_client.update_status(lead_id, "prototype", "polished", note=note)
            for e in errors:
                sheets_client.append_error(lead_id, "polish", e)
        except Exception as exc:  # noqa: BLE001
            logger.warning("sheets update failed: %s", exc)
            errors.append(f"sheets update failed: {exc}")

    return result
