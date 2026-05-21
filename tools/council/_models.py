"""Pydantic models for the design council."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Genre = Literal["editorial", "modern-minimal", "atmospheric", "playful"]


class CouncilResult(BaseModel):
    """End-to-end output of `run_council`."""

    lead_id: str
    brief_path: str
    chosen_macrostructure: str
    chosen_theme: str
    chosen_nav: str
    chosen_footer: str
    genre: Genre
    must_have_sections: list[str] = Field(default_factory=list)
    motion_primitives: dict[str, list[str]] = Field(default_factory=dict)
    agent_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class AgentOutput(BaseModel):
    """Generic envelope an agent may return (rarely used — agents return raw dicts)."""

    name: str
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
