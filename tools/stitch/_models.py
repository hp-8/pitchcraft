"""Pydantic models for Stitch screen prompt building."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Vertical = Literal["restaurant", "dental", "realtor", "fnb"]
Page = Literal["landing", "services", "about", "contact"]


class LeadContext(BaseModel):
    """Per-lead brand context fed into the Stitch prompt builder."""

    lead_id: str
    business: str
    vertical: Vertical
    tagline: str | None = None
    services: list[str] = Field(default_factory=list)
    location: str | None = None
    phone: str | None = None
    booking_provider: str | None = None
    extra_context: str | None = None


class ScreenRequest(BaseModel):
    """One Stitch screen-generation request (one page, one variant)."""

    page: Page
    variant_idx: int
    variant_direction: str
    prompt: str
    design_system_id: str
    target_path: str
