"""Audit orchestrator + typer CLI.

CLI:
    uv run python -m tools.audit --url https://example.com --vertical restaurant

Importable:
    from tools.audit.audit import audit
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer

from tools.audit._dollar_impact import estimate_dollar_impact
from tools.audit._firecrawl import fetch_firecrawl
from tools.audit._heuristics import run_heuristics
from tools.audit._models import AuditResult, PageSpeedSummary
from tools.audit._pagespeed import fetch_pagespeed
from tools.audit._slug import url_to_slug

VERTICALS = ("restaurant", "dental", "realtor", "fnb")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def audit(
    url: str,
    vertical: str,
    out_dir: str | Path = "data/outputs",
    strategy: str = "mobile",
) -> AuditResult:
    """Run a full audit and write audit.json + screenshot under out_dir/<slug>/."""
    if vertical not in VERTICALS:
        raise ValueError(f"vertical must be one of {VERTICALS}, got {vertical!r}")

    slug = url_to_slug(url)
    out_root = Path(out_dir) / slug
    out_root.mkdir(parents=True, exist_ok=True)
    screenshot_dest = out_root / "screenshot.png"

    fc = fetch_firecrawl(url, screenshot_dest=screenshot_dest)
    firecrawl_error = fc.get("error")
    markdown = fc.get("markdown", "") if not firecrawl_error else ""
    html = fc.get("html", "") if not firecrawl_error else ""
    screenshot_path = fc.get("screenshot_path") if not firecrawl_error else None

    ps_raw = fetch_pagespeed(url, strategy=strategy)
    pagespeed_error = ps_raw.get("error") if isinstance(ps_raw, dict) else None
    pagespeed_summary: PageSpeedSummary | None = None
    if not pagespeed_error:
        pagespeed_summary = PageSpeedSummary(
            performance_score=ps_raw.get("performance_score"),
            seo_score=ps_raw.get("seo_score"),
            accessibility_score=ps_raw.get("accessibility_score"),
            best_practices_score=ps_raw.get("best_practices_score"),
            lcp_ms=ps_raw.get("lcp_ms"),
            cls=ps_raw.get("cls"),
            inp_ms=ps_raw.get("inp_ms"),
            tbt_ms=ps_raw.get("tbt_ms"),
            opportunities=ps_raw.get("opportunities") or [],
        )

    problems = run_heuristics(markdown, html, vertical, url=url)
    dollar_impact = estimate_dollar_impact(problems, ps_raw, vertical)

    result = AuditResult(
        url=url,
        vertical=vertical,
        slug=slug,
        audited_at=_now_iso(),
        screenshot_path=screenshot_path,
        pagespeed=pagespeed_summary,
        problems=problems,
        dollar_impact=dollar_impact,
        firecrawl_error=firecrawl_error,
        pagespeed_error=pagespeed_error,
    )

    out_path = out_root / "audit.json"
    out_path.write_text(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    return result


app = typer.Typer(add_completion=False, help="Website audit engine.")


@app.command()
def main(
    url: str = typer.Option(..., "--url", help="Target site URL."),
    vertical: str = typer.Option(
        ...,
        "--vertical",
        help="Business vertical.",
        case_sensitive=False,
    ),
    out_dir: str = typer.Option(
        "data/outputs", "--out-dir", help="Output root directory."
    ),
    strategy: str = typer.Option(
        "mobile", "--strategy", help="PageSpeed strategy: mobile|desktop."
    ),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print stdout JSON."),
) -> None:
    """Run a full audit and emit AuditResult JSON to stdout."""
    if vertical not in VERTICALS:
        raise typer.BadParameter(f"--vertical must be one of {VERTICALS}")
    result = audit(url=url, vertical=vertical, out_dir=out_dir, strategy=strategy)
    indent = 2 if pretty else None
    typer.echo(json.dumps(result.model_dump(), indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    app()
