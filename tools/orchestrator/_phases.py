"""Async wrappers for each pipeline phase. CPU/IO bound work runs in threadpool."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from tools.orchestrator._models import LeadJob, PhaseResult

logger = logging.getLogger(__name__)

OUT_ROOT = Path("data/outputs")


# ----------------------- helpers ---------------------------------------------


def _now() -> float:
    return time.perf_counter()


def _result(lead_id: str, phase: str, start: float, ok: bool,
            error: str | None = None, **artifacts: Any) -> PhaseResult:
    return PhaseResult(
        lead_id=lead_id, phase=phase, ok=ok,
        duration_s=round(_now() - start, 2),
        error=error, artifacts=artifacts,
    )


def _lead_dir(job: LeadJob) -> Path:
    if job.lead_dir:
        return Path(job.lead_dir)
    # Slug from site_url host or lead_id fallback
    from urllib.parse import urlparse
    host = urlparse(job.site_url).hostname or job.lead_id
    slug = host.replace(".", "-")
    p = OUT_ROOT / slug
    p.mkdir(parents=True, exist_ok=True)
    job.lead_dir = str(p)
    return p


# ----------------------- Phase 1: scrape moodboard ---------------------------


def _scrape_sync(job: LeadJob, out_path: Path) -> dict:
    from tools.scrapers.cli import run as scrapers_run
    data = scrapers_run(
        vertical=job.vertical, style="editorial", limit=30,
        include_motion=False, use_cache=True,
        keywords_path=job.keywords_path,
    )
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


async def phase_scrape(job: LeadJob) -> PhaseResult:
    start = _now()
    try:
        ld = _lead_dir(job)
        moodboard = ld / "moodboard.json"
        if not moodboard.exists():
            await asyncio.to_thread(_scrape_sync, job, moodboard)
        job.moodboard_path = str(moodboard)
        return _result(job.lead_id, "scrape", start, True, moodboard=str(moodboard))
    except Exception as exc:  # noqa: BLE001
        logger.exception("scrape failed %s", job.lead_id)
        return _result(job.lead_id, "scrape", start, False, error=str(exc))


# ----------------------- Phase 2: audit --------------------------------------


def _audit_sync(job: LeadJob) -> dict:
    from tools.audit.audit import audit as audit_fn
    res = audit_fn(url=job.site_url, vertical=job.vertical, out_dir=str(OUT_ROOT))
    return res.model_dump() if hasattr(res, "model_dump") else res


async def phase_audit(job: LeadJob) -> PhaseResult:
    start = _now()
    try:
        ld = _lead_dir(job)
        audit_path = ld / "audit.json"
        if not audit_path.exists():
            await asyncio.to_thread(_audit_sync, job)
        job.audit_path = str(audit_path)
        return _result(job.lead_id, "audit", start, True, audit=str(audit_path))
    except Exception as exc:  # noqa: BLE001
        logger.exception("audit failed %s", job.lead_id)
        return _result(job.lead_id, "audit", start, False, error=str(exc))


# ----------------------- Phase 1.5: keywords (NLP) ---------------------------


def _keywords_sync(job: LeadJob) -> str:
    from tools.keywords.pipeline import build_keywords
    ld = _lead_dir(job)
    res = build_keywords(
        lead_id=job.lead_id,
        business=job.business,
        vertical=job.vertical,
        site_url=job.site_url,
        lead_dir=ld,
        tagline=job.tagline,
        services=job.services,
        max_pages=3,
        skip_llm=False,
    )
    return str(ld / "keywords.json")


async def phase_keywords(job: LeadJob) -> PhaseResult:
    start = _now()
    try:
        ld = _lead_dir(job)
        keywords_path = ld / "keywords.json"
        if not keywords_path.exists():
            await asyncio.to_thread(_keywords_sync, job)
        job.keywords_path = str(keywords_path)
        return _result(job.lead_id, "keywords", start, True, keywords=str(keywords_path))
    except Exception as exc:  # noqa: BLE001
        logger.exception("keywords failed %s", job.lead_id)
        # Non-fatal — scrapers fall back to VERTICAL_SEEDS
        return _result(job.lead_id, "keywords", start, False, error=str(exc))


# ----------------------- Phase 3: design_ref → DESIGN.md ---------------------


def _design_ref_sync(job: LeadJob, skip_llm: bool = False) -> str:
    from agents.design_ref.agent import build_design_system
    res = build_design_system(
        moodboard_path=Path(job.moodboard_path),
        out_dir=OUT_ROOT,
        skip_llm=skip_llm,
    )
    return res["design_md_path"]


async def phase_design_ref(job: LeadJob) -> PhaseResult:
    """Design ref with automatic LLM fallback.

    Tries LLM enabled first. If every provider in the LLM chain fails
    (rate limit, no key, etc.), retries with skip_llm=True so the pipeline
    keeps moving with a template DESIGN.md derived from the moodboard alone.
    """
    start = _now()
    if not job.moodboard_path:
        return _result(job.lead_id, "design_ref", start, False, error="no moodboard")
    try:
        design_md = await asyncio.to_thread(_design_ref_sync, job, False)
        job.design_md_path = design_md
        job.design_dir = str(Path(design_md).parent)
        return _result(job.lead_id, "design_ref", start, True, design_md=design_md)
    except Exception as exc:
        logger.warning("design_ref LLM failed for %s; retrying without LLM: %s", job.lead_id, exc)
        try:
            design_md = await asyncio.to_thread(_design_ref_sync, job, True)
            job.design_md_path = design_md
            job.design_dir = str(Path(design_md).parent)
            return _result(
                job.lead_id, "design_ref", start, True,
                design_md=design_md, fallback="skip_llm",
            )
        except Exception as exc2:  # noqa: BLE001
            logger.exception("design_ref skip_llm also failed %s", job.lead_id)
            return _result(job.lead_id, "design_ref", start, False, error=str(exc2))


# ----------------------- Phase 6a: council (non-blocking) -------------------


def _council_sync(job: LeadJob) -> str | None:
    from tools.council.orchestrator import run_council
    try:
        result = run_council(
            lead_id=job.lead_id,
            business=job.business,
            vertical=job.vertical,
            location=job.location,
            services=job.services,
            tagline=job.tagline,
            phone=job.phone,
            audit_json=Path(job.audit_path) if job.audit_path else None,
            moodboard=Path(job.moodboard_path) if job.moodboard_path else None,
            design_md=Path(job.design_md_path) if job.design_md_path else None,
            out_dir=OUT_ROOT,
            skip_llm=False,
            sheets_client=None,
        )
        return str(result.brief_path) if hasattr(result, "brief_path") else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("council non-blocking err %s: %s", job.lead_id, exc)
        return None


async def phase_council_async(job: LeadJob) -> PhaseResult:
    """Fire-and-forget. Returns immediately after task scheduled."""
    start = _now()
    asyncio.create_task(asyncio.to_thread(_council_sync, job))
    return _result(job.lead_id, "council", start, True, scheduled=True)


# ----------------------- Phase 4: stitch envelope ---------------------------


def _stitch_envelope_sync(job: LeadJob, design_system_id: str) -> str:
    from tools.stitch._models import LeadContext
    from tools.stitch.screens import write_screens_request
    lead = LeadContext(
        lead_id=job.lead_id, business=job.business, vertical=job.vertical,
        tagline=job.tagline, services=list(job.services),
        location=job.location, phone=job.phone,
    )
    # Load audit problems
    problems: list[str] = []
    if job.audit_path and Path(job.audit_path).exists():
        try:
            data = json.loads(Path(job.audit_path).read_text())
            problems = [p.get("code", "") for p in data.get("problems", [])]
        except Exception:
            pass
    env = write_screens_request(
        lead, design_system_id, audit_problems=problems, out_root=OUT_ROOT,
    )
    return str(env)


async def phase_stitch_envelope(job: LeadJob, design_system_id: str) -> PhaseResult:
    start = _now()
    try:
        env = await asyncio.to_thread(_stitch_envelope_sync, job, design_system_id)
        job.envelope_path = env
        return _result(job.lead_id, "stitch_envelope", start, True, envelope=env)
    except Exception as exc:  # noqa: BLE001
        logger.exception("stitch_envelope failed %s", job.lead_id)
        return _result(job.lead_id, "stitch_envelope", start, False, error=str(exc))


# ----------------------- Phase 6c: polish -----------------------------------


def _polish_sync(job: LeadJob) -> str:
    from tools.polisher.polish import polish_prototype
    lead_dir = Path(job.lead_dir) if job.lead_dir else Path("data/outputs") / job.lead_id
    res = polish_prototype(
        lead_id=job.lead_id,
        lead_dir=lead_dir,
        brief_path=Path(job.brief_path) if job.brief_path else lead_dir / "design_brief.md",
        design_md_path=Path(job.design_md_path) if job.design_md_path else None,
        approved_path=Path(job.approved_path) if job.approved_path else None,
        sheets_client=None,
        business=job.business or "",
        vertical=job.vertical,
    )
    return res.site_dir


async def phase_polish(job: LeadJob) -> PhaseResult:
    start = _now()
    try:
        site_dir = await asyncio.to_thread(_polish_sync, job)
        job.site_dir = site_dir
        return _result(job.lead_id, "polish", start, True, site_dir=site_dir)
    except Exception as exc:  # noqa: BLE001
        logger.exception("polish failed %s", job.lead_id)
        return _result(job.lead_id, "polish", start, False, error=str(exc))


# ----------------------- Phase 6d: build + deploy ---------------------------


def _build_sync(job: LeadJob, skip_deploy: bool) -> dict:
    from tools.builder.prototype import build_prototype
    lead_dir = Path(job.lead_dir) if job.lead_dir else Path("data/outputs") / job.lead_id
    res = build_prototype(
        lead_id=job.lead_id,
        business=job.business,
        vertical=job.vertical,
        lead_dir=lead_dir,
        skip_deploy=skip_deploy,
        sheets_client=None,
    )
    return res.model_dump() if hasattr(res, "model_dump") else dict(res)


async def phase_build(job: LeadJob, skip_deploy: bool = False) -> PhaseResult:
    start = _now()
    try:
        res = await asyncio.to_thread(_build_sync, job, skip_deploy)
        job.deploy_url = res.get("deploy_url")
        return _result(job.lead_id, "build", start, True,
                       deploy_url=job.deploy_url, site_dir=res.get("site_dir"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("build failed %s", job.lead_id)
        return _result(job.lead_id, "build", start, False, error=str(exc))
