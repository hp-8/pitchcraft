"""Approval gate UI — Flask app for selecting Stitch variants per lead.

Usage:
    python -m tools.approval --port 8765 --out-dir data/outputs

Routes:
    GET  /                          — list leads with available envelopes
    GET  /lead/<lead_id>            — variant grid (4 pages × N variants)
    GET  /variant/<lead_id>/<page>/<idx>  — iframe-serve a single variant HTML
    POST /approve                   — JSON {lead_id, page, variant_idx} → updates approved.json
    POST /finalize/<lead_id>        — write final approved.json + redirect home
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, redirect, request, send_file, url_for
from markupsafe import escape

logger = logging.getLogger(__name__)

PAGES = ("landing", "services", "about", "contact")


def _read_envelope(lead_dir: Path) -> dict | None:
    p = lead_dir / "stitch_screens_request.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _list_leads(out_root: Path) -> list[dict]:
    leads: list[dict] = []
    for lead_dir in sorted(out_root.iterdir()):
        if not lead_dir.is_dir():
            continue
        env = _read_envelope(lead_dir)
        if env is None:
            # Still surface leads with stitch/ folder
            if not (lead_dir / "stitch").exists():
                continue
            env = {"lead_id": lead_dir.name, "business": lead_dir.name, "screens": []}
        screens = env.get("screens") or []
        fulfilled = sum(1 for s in screens if s.get("fulfilled"))
        approved_path = lead_dir / "approved.json"
        approved = {}
        if approved_path.exists():
            try:
                approved = json.loads(approved_path.read_text(encoding="utf-8")).get("approved") or {}
            except Exception:
                approved = {}
        leads.append({
            "lead_id": env.get("lead_id") or lead_dir.name,
            "business": env.get("business") or lead_dir.name,
            "lead_dir": str(lead_dir),
            "fulfilled": fulfilled,
            "total": len(screens),
            "approved_pages": list(approved.keys()),
        })
    return leads


def _list_variants(lead_dir: Path) -> dict[str, list[int]]:
    """Walk lead_dir/stitch/ for <page>-v<idx>.html files."""
    stitch = lead_dir / "stitch"
    out: dict[str, list[int]] = {}
    if not stitch.exists():
        return out
    for html in sorted(stitch.glob("*-v*.html")):
        stem = html.stem  # e.g. landing-v0
        if "-v" not in stem:
            continue
        page, _, idx = stem.rpartition("-v")
        try:
            out.setdefault(page, []).append(int(idx))
        except ValueError:
            continue
    for page in list(out.keys()):
        out[page].sort()
    return out


def _read_approved(lead_dir: Path) -> dict[str, int]:
    p = lead_dir / "approved.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {str(k): int(v) for k, v in (data.get("approved") or {}).items()}
    except Exception:
        return {}


def _write_approved(lead_dir: Path, approved: dict[str, int]) -> None:
    p = lead_dir / "approved.json"
    p.write_text(json.dumps({"approved": approved}, indent=2), encoding="utf-8")


# ---- Templates (inline so no static deps) -----------------------------------

_BASE_CSS = """
body { font: 13px/1.5 ui-sans-serif, system-ui, -apple-system, sans-serif;
  color: #1A1410; background: #FAF7F2; margin: 0; padding: 24px; }
a { color: #2A1414; text-decoration: none; }
a:hover { text-decoration: underline; }
h1 { font: 600 28px/1.1 "Iowan Old Style", Georgia, serif; margin: 0 0 18px; }
h2 { font: 600 18px/1.1 "Iowan Old Style", Georgia, serif; margin: 16px 0 8px;
  letter-spacing: 0.02em; text-transform: uppercase; font-size: 11px;
  color: #6B655A; letter-spacing: 0.16em; }
.lead-row { border-top: 1px solid #E2DACB; padding: 12px 0; display: flex;
  justify-content: space-between; align-items: center; gap: 12px; }
.lead-row .meta { font-family: ui-monospace, "JetBrains Mono", monospace;
  font-size: 11px; color: #6B655A; letter-spacing: 0.1em; text-transform: uppercase; }
.btn { display: inline-block; padding: 6px 14px; background: #2A1414;
  color: #FAF7F2; border: 0; border-radius: 2px; cursor: pointer;
  font: 500 11px/1 ui-monospace, monospace; letter-spacing: 0.16em;
  text-transform: uppercase; }
.btn--ghost { background: transparent; color: #2A1414; border: 1px solid #2A1414; }
.btn--brass { background: #B08D57; color: #FAF7F2; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.variant { border: 1px solid #E2DACB; border-radius: 2px; overflow: hidden;
  background: #fff; display: flex; flex-direction: column; }
.variant.is-approved { border: 2px solid #B08D57; box-shadow: 0 0 0 2px rgba(176,141,87,0.18); }
.variant iframe { width: 100%; height: 320px; border: 0; pointer-events: none;
  transform: scale(0.6); transform-origin: 0 0; width: 167%; height: 533px; }
.variant .frame { height: 320px; overflow: hidden; background: #F1ECE3; position: relative; }
.variant .actions { padding: 8px 12px; display: flex; justify-content: space-between;
  align-items: center; border-top: 1px solid #E2DACB; font-family: ui-monospace, monospace;
  font-size: 11px; }
.page-block { margin-bottom: 28px; }
.brand { font: italic 600 22px/1 "Iowan Old Style", Georgia, serif;
  letter-spacing: -0.02em; margin-bottom: 4px; }
.eyebrow { font-family: ui-monospace, monospace; font-size: 11px; color: #6B655A;
  letter-spacing: 0.18em; text-transform: uppercase; }
.toolbar { display: flex; gap: 8px; margin-top: 18px; }
.muted { color: #6B655A; }
"""


def _layout(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>{escape(title)}</title>
<style>{_BASE_CSS}</style>
</head><body>{body}</body></html>"""


def _render_index(leads: list[dict]) -> str:
    rows = ""
    if not leads:
        rows = '<p class="muted">No leads with Stitch envelopes found in data/outputs/.</p>'
    for l in leads:
        rows += f'''
        <div class="lead-row">
          <div>
            <div class="brand">{escape(l['business'])}</div>
            <div class="meta">{escape(l['lead_id'])} · fulfilled {l['fulfilled']}/{l['total']} · approved {len(l['approved_pages'])}/{len(PAGES)}</div>
          </div>
          <a class="btn" href="{url_for('lead_view', lead_id=l['lead_id'])}">Review variants →</a>
        </div>'''
    body = f'''
    <div class="brand">Harsh Patadia <span class="eyebrow muted">· approval gate</span></div>
    <h1>Leads awaiting variant approval</h1>
    {rows}'''
    return _layout("Approval gate", body)


def _render_lead(lead: dict, variants: dict[str, list[int]], approved: dict[str, int]) -> str:
    blocks = ""
    for page in PAGES:
        idxs = variants.get(page, [])
        if not idxs:
            blocks += f'<div class="page-block"><h2>{page}</h2><p class="muted">No variants found.</p></div>'
            continue
        cards = ""
        for idx in idxs:
            is_approved = approved.get(page) == idx
            ap_cls = " is-approved" if is_approved else ""
            label = "Approved" if is_approved else "Approve"
            btn_cls = "btn btn--brass" if is_approved else "btn btn--ghost"
            cards += f'''
            <div class="variant{ap_cls}" id="card-{page}-v{idx}">
              <div class="frame">
                <iframe src="{url_for('serve_variant', lead_id=lead['lead_id'], page=page, idx=idx)}" loading="lazy"></iframe>
              </div>
              <div class="actions">
                <span class="muted">v{idx}</span>
                <button class="{btn_cls}" onclick="approve('{lead['lead_id']}','{page}',{idx})">{label}</button>
              </div>
            </div>'''
        blocks += f'<div class="page-block"><h2>{page}</h2><div class="grid">{cards}</div></div>'

    body = f'''
    <div class="brand">{escape(lead['business'])} <span class="eyebrow muted">· {escape(lead['lead_id'])}</span></div>
    <h1>Pick one variant per page</h1>
    <div class="toolbar">
      <a class="btn btn--ghost" href="{url_for('index')}">← Back</a>
      <form action="{url_for('finalize', lead_id=lead['lead_id'])}" method="post" style="display:inline">
        <button class="btn" type="submit">Finalize approval & continue</button>
      </form>
    </div>
    {blocks}
    <script>
      async function approve(leadId, page, idx) {{
        const r = await fetch('/approve', {{ method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ lead_id: leadId, page, variant_idx: idx }}) }});
        if (r.ok) location.reload();
        else alert('Approve failed: ' + r.status);
      }}
    </script>'''
    return _layout(f"Approve · {lead['business']}", body)


# ---- App factory ------------------------------------------------------------


def create_app(out_root: Path) -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        leads = _list_leads(out_root)
        return _render_index(leads)

    @app.route("/lead/<lead_id>")
    def lead_view(lead_id: str):
        lead_dir = _find_lead_dir(out_root, lead_id)
        if lead_dir is None:
            abort(404)
        env = _read_envelope(lead_dir) or {"lead_id": lead_id, "business": lead_id}
        lead = {
            "lead_id": env.get("lead_id") or lead_id,
            "business": env.get("business") or lead_id,
            "lead_dir": str(lead_dir),
        }
        variants = _list_variants(lead_dir)
        approved = _read_approved(lead_dir)
        return _render_lead(lead, variants, approved)

    @app.route("/variant/<lead_id>/<page>/<int:idx>")
    def serve_variant(lead_id: str, page: str, idx: int):
        lead_dir = _find_lead_dir(out_root, lead_id)
        if lead_dir is None:
            abort(404)
        html = lead_dir / "stitch" / f"{page}-v{idx}.html"
        if not html.exists():
            abort(404)
        return send_file(html, mimetype="text/html")

    @app.route("/approve", methods=["POST"])
    def approve():
        body = request.get_json(silent=True) or {}
        lead_id = body.get("lead_id")
        page = body.get("page")
        idx = body.get("variant_idx")
        if not lead_id or page not in PAGES or idx is None:
            return jsonify({"error": "bad request"}), 400
        lead_dir = _find_lead_dir(out_root, lead_id)
        if lead_dir is None:
            return jsonify({"error": "lead not found"}), 404
        approved = _read_approved(lead_dir)
        approved[page] = int(idx)
        _write_approved(lead_dir, approved)
        return jsonify({"ok": True, "approved": approved})

    @app.route("/finalize/<lead_id>", methods=["POST"])
    def finalize(lead_id: str):
        lead_dir = _find_lead_dir(out_root, lead_id)
        if lead_dir is None:
            abort(404)
        approved = _read_approved(lead_dir)
        _write_approved(lead_dir, approved)  # no-op re-write to ensure file exists
        return redirect(url_for("index"))

    return app


def _find_lead_dir(out_root: Path, lead_id: str) -> Path | None:
    # Match by exact dir name OR by envelope lead_id field
    direct = out_root / lead_id
    if direct.exists() and direct.is_dir():
        return direct
    for d in out_root.iterdir():
        if not d.is_dir():
            continue
        env = _read_envelope(d)
        if env and env.get("lead_id") == lead_id:
            return d
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Approval gate UI.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--out-dir", default="data/outputs")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    out_root = Path(args.out_dir).resolve()
    if not out_root.exists():
        raise SystemExit(f"out-dir does not exist: {out_root}")
    app = create_app(out_root)
    logger.info("approval gate serving %s on http://%s:%d", out_root, args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
