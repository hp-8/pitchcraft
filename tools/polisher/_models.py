"""Pydantic models for the polisher."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PageReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: str
    source_html: str
    output_html: str
    autotag_counts: dict[str, int] = Field(default_factory=dict)
    honesty_flags: list[str] = Field(default_factory=list)
    slop_gate_failures: list[str] = Field(default_factory=list)
    mobile_fixes_applied: list[str] = Field(default_factory=list)


class PolishResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str
    site_dir: str
    pages: list[PageReport] = Field(default_factory=list)
    libs_loaded: list[str] = Field(default_factory=list)
    theme_name: str = ""
    macrostructure: str = ""
    errors: list[str] = Field(default_factory=list)


class BriefSummary(BaseModel):
    """Parsed shape of design_brief.md the polisher needs."""

    model_config = ConfigDict(extra="forbid")

    business: str = ""
    vertical: str = ""
    genre: str = "editorial"
    macrostructure: str = ""
    theme: str = ""
    paper_band: str = "light"
    display_style: str = "modern-sans"
    accent_hue: str = "warm"
    nav: str = ""
    footer: str = ""
    must_have_sections: list[str] = Field(default_factory=list)
    per_page_motion: dict[str, list[str]] = Field(default_factory=dict)
    libs_required: list[str] = Field(default_factory=list)
    honesty_rules: list[str] = Field(default_factory=list)
    page_transitions: bool = False
    gradient_mesh: bool = False
    raw_palette: str | None = None
    raw_typography: str | None = None
