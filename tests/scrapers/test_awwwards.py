"""Tests for tools.scrapers.awwwards."""
from __future__ import annotations

import importlib

import pytest

from tools.scrapers import _cache, awwwards
from tools.scrapers._models import CaptureResult, ScraperResult

LIST_HTML = """
<html>
<a href="/sites/cool-site-one"><img src="https://cdn.example/1.jpg" /></a>
<a href="/sites/cool-site-two"><img src="https://cdn.example/2.jpg" /></a>
</html>
"""

DETAIL_HTML = """
<html>
<a class="website-button btn" href="https://external.example/site">visit</a>
<img src="https://cdn.example/thumb.jpg" />
</html>
"""


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", tmp_path / "db.sqlite")
    importlib.reload(awwwards)


def _stub_stealth_factory(html_by_url):
    def _stub(url: str):
        for needle, html in html_by_url.items():
            if needle in url:
                return html
        return None
    return _stub


def test_happy_path(monkeypatch):
    monkeypatch.setattr(
        awwwards,
        "_stealth_get",
        _stub_stealth_factory({"/websites/": LIST_HTML, "/sites/": DETAIL_HTML}),
    )
    result = awwwards.fetch_awwwards(query="design", limit=2, use_cache=False)
    assert isinstance(result, ScraperResult)
    assert len(result.items) == 2
    assert result.items[0].url.startswith("https://www.awwwards.com/sites/")
    assert result.items[0].image_url == "https://cdn.example/thumb.jpg"


def test_empty_when_blocked(monkeypatch):
    monkeypatch.setattr(awwwards, "_stealth_get", lambda url: None)
    result = awwwards.fetch_awwwards(query="boom", limit=5, use_cache=False)
    assert result.items == []


def test_cache_hit(monkeypatch):
    calls = {"n": 0}

    def _stub(url):
        calls["n"] += 1
        if "/websites/" in url:
            return LIST_HTML
        return DETAIL_HTML

    monkeypatch.setattr(awwwards, "_stealth_get", _stub)
    awwwards.fetch_awwwards(query="z", limit=2, use_cache=True)
    n = calls["n"]
    awwwards.fetch_awwwards(query="z", limit=2, use_cache=True)
    assert calls["n"] == n


def test_capture_invoked(monkeypatch):
    monkeypatch.setattr(
        awwwards,
        "_stealth_get",
        _stub_stealth_factory({"/websites/": LIST_HTML, "/sites/": DETAIL_HTML}),
    )

    def _fake_capture(url, slug, source, **kw):
        return CaptureResult(
            url=url, source=source, slug=slug,
            captured_at="2025-01-01T00:00:00+00:00",
            artifact_dir=f"/tmp/{slug}",
            video_path=f"/tmp/{slug}/preview.webm",
            thumbnail_path=f"/tmp/{slug}/thumb.jpg",
            libs_detected=["gsap"], keyframes_count=2, has_animation=True,
        )

    monkeypatch.setattr(awwwards._capture, "capture_url", _fake_capture)
    result = awwwards.fetch_awwwards(query="x", limit=1, use_cache=False, do_capture=True)
    assert result.items[0].preview_mp4_path.endswith("preview.webm")
    assert "gsap" in result.items[0].libs_detected


def test_schema_validates(monkeypatch):
    monkeypatch.setattr(awwwards, "_stealth_get", lambda url: LIST_HTML if "websites" in url else DETAIL_HTML)
    result = awwwards.fetch_awwwards(query="s", limit=1, use_cache=False)
    ScraperResult.model_validate(result.model_dump())
