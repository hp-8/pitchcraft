"""Pitchcraft operator API.

Reads pipeline state straight from disk (data/leads/*.csv, data/outputs/<slug>/)
and launches orchestrator runs as subprocesses. The web console talks only to this.

Run:  uv run uvicorn api.server:app --host 0.0.0.0 --port 8000
Auth: every /api route requires `Authorization: Bearer $PITCHCRAFT_API_TOKEN`.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
LEADS_DIR = ROOT / "data" / "leads"
OUT_DIR = ROOT / "data" / "outputs"
RUNS_DIR = ROOT / "data" / "runs"

REQUIRED_COLS = ("lead_id", "business", "vertical", "site_url")
VERTICALS = {"restaurant", "dental", "realtor", "fnb"}
MAX_CSV_BYTES = 5 * 1024 * 1024
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,80}$")

# Phase → how to tell it's done from files on disk. Order = pipeline order.
PHASES = ("audit", "references", "brief", "screens", "site", "deploy", "pdfs")

app = FastAPI(title="Pitchcraft API", docs_url=None, redoc_url=None)
_procs: dict[str, subprocess.Popen] = {}


def require_token(authorization: str = Header(default="")) -> None:
    expected = os.getenv("PITCHCRAFT_API_TOKEN")
    if not expected:
        raise HTTPException(503, "PITCHCRAFT_API_TOKEN not configured on server")
    if not secrets.compare_digest(authorization, f"Bearer {expected}"):
        raise HTTPException(401, "unauthorized")


auth = [Depends(require_token)]


# ---------------------------------------------------------------- helpers ---


def _safe_id(value: str) -> str:
    if not SLUG_RE.match(value):
        raise HTTPException(400, "invalid id")
    return value


def _lead_slug(site_url: str, lead_id: str) -> str:
    # Mirrors tools/orchestrator/_phases.py::_lead_dir
    host = urlparse(site_url).hostname or lead_id
    return host.replace(".", "-")


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _mtime(path: Path) -> str | None:
    try:
        ts = path.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _phase_status(d: Path) -> dict[str, str]:
    """done | waiting (manual step) | pending."""
    stitch = d / "stitch"
    build = _read_json(d / "build.json") or {}
    s = {
        "audit": (d / "audit.json").exists(),
        "references": (d / "moodboard.json").exists(),
        "brief": (d / "design_brief.md").exists(),
        "screens": stitch.is_dir() and any(stitch.rglob("*.html")),
        "site": (d / "site" / "index.html").exists(),
        "deploy": bool(build.get("deploy_url")),
        "pdfs": (d / "audit.pdf").exists() and (d / "proposal.pdf").exists(),
    }
    out = {k: "done" if v else "pending" for k, v in s.items()}
    if not s["screens"] and (d / "stitch_screens_request.json").exists():
        out["screens"] = "waiting"
    return out


def _lead_summary(row: dict) -> dict:
    slug = _lead_slug(row.get("site_url", ""), row.get("lead_id", ""))
    d = OUT_DIR / slug
    audit = _read_json(d / "audit.json") or {}
    decision = _read_json(d / "decision.json") or {}
    build = _read_json(d / "build.json") or {}
    impact = audit.get("dollar_impact") or {}
    problems = audit.get("problems") or []
    return {
        "lead_id": row.get("lead_id"),
        "slug": slug,
        "business": row.get("business"),
        "vertical": row.get("vertical"),
        "site_url": row.get("site_url"),
        "email": row.get("email") or None,
        "location": row.get("location") or None,
        "phases": _phase_status(d),
        "problem_count": len(problems),
        "high_count": sum(1 for p in problems if p.get("severity") == "high"),
        "loss_low": impact.get("monthly_loss_low"),
        "loss_high": impact.get("monthly_loss_high"),
        "deploy_url": build.get("deploy_url"),
        "decision": decision.get("decision"),
        "updated_at": _mtime(d),
    }


def _batch_rows(batch_id: str) -> list[dict]:
    path = LEADS_DIR / f"{_safe_id(batch_id)}.csv"
    if not path.exists():
        raise HTTPException(404, "batch not found")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _run_state(batch_id: str) -> dict:
    p = _procs.get(batch_id)
    log = RUNS_DIR / f"{batch_id}.log"
    if p is not None and p.poll() is None:
        state = "running"
    elif p is not None:
        state = "finished" if p.returncode == 0 else "failed"
    else:
        state = "idle"
    return {"state": state, "log_updated_at": _mtime(log)}


# ----------------------------------------------------------------- routes ---


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/api/batches", dependencies=auth)
def list_batches() -> list[dict]:
    LEADS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for path in sorted(LEADS_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not SLUG_RE.match(path.stem):
            continue
        leads = [_lead_summary(r) for r in _batch_rows(path.stem)]
        out.append({
            "id": path.stem,
            "created_at": _mtime(path),
            "total": len(leads),
            "deployed": sum(1 for l in leads if l["phases"]["deploy"] == "done"),
            "waiting": sum(1 for l in leads if "waiting" in l["phases"].values()),
            "to_review": sum(1 for l in leads if l["decision"] is None and l["phases"]["site"] == "done"),
            "approved": sum(1 for l in leads if l["decision"] == "approved"),
            "rejected": sum(1 for l in leads if l["decision"] == "rejected"),
            "phase_done": {ph: sum(1 for l in leads if l["phases"][ph] == "done") for ph in PHASES},
            "run": _run_state(path.stem),
        })
    return out


@app.post("/api/batches", dependencies=auth)
async def upload_batch(file: UploadFile = File(...)) -> dict:
    raw = await file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(413, "CSV larger than 5 MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV must be UTF-8")
    reader = csv.DictReader(io.StringIO(text))
    cols = [c.strip() for c in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED_COLS if c not in cols]
    if missing:
        raise HTTPException(400, f"Missing columns: {', '.join(missing)}")
    rows, errors, seen = [], [], set()
    for i, row in enumerate(reader, start=2):
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        if not all(row.get(c) for c in REQUIRED_COLS):
            errors.append(f"Row {i}: empty required field")
        elif row["vertical"] not in VERTICALS:
            errors.append(f"Row {i}: vertical '{row['vertical']}' not one of {sorted(VERTICALS)}")
        elif not row["site_url"].startswith(("http://", "https://")):
            errors.append(f"Row {i}: site_url must start with http(s)://")
        elif row["lead_id"] in seen:
            errors.append(f"Row {i}: duplicate lead_id {row['lead_id']}")
        else:
            seen.add(row["lead_id"])
            rows.append(row)
    if errors:
        raise HTTPException(400, {"errors": errors[:20], "error_count": len(errors)})
    if not rows:
        raise HTTPException(400, "CSV has no leads")

    stem = re.sub(r"[^a-z0-9_-]+", "-", Path(file.filename or "batch").stem.lower()).strip("-") or "batch"
    batch_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M}-{stem[:40]}"
    LEADS_DIR.mkdir(parents=True, exist_ok=True)
    with (LEADS_DIR / f"{batch_id}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return {"id": batch_id, "total": len(rows)}


@app.get("/api/batches/{batch_id}", dependencies=auth)
def get_batch(batch_id: str) -> dict:
    leads = [_lead_summary(r) for r in _batch_rows(batch_id)]
    return {"id": batch_id, "leads": leads, "run": _run_state(batch_id)}


class RunBody(BaseModel):
    mode: str = "run"  # run | resume
    skip_deploy: bool = False


@app.post("/api/batches/{batch_id}/run", dependencies=auth)
def run_batch(batch_id: str, body: RunBody) -> dict:
    _batch_rows(batch_id)  # 404 check
    if _run_state(batch_id)["state"] == "running":
        raise HTTPException(409, "batch already running")
    if body.mode not in ("run", "resume"):
        raise HTTPException(400, "mode must be run or resume")
    cmd = [sys.executable, "-m", "tools.orchestrator",
           "run-batch" if body.mode == "run" else "resume",
           "--leads", str(LEADS_DIR / f"{batch_id}.csv"), "--no-sheet"]
    if body.mode == "run":
        ds = os.getenv("STITCH_DESIGN_SYSTEM_ID")
        if not ds:
            raise HTTPException(503, "STITCH_DESIGN_SYSTEM_ID not configured on server")
        cmd += ["--design-system-id", ds]
    if body.skip_deploy:
        cmd.append("--skip-deploy")
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    log = (RUNS_DIR / f"{batch_id}.log").open("ab")
    _procs[batch_id] = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    return _run_state(batch_id)


@app.get("/api/batches/{batch_id}/log", dependencies=auth)
def batch_log(batch_id: str) -> dict:
    path = RUNS_DIR / f"{_safe_id(batch_id)}.log"
    if not path.exists():
        return {"lines": []}
    with path.open("rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 32_000))
        tail = f.read().decode("utf-8", "replace").splitlines()[-200:]
    return {"lines": tail}


@app.get("/api/leads/{slug}", dependencies=auth)
def get_lead(slug: str) -> dict:
    d = OUT_DIR / _safe_id(slug)
    if not d.is_dir():
        raise HTTPException(404, "lead not found")
    audit = _read_json(d / "audit.json") or {}
    return {
        "slug": slug,
        "phases": _phase_status(d),
        "audit": {
            "url": audit.get("url"),
            "vertical": audit.get("vertical"),
            "audited_at": audit.get("audited_at"),
            "problems": audit.get("problems") or [],
            "dollar_impact": audit.get("dollar_impact"),
            "pagespeed": audit.get("pagespeed"),
        },
        "build": _read_json(d / "build.json"),
        "decision": _read_json(d / "decision.json"),
        "files": {
            "audit_pdf": (d / "audit.pdf").exists(),
            "proposal_pdf": (d / "proposal.pdf").exists(),
            "site": (d / "site" / "index.html").exists(),
        },
    }


FILE_MAP = {"audit.pdf": "audit.pdf", "proposal.pdf": "proposal.pdf", "site": "site/index.html"}


@app.get("/api/leads/{slug}/file/{name}", dependencies=auth)
def lead_file(slug: str, name: str) -> FileResponse:
    rel = FILE_MAP.get(name)
    if rel is None:
        raise HTTPException(404, "unknown file")
    path = OUT_DIR / _safe_id(slug) / rel
    if not path.is_file():
        raise HTTPException(404, "file not generated yet")
    return FileResponse(path)


class DecisionBody(BaseModel):
    decision: str | None  # approved | rejected | None (clear)
    note: str = ""


@app.post("/api/leads/{slug}/decision", dependencies=auth)
def set_decision(slug: str, body: DecisionBody) -> dict:
    d = OUT_DIR / _safe_id(slug)
    if not d.is_dir():
        raise HTTPException(404, "lead not found")
    if body.decision not in ("approved", "rejected", None):
        raise HTTPException(400, "decision must be approved, rejected or null")
    rec = {"decision": body.decision, "note": body.note[:2000],
           "decided_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    (d / "decision.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rec
