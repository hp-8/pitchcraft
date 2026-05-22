"""Orchestrator data models."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# Phase order. Each phase has a sheet status field it advances.
PHASE_ORDER: tuple[str, ...] = (
    "audit",        # Phase 2
    "keywords",     # NLP — runs after audit (reuses Firecrawl)
    "scrape",       # Phase 1: moodboard (consumes keywords.json if present)
    "design_ref",   # Phase 3: DESIGN.md
    "council",      # Phase 6a: design_brief.md (fire-and-forget)
    "stitch_envelope",  # Phase 4: build screen envelope JSON
    "stitch_fulfill",   # Phase 6b: MCP calls (driven by CC skill)
    "polish",       # Phase 6c
    "build",        # Phase 6d: assemble + Vercel deploy
    "email",        # Phase 7
)

# Per-phase concurrency caps. Stitch fulfill is overridden by probe.
DEFAULT_CONCURRENCY: dict[str, int] = {
    "scrape": 10,
    "audit": 10,
    "keywords": 5,        # KeyBERT model is memory-heavy; lower fan-out
    "design_ref": 10,
    "council": 10,
    "stitch_envelope": 20,
    "stitch_fulfill": 3,
    "polish": 10,
    "build": 5,
    "email": 1,
}


class LeadJob(BaseModel):
    """One lead's state through the pipeline."""
    lead_id: str
    business: str
    vertical: str
    site_url: str
    email: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    services: list[str] = Field(default_factory=list)
    tagline: Optional[str] = None
    phone: Optional[str] = None
    # Working state
    lead_dir: Optional[str] = None
    design_dir: Optional[str] = None
    audit_path: Optional[str] = None
    moodboard_path: Optional[str] = None
    keywords_path: Optional[str] = None
    design_md_path: Optional[str] = None
    brief_path: Optional[str] = None
    envelope_path: Optional[str] = None
    approved_path: Optional[str] = None
    site_dir: Optional[str] = None
    deploy_url: Optional[str] = None
    # Progress
    current_phase: Optional[str] = None
    completed_phases: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PhaseResult(BaseModel):
    lead_id: str
    phase: str
    ok: bool
    duration_s: float
    error: Optional[str] = None
    artifacts: dict[str, Any] = Field(default_factory=dict)


class BatchResult(BaseModel):
    started_at: str
    finished_at: Optional[str] = None
    total_leads: int
    by_phase_ok: dict[str, int] = Field(default_factory=dict)
    by_phase_err: dict[str, int] = Field(default_factory=dict)
    per_lead: dict[str, list[PhaseResult]] = Field(default_factory=dict)
    paused_at_stitch_fulfill: bool = False
