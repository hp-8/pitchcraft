"""Bundle final per-lead deliverables: PDFs, prototype URL, contact links.

Output layout:
    data/deliverables/<lead_id>/
        proposal.pdf
        audit.pdf
        README.md
        index.html
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_BOOK_CALL_URL = "https://calendar.app.google/hqKrMkn66PddNMaS8"
DEFAULT_SOCIALS = [
    ("Portfolio", "https://www.harshpatadia.space/"),
    ("LinkedIn", "https://www.linkedin.com/in/harsh-patadia/"),
    ("GitHub", "https://github.com/hp-8"),
    ("Substack", "https://substack.com/@damnyouharsh"),
]


def _slug_dir(out_root: Path, row: dict) -> Path:
    host = urlparse(row.get("site_url", "")).hostname or row["lead_id"]
    return out_root / host.replace(".", "-")


def _readme(row: dict, prototype_url: str | None, dated: str) -> str:
    business = row.get("business", row["lead_id"])
    socials_md = "\n".join(f"- **{label}**: {url}" for label, url in DEFAULT_SOCIALS)
    return f"""# {business}

Prepared: {dated}

## Live prototype
{prototype_url or "(not yet deployed)"}

## Files
- `proposal.pdf` ,  one page growth proposal with pricing and timeline.
- `audit.pdf` ,  multi page revenue audit with calculation transparency and local competitor context.

## Book a call
{DEFAULT_BOOK_CALL_URL}

## Contact
{socials_md}
"""


def _index_html(row: dict, prototype_url: str | None, dated: str) -> str:
    business = row.get("business", row["lead_id"])
    socials_html = "".join(
        f'<li><span class="label">{label}</span> <a href="{url}">{url}</a></li>'
        for label, url in DEFAULT_SOCIALS
    )
    proto_block = (
        f'<a class="cta" href="{prototype_url}">Open Prototype</a>'
        if prototype_url else
        '<div class="muted">Prototype not yet deployed.</div>'
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{business} , Deliverables</title>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
  :root {{
    --ink: #0F2A44; --paper: #FAF8F4; --gold: #C9A24B; --muted: #6B7280;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Inter', system-ui, sans-serif;
    background: var(--paper); color: var(--ink);
    margin: 0; padding: 48px 24px; line-height: 1.6;
  }}
  .wrap {{ max-width: 720px; margin: 0 auto; }}
  h1 {{ font-family: 'Playfair Display', Georgia, serif; font-size: 48px; line-height: 1.1; margin: 0 0 8px; letter-spacing: -0.02em; }}
  .date {{ color: var(--muted); font-size: 14px; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 32px; }}
  hr {{ border: 0; border-top: 1px solid var(--gold); margin: 32px 0; }}
  h2 {{ font-family: 'Playfair Display', Georgia, serif; font-size: 24px; margin: 0 0 12px; }}
  ul {{ list-style: none; padding: 0; }}
  ul li {{ padding: 8px 0; border-bottom: 1px solid rgba(15,42,68,0.08); }}
  ul li .label {{ display: inline-block; min-width: 110px; color: var(--muted); }}
  a {{ color: var(--ink); text-decoration: underline; text-decoration-color: var(--gold); }}
  .files {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .file {{ padding: 24px; border: 1px solid rgba(15,42,68,0.12); border-radius: 4px; background: #fff; }}
  .file h3 {{ margin: 0 0 4px; font-size: 18px; }}
  .file p {{ margin: 0 0 12px; color: var(--muted); font-size: 14px; }}
  .file a {{ font-weight: 600; }}
  .cta {{
    display: inline-block; background: var(--ink); color: var(--paper);
    padding: 14px 28px; border-radius: 4px; text-decoration: none;
    font-weight: 600; letter-spacing: 0.05em;
  }}
  .cta:hover {{ background: var(--gold); }}
  .muted {{ color: var(--muted); font-size: 14px; }}
  .footer {{ margin-top: 48px; padding-top: 24px; border-top: 1px solid rgba(15,42,68,0.08); color: var(--muted); font-size: 13px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="date">{dated}</div>
  <h1>{business}</h1>
  <p class="muted">Growth proposal, revenue audit, and live prototype prepared by Harsh Patadia.</p>

  <hr>

  <h2>Live Prototype</h2>
  {proto_block}

  <hr>

  <h2>Documents</h2>
  <div class="files">
    <div class="file">
      <h3>Proposal</h3>
      <p>One page growth plan, pricing, and timeline.</p>
      <a href="proposal.pdf">Open proposal.pdf</a>
    </div>
    <div class="file">
      <h3>Audit</h3>
      <p>Multi page audit with revenue math and local competitor context.</p>
      <a href="audit.pdf">Open audit.pdf</a>
    </div>
  </div>

  <hr>

  <h2>Book a Call</h2>
  <a class="cta" href="{DEFAULT_BOOK_CALL_URL}">Pick a Time</a>

  <hr>

  <h2>Contact</h2>
  <ul>
    {socials_html}
  </ul>

  <div class="footer">
    {business} deliverables bundle. {dated}.
  </div>
</div>
</body>
</html>
"""


def bundle_lead(
    row: dict[str, Any],
    out_root: Path = Path("data/outputs"),
    deliverables_root: Path = Path("data/deliverables"),
) -> Path:
    """Copy PDFs + write README.md + index.html for one lead. Returns dst dir."""
    src_dir = _slug_dir(out_root, row)
    dst_dir = deliverables_root / row["lead_id"]
    dst_dir.mkdir(parents=True, exist_ok=True)

    dated = datetime.now(timezone.utc).strftime("%B %Y")
    prototype_url = row.get("prototype_url") or None

    for name in ("proposal.pdf", "audit.pdf"):
        src = src_dir / name
        if src.exists():
            shutil.copy2(src, dst_dir / name)

    (dst_dir / "README.md").write_text(_readme(row, prototype_url, dated), encoding="utf-8")
    (dst_dir / "index.html").write_text(_index_html(row, prototype_url, dated), encoding="utf-8")

    return dst_dir
