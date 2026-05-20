"""Shared Pydantic models for all scrapers."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ScraperItem(BaseModel):
    """A single design reference item from any source."""

    id: str
    title: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    channel: Optional[str] = None
    source: str
    libs_detected: List[str] = Field(default_factory=list)
    has_animation: bool = False
    preview_mp4_path: Optional[str] = None
    components_tsx_path: Optional[str] = None


class ScraperResult(BaseModel):
    """Standard envelope returned by every scraper."""

    source: str
    query: str
    fetched_at: str  # ISO-8601
    items: List[ScraperItem] = Field(default_factory=list)


class CaptureResult(BaseModel):
    """Result of a Playwright capture for a single URL."""

    url: str
    source: str
    slug: str
    captured_at: str  # ISO-8601
    artifact_dir: str
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    libs_detected: List[str] = Field(default_factory=list)
    keyframes_count: int = 0
    has_animation: bool = False
    error: Optional[str] = None
