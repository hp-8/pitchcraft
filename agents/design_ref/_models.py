"""Pydantic models for the design-ref agent."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class MoodboardItem(BaseModel):
    """A single ref item inside a moodboard (mirrors ScraperItem loosely)."""

    id: str
    title: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    source: str
    tags: List[str] = Field(default_factory=list)
    libs_detected: List[str] = Field(default_factory=list)
    has_animation: bool = False
    preview_mp4_path: Optional[str] = None
    components_tsx_path: Optional[str] = None
    score: float = 0.0


class Moodboard(BaseModel):
    """Combined moodboard input — usually the dedup'd output of Phase 1 scrapers."""

    vertical: str
    style: str
    items: List[MoodboardItem] = Field(default_factory=list)


class ColorPalette(BaseModel):
    primary: str = "#111111"
    accent: str = "#ff5a3c"
    neutral_0: str = "#ffffff"
    neutral_50: str = "#f6f6f6"
    neutral_100: str = "#ececec"
    neutral_500: str = "#888888"
    neutral_900: str = "#0a0a0a"
    background: str = "#ffffff"
    surface: str = "#f6f6f6"


class TypographySpec(BaseModel):
    display: str = "Inter Variable, 600/700/900, 48–120px clamp"
    body: str = "Inter, 400/500, 16–18px"
    mono: Optional[str] = "JetBrains Mono, 400, 14px"


class DesignSpec(BaseModel):
    """Everything required to render a DESIGN.md."""

    vertical: str
    style: str
    slug: str
    brand_mood: str
    palette: ColorPalette
    typography: TypographySpec
    spacing_base: str = "8px (with 4px micro-unit)"
    radius_scale: str = "0, 4px, 8px, 16px, 24px, 9999px"
    component_patterns: List[str] = Field(default_factory=list)
    motion_references: List[MoodboardItem] = Field(default_factory=list)
    image_direction: str
    all_references: List[MoodboardItem] = Field(default_factory=list)
