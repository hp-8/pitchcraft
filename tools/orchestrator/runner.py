"""Async pipeline runner — drives N leads in parallel through the factory.

Stitch fulfillment (Phase 6b) requires CC-side MCP calls. The runner pauses
after writing all envelopes and returns. A separate CC skill / Python entry
runs MCP fulfillment, then the user re-invokes `orchestrator resume` to drive
the remaining phases (polish, build, email).
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from tools.orchestrator._models import BatchResult, LeadJob, PhaseResult
from tools.orchestrator._phases import (
    phase_audit,
    phase_build,
    phase_council_async,
    phase_design_ref,
    phase_keywords,
    phase_polish,
    phase_scrape,
    phase_stitch_envelope,
)
from tools.orchestrator._state import StateDriver
from tools.orchestrator._workers import build_semaphores

logger = logging.getLogger(__name__)

STATE_DIR = Path(".orchestrator")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _gated(sem: asyncio.Semaphore, coro):
    async with sem:
        return await coro


async def run_pre_stitch(
    job: LeadJob,
    sems: dict[str, asyncio.Semaphore],
    state: StateDriver,
) -> list[PhaseResult]:
    """Audit → keywords (NLP) → scrape → design_ref → council (fire-and-forget).

    Audit runs first (reuses Firecrawl). keywords consumes audit + crawls 2 extra pages.
    Scrape then runs with NLP keywords (falls back to VERTICAL_SEEDS if missing).
    design_ref blocks on scrape.
    """
    results: list[PhaseResult] = []

    # 1) Audit alone (keywords pipeline reuses its Firecrawl markdown)
    await state.update_status(job.lead_id, "audit", "running")
    audit_res = await _gated(sems["audit"], phase_audit(job))
    results.append(audit_res)
    await state.update_status(job.lead_id, "audit", "done" if audit_res.ok else "error",
                              note=audit_res.error)

    # 2) NLP keywords (non-fatal if it fails — scraper falls back to seeds)
    kw_res = await _gated(sems["keywords"], phase_keywords(job))
    results.append(kw_res)

    # 3) Scrape moodboard with NLP-driven queries
    scrape_res = await _gated(sems["scrape"], phase_scrape(job))
    results.append(scrape_res)
    if not scrape_res.ok:
        await state.update_status(job.lead_id, "scrape", "error", note=scrape_res.error)
        return results

    await state.update_status(job.lead_id, "design_ref", "running")
    dr_res = await _gated(sems["design_ref"], phase_design_ref(job))
    results.append(dr_res)
    await state.update_status(job.lead_id, "design_ref", "done" if dr_res.ok else "error",
                              note=dr_res.error)

    # Fire-and-forget council (non-blocking).
    council_res = await _gated(sems["council"], phase_council_async(job))
    results.append(council_res)
    return results


async def run_envelope(
    job: LeadJob,
    design_system_id: str,
    sems: dict[str, asyncio.Semaphore],
    state: StateDriver,
) -> PhaseResult:
    await state.update_status(job.lead_id, "stitch_envelope", "queued")
    env_res = await _gated(sems["stitch_envelope"], phase_stitch_envelope(job, design_system_id))
    await state.update_status(
        job.lead_id, "stitch_envelope",
        "queued" if env_res.ok else "error",
        note=env_res.error,
    )
    return env_res


async def run_post_stitch(
    job: LeadJob,
    sems: dict[str, asyncio.Semaphore],
    state: StateDriver,
    skip_deploy: bool = False,
) -> list[PhaseResult]:
    """Phases 6c + 6d — polish + build/deploy. Assumes stitch fulfillment done."""
    results: list[PhaseResult] = []
    await state.update_status(job.lead_id, "polish", "running")
    polish_res = await _gated(sems["polish"], phase_polish(job))
    results.append(polish_res)
    await state.update_status(job.lead_id, "polish", "done" if polish_res.ok else "error",
                              note=polish_res.error)
    if not polish_res.ok:
        return results

    await state.update_status(job.lead_id, "build", "running")
    build_res = await _gated(sems["build"], phase_build(job, skip_deploy=skip_deploy))
    results.append(build_res)
    await state.update_status(
        job.lead_id, "build",
        "deployed" if build_res.ok and build_res.artifacts.get("deploy_url") else "built",
        note=build_res.error,
    )
    if build_res.artifacts.get("deploy_url"):
        await state.upsert(job.lead_id, {
            "prototype_url": build_res.artifacts["deploy_url"],
            "deployed_at": _utc_now(),
        })
    return results


async def run_batch(
    jobs: Iterable[LeadJob],
    design_system_id: str,
    sheets_client=None,
    skip_deploy: bool = False,
    pause_at_stitch: bool = True,
) -> BatchResult:
    """Run pre-stitch + envelope phases for all jobs in parallel.

    If pause_at_stitch=True (default), returns after writing envelopes so the
    CC-side Stitch fulfillment loop can pick them up. Otherwise runs straight
    through (only viable when stitch fulfillment already happened or is mocked).
    """
    jobs_list = list(jobs)
    started = _utc_now()
    sems = build_semaphores()
    state = StateDriver(sheets_client)
    per_lead: dict[str, list[PhaseResult]] = {}
    by_ok: dict[str, int] = {}
    by_err: dict[str, int] = {}

    async def drive_pre(j: LeadJob) -> None:
        res = await run_pre_stitch(j, sems, state)
        per_lead.setdefault(j.lead_id, []).extend(res)

    await asyncio.gather(*[drive_pre(j) for j in jobs_list], return_exceptions=False)

    async def drive_env(j: LeadJob) -> None:
        if not j.design_md_path:
            return
        res = await run_envelope(j, design_system_id, sems, state)
        per_lead.setdefault(j.lead_id, []).append(res)

    await asyncio.gather(*[drive_env(j) for j in jobs_list], return_exceptions=False)

    # Tally
    for lead_id, results in per_lead.items():
        for r in results:
            (by_ok if r.ok else by_err).update({r.phase: (by_ok if r.ok else by_err).get(r.phase, 0) + 1})

    result = BatchResult(
        started_at=started,
        finished_at=_utc_now() if not pause_at_stitch else None,
        total_leads=len(jobs_list),
        by_phase_ok=by_ok,
        by_phase_err=by_err,
        per_lead=per_lead,
        paused_at_stitch_fulfill=pause_at_stitch,
    )

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "last_batch.json").write_text(
        json.dumps(result.model_dump(), indent=2), encoding="utf-8"
    )

    if pause_at_stitch:
        return result

    # Continue post-stitch (only when caller knows fulfillment happened)
    async def drive_post(j: LeadJob) -> None:
        res = await run_post_stitch(j, sems, state, skip_deploy=skip_deploy)
        per_lead.setdefault(j.lead_id, []).extend(res)

    await asyncio.gather(*[drive_post(j) for j in jobs_list], return_exceptions=False)

    result.finished_at = _utc_now()
    (STATE_DIR / "last_batch.json").write_text(
        json.dumps(result.model_dump(), indent=2), encoding="utf-8"
    )
    return result


async def resume_post_stitch(
    jobs: Iterable[LeadJob],
    sheets_client=None,
    skip_deploy: bool = False,
) -> BatchResult:
    """After Stitch fulfillment, drive polish + build/deploy in parallel."""
    jobs_list = list(jobs)
    started = _utc_now()
    sems = build_semaphores()
    state = StateDriver(sheets_client)
    per_lead: dict[str, list[PhaseResult]] = {}

    async def drive(j: LeadJob) -> None:
        res = await run_post_stitch(j, sems, state, skip_deploy=skip_deploy)
        per_lead.setdefault(j.lead_id, []).extend(res)

    await asyncio.gather(*[drive(j) for j in jobs_list], return_exceptions=False)

    by_ok: dict[str, int] = {}
    by_err: dict[str, int] = {}
    for results in per_lead.values():
        for r in results:
            (by_ok if r.ok else by_err).update({r.phase: (by_ok if r.ok else by_err).get(r.phase, 0) + 1})

    return BatchResult(
        started_at=started, finished_at=_utc_now(),
        total_leads=len(jobs_list),
        by_phase_ok=by_ok, by_phase_err=by_err,
        per_lead=per_lead, paused_at_stitch_fulfill=False,
    )
