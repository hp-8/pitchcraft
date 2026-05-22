"""Proposal PDF: 1 page, plain-English problems → $ loss → demo → cost → CTA."""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.pdf._brand import BASE_CSS, render_brand_strip
from tools.pdf._humanize import humanize_problem
from tools.pdf.renderer import render_pdf

DEFAULT_PRICE = "$2,400"
DEFAULT_TIMELINE = (
    ("WEEK 1", "Discovery, full audit walkthrough, conversion gap mapping."),
    ("WEEK 1 to 2", "Homepage + key pages restructured, B2B/B2C journeys split, copy rewritten."),
    ("WEEK 2 to 3", "SEO + analytics + schema, sold-out + cart flow fixes, mobile polish."),
    ("WEEK 4", "QA, soft launch, post-launch monitoring + tuning."),
)
DEFAULT_SOCIALS = [
    ("Portfolio", "harshpatadia.space"),
    ("LinkedIn", "linkedin.com/in/harsh-patadia"),
    ("GitHub", "github.com/hp-8"),
    ("Substack", "substack.com/@damnyouharsh"),
]
DEFAULT_BOOK_CALL_URL = "https://calendar.app.google/hqKrMkn66PddNMaS8"


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%B %Y")


def _top_problems(audit: dict[str, Any], n: int = 4) -> list[dict[str, str]]:
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    problems = audit.get("problems") or []
    sorted_p = sorted(problems, key=lambda p: sev_rank.get(p.get("severity", "low"), 99))
    return [humanize_problem(p) for p in sorted_p[:n]]


def build_proposal_html(
    lead: dict[str, Any],
    audit: dict[str, Any],
    preview_url: str | None = None,
    book_call_url: str = DEFAULT_BOOK_CALL_URL,
    price: str = DEFAULT_PRICE,
    timeline: list[tuple[str, str]] | None = None,
    socials: list[tuple[str, str]] | None = None,
) -> str:
    business = lead.get("business") or "your business"
    audit_date = _utc_today()
    impact = audit.get("dollar_impact") or {}
    low = int(impact.get("monthly_loss_low") or 0)
    high = int(impact.get("monthly_loss_high") or 0)
    problems = _top_problems(audit, n=4)

    timeline = timeline or list(DEFAULT_TIMELINE)
    socials = socials or DEFAULT_SOCIALS

    problems_html = ""
    for p in problems:
        problems_html += (
            f'<li><strong>{_html.escape(p["headline"])}</strong> '
            f'<span class="muted">. {_html.escape(p["why"])}</span></li>'
        )

    timeline_html = ""
    for week, what in timeline:
        timeline_html += (
            f'<div class="timeline-row"><div class="week">{_html.escape(week)}</div>'
            f'<div>{_html.escape(what)}</div></div>'
        )

    socials_html = " · ".join(
        f'<span class="muted">{_html.escape(label)}</span> '
        f'<span class="tabular">{_html.escape(url)}</span>'
        for label, url in socials
    )

    preview_block = ""
    if preview_url:
        preview_block = (
            f'<div style="margin: 10pt 0 14pt;">'
            f'<div class="eyebrow" style="margin-bottom:6pt;">LIVE PROTOTYPE</div>'
            f'<div class="url-block">{_html.escape(preview_url)}</div>'
            f'</div>'
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Proposal, {_html.escape(business)}</title>
<style>{BASE_CSS}</style>
</head>
<body>
<div style="padding: 8mm 0;">
  {render_brand_strip(business, audit_date, "WEBSITE GROWTH PROPOSAL")}

  <div class="eyebrow">The Problem</div>
  <h2 style="margin-top: 4pt;">A few things on {_html.escape(business)}.com<br/>are costing revenue every month.</h2>
  <hr class="hr-brass"/>

  <ul class="tight">
    {problems_html}
  </ul>

  <div class="callout">
    <div class="eyebrow">ESTIMATED MONTHLY LEAKAGE</div>
    <div class="callout-amount tabular">${low:,} to ${high:,}</div>
    <div class="muted" style="color: rgba(250,247,242,0.75); font-size: 9pt;">
      Audit driven range. Full calculation in the companion audit PDF.
    </div>
  </div>

  {preview_block}

  <div class="grid-2" style="gap: 18pt;">
    <div>
      <div class="eyebrow">TIMELINE</div>
      <div style="margin-top: 6pt;">{timeline_html}</div>
    </div>
    <div>
      <div class="eyebrow">FIXED PROJECT FEE</div>
      <div class="callout-amount oxblood tabular" style="font-size: 28pt;">{_html.escape(price)}</div>
      <div class="muted" style="font-size: 9pt;">Includes audit, restructure, SEO + analytics setup, polish, deployment.</div>

      <div class="eyebrow" style="margin-top: 12pt;">WHY ME</div>
      <ul class="tight">
        <li>Full-stack engineer building conversion-focused systems</li>
        <li>SaaS platforms · AI automation · modern web infra</li>
        <li>Analytics + growth optimization, not just a redesign</li>
      </ul>
    </div>
  </div>

  <div style="margin-top: 16pt; display:flex; align-items:center; justify-content:space-between; gap: 12pt;">
    <div>
      <div class="eyebrow">NEXT STEP</div>
      <div class="kicker">Book a 20-minute call.<br/>I'll walk through the findings + priorities.</div>
    </div>
    <a class="cta-pill" href="{_html.escape(book_call_url)}">Book A Call</a>
  </div>

  <div class="footer-pdf">
    <div>{socials_html}</div>
    <div class="tabular">{_html.escape(audit_date)}</div>
  </div>
</div>
</body>
</html>
"""


def build_proposal_pdf(
    lead: dict[str, Any],
    audit: dict[str, Any],
    out_path: str | Path,
    preview_url: str | None = None,
    **kwargs,
) -> Path:
    html = build_proposal_html(lead, audit, preview_url=preview_url, **kwargs)
    return render_pdf(html, out_path)
