"""Tests for tools.scrapers.gsap_showcase."""
from __future__ import annotations

import importlib

import pytest

from tools.scrapers import _cache, gsap_showcase
from tools.scrapers._models import CaptureResult, ScraperResult

HTML = """
<img src="https://cdn/g1.jpg" />
<a href="https://siteone.example/">one</a>
<img src="https://cdn/g2.jpg" />
<a href="https://sitetwo.example/landing">two</a>
"""


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", tmp_path / "db.sqlite")
    importlib.reload(gsap_showcase)


def test_happy(monkeypatch):
    monkeypatch.setattr(gsap_showcase, "_fetch", lambda u: HTML)
    r = gsap_showcase.fetch_gsap_showcase(query="", limit=5, use_cache=False)
    assert len(r.items) == 2
    assert "gsap" in r.items[0].libs_detected
    assert r.items[0].has_animation is True


def test_empty(monkeypatch):
    monkeypatch.setattr(gsap_showcase, "_fetch", lambda u: None)
    r = gsap_showcase.fetch_gsap_showcase(query="x", limit=5, use_cache=False)
    assert r.items == []


def test_cache(monkeypatch):
    calls = {"n": 0}

    def _s(u):
        calls["n"] += 1
        return HTML

    monkeypatch.setattr(gsap_showcase, "_fetch", _s)
    gsap_showcase.fetch_gsap_showcase(query="c", limit=2, use_cache=True)
    gsap_showcase.fetch_gsap_showcase(query="c", limit=2, use_cache=True)
    assert calls["n"] == 1


def test_capture(monkeypatch):
    monkeypatch.setattr(gsap_showcase, "_fetch", lambda u: HTML)

    def _fake(url, slug, source, **kw):
        return CaptureResult(
            url=url, source=source, slug=slug,
            captured_at="2025-01-01T00:00:00+00:00",
            artifact_dir="/tmp/x",
            video_path="/tmp/x/preview.webm",
            thumbnail_path="/tmp/x/t.jpg",
            libs_detected=["lenis"], keyframes_count=0, has_animation=True,
        )

    monkeypatch.setattr(gsap_showcase._capture, "capture_url", _fake)
    r = gsap_showcase.fetch_gsap_showcase(query="", limit=1, use_cache=False, do_capture=True)
    assert r.items[0].preview_mp4_path.endswith("preview.webm")
    assert "lenis" in r.items[0].libs_detected


def test_schema(monkeypatch):
    monkeypatch.setattr(gsap_showcase, "_fetch", lambda u: HTML)
    r = gsap_showcase.fetch_gsap_showcase(query="", limit=1, use_cache=False)
    ScraperResult.model_validate(r.model_dump())
