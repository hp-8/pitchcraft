"""Tests for tools.scrapers._capture."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.scrapers import _capture
from tools.scrapers._capture import (
    CaptureError,
    capture_url,
    derive_has_animation,
    extract_libs,
)
from tools.scrapers._models import CaptureResult


# --- Pure helper tests --------------------------------------------------------


def test_derive_has_animation_true_when_libs():
    assert derive_has_animation(["gsap"], 0, False) is True


def test_derive_has_animation_true_when_keyframes():
    assert derive_has_animation([], 3, False) is True


def test_derive_has_animation_true_when_scroll_attr():
    assert derive_has_animation([], 0, True) is True


def test_derive_has_animation_false_when_all_empty():
    assert derive_has_animation([], 0, False) is False


def test_extract_libs_filters_truthy_and_sorts():
    raw = {"libs": {"gsap": True, "lenis": False, "three": True, "motion": False}}
    assert extract_libs(raw) == ["gsap", "three"]


def test_extract_libs_handles_missing_libs_key():
    assert extract_libs({}) == []
    assert extract_libs({"libs": None}) == []


# --- CaptureResult model ------------------------------------------------------


def test_capture_result_roundtrip():
    payload = {
        "url": "https://example.com",
        "source": "awwwards",
        "slug": "example-com",
        "captured_at": "2026-05-20T00:00:00+00:00",
        "artifact_dir": "/tmp/x",
        "video_path": None,
        "thumbnail_path": None,
        "libs_detected": ["gsap"],
        "keyframes_count": 2,
        "has_animation": True,
        "error": None,
    }
    result = CaptureResult.model_validate(payload)
    assert result.libs_detected == ["gsap"]
    assert result.model_dump() == payload


# --- Path construction --------------------------------------------------------


def test_artifact_dir_construction(tmp_path):
    root = str(tmp_path / "refs")
    path = _capture._artifact_dir(root, "awwwards", "cool-site")
    assert path == Path(root) / "awwwards" / "cool-site"


# --- Playwright-not-installed ------------------------------------------------


def test_capture_raises_capture_error_when_playwright_missing(monkeypatch, tmp_path):
    def boom():
        raise ImportError("no playwright")

    monkeypatch.setattr(
        _capture,
        "_import_playwright",
        lambda: (_ for _ in ()).throw(CaptureError("Playwright not installed. Run: playwright install chromium")),
    )
    with pytest.raises(CaptureError) as exc:
        capture_url(
            url="https://x.example",
            slug="x",
            source="test",
            artifact_root=str(tmp_path),
        )
    assert "playwright install" in str(exc.value).lower()


# --- Mocked end-to-end capture ------------------------------------------------


def _make_fake_playwright(monkeypatch, tmp_path, raw_detect=None, video_suffix=".webm"):
    """Patch sync_playwright with a stub that records calls and produces a fake video."""
    if raw_detect is None:
        raw_detect = {
            "libs": {"gsap": True, "lenis": False, "three": True},
            "keyframes_count": 5,
            "has_smooth_scroll_attr": True,
        }

    # Pre-create a fake video file Playwright "would have written" inside a
    # temp location; .video.path() will return its location.
    fake_video = tmp_path / f"fake-video{video_suffix}"
    fake_video.write_bytes(b"FAKE")

    page = MagicMock()
    page.goto = MagicMock()
    page.wait_for_timeout = MagicMock()
    page.evaluate = MagicMock(return_value=raw_detect)
    page.screenshot = MagicMock(
        side_effect=lambda path, **kw: Path(path).write_bytes(b"JPG")
    )
    page.close = MagicMock()
    video_mock = MagicMock()
    video_mock.path = MagicMock(return_value=str(fake_video))
    page.video = video_mock

    context = MagicMock()
    context.new_page = MagicMock(return_value=page)
    context.close = MagicMock()

    browser = MagicMock()
    browser.new_context = MagicMock(return_value=context)
    browser.close = MagicMock()

    chromium = MagicMock()
    chromium.launch = MagicMock(return_value=browser)

    pw_obj = MagicMock()
    pw_obj.chromium = chromium

    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=pw_obj)
    cm.__exit__ = MagicMock(return_value=False)

    sync_playwright = MagicMock(return_value=cm)
    monkeypatch.setattr(_capture, "_import_playwright", lambda: sync_playwright)
    return {
        "page": page,
        "context": context,
        "browser": browser,
        "fake_video": fake_video,
    }


def test_capture_url_happy_path_writes_artifacts(monkeypatch, tmp_path):
    stubs = _make_fake_playwright(monkeypatch, tmp_path)
    result = capture_url(
        url="https://example.com",
        slug="example",
        source="awwwards",
        artifact_root=str(tmp_path / "refs"),
        scroll_seconds=2,
        viewport=(1280, 720),
        timeout_ms=10000,
    )

    artifact_dir = tmp_path / "refs" / "awwwards" / "example"
    assert artifact_dir.exists()
    meta_path = artifact_dir / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())

    assert meta["url"] == "https://example.com"
    assert meta["source"] == "awwwards"
    assert meta["libs_detected"] == ["gsap", "three"]
    assert meta["keyframes_count"] == 5
    assert meta["has_smooth_scroll_attr"] is True
    assert meta["has_animation"] is True
    assert meta["viewport"] == [1280, 720]
    assert meta["error"] is None
    assert meta["thumbnail_filename"] == "thumbnail.jpg"
    assert meta["video_filename"] == "preview.webm"

    # Thumbnail + video moved into place
    assert (artifact_dir / "thumbnail.jpg").exists()
    assert (artifact_dir / "preview.webm").exists()
    # Original fake video moved away
    assert not stubs["fake_video"].exists()

    # Result model populated correctly
    assert isinstance(result, CaptureResult)
    assert result.libs_detected == ["gsap", "three"]
    assert result.has_animation is True
    assert result.error is None
    assert result.video_path.endswith("preview.webm")
    assert result.thumbnail_path.endswith("thumbnail.jpg")

    # Playwright surface called as expected
    stubs["page"].goto.assert_called_once()
    stubs["browser"].close.assert_called_once()


def test_capture_url_records_error_on_goto_failure(monkeypatch, tmp_path):
    stubs = _make_fake_playwright(monkeypatch, tmp_path)
    stubs["page"].goto.side_effect = RuntimeError("net::ERR_TIMED_OUT")

    result = capture_url(
        url="https://broken.example",
        slug="broken",
        source="awwwards",
        artifact_root=str(tmp_path / "refs"),
        scroll_seconds=1,
    )
    assert result.error is not None
    assert "ERR_TIMED_OUT" in result.error or "page_error" in result.error
    # Meta still written
    meta = json.loads((tmp_path / "refs" / "awwwards" / "broken" / "meta.json").read_text())
    assert meta["error"] is not None
    # No libs since detection never ran
    assert meta["libs_detected"] == []
    assert meta["has_animation"] is False
