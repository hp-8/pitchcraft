"""Pydantic models for the audit engine."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low"]
Vertical = Literal["restaurant", "dental", "realtor", "fnb"]


class Problem(BaseModel):
    code: str
    severity: Severity
    message: str
    evidence: Optional[str] = None


class DollarImpactItem(BaseModel):
    code: str
    low: int
    high: int
    rationale: str


class DollarImpact(BaseModel):
    monthly_loss_low: int
    monthly_loss_high: int
    breakdown: list[DollarImpactItem] = Field(default_factory=list)


class PageSpeedSummary(BaseModel):
    performance_score: Optional[float] = None
    seo_score: Optional[float] = None
    accessibility_score: Optional[float] = None
    best_practices_score: Optional[float] = None
    lcp_ms: Optional[int] = None
    cls: Optional[float] = None
    inp_ms: Optional[int] = None
    tbt_ms: Optional[int] = None
    opportunities: list[dict[str, Any]] = Field(default_factory=list)


class AuditResult(BaseModel):
    url: str
    vertical: str
    slug: str
    audited_at: str  # ISO-8601
    screenshot_path: Optional[str] = None
    pagespeed: Optional[PageSpeedSummary] = None
    problems: list[Problem] = Field(default_factory=list)
    dollar_impact: DollarImpact
    firecrawl_error: Optional[str] = None
    pagespeed_error: Optional[str] = None
