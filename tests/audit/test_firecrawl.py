"""Tests for tools.audit._firecrawl."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import requests_mock

from tools.audit import _firecrawl


class FakeDoc:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def model_dump(self):
        return {
            "markdown": self.markdown,
            "html": self.html,
            "screenshot": self.screenshot,
            "metadata": getattr(self, "metadata", {}),
        }


def test_fetch_firecrawl_happy(monkeypatch, tmp_path):
    fake = FakeDoc(
        markdown="# Hello",
        html="<html><h1>Hello</h1></html>",
        screenshot="https://cdn.example.com/shot.png",
        metadata={"title": "Hello"},
    )
    client = MagicMock()
    client.scrape.return_value = fake
    monkeypatch.setattr(_firecrawl, "_get_client", lambda: client)

    dest = tmp_path / "shot.png"
    with requests_mock.Mocker() as m:
        m.get("https://cdn.example.com/shot.png", content=b"PNGDATA", status_code=200)
        out = _firecrawl.fetch_firecrawl("https://x.com", screenshot_dest=dest)

    assert out["markdown"] == "# Hello"
    assert "<h1>" in out["html"]
    assert out["screenshot_url"] == "https://cdn.example.com/shot.png"
    assert out["screenshot_path"] == str(dest)
    assert dest.read_bytes() == b"PNGDATA"
    assert out["metadata"] == {"title": "Hello"}


def test_fetch_firecrawl_error_returns_dict(monkeypatch, tmp_path):
    def boom():
        raise RuntimeError("nope")

    monkeypatch.setattr(_firecrawl, "_get_client", boom)
    out = _firecrawl.fetch_firecrawl("https://x.com", screenshot_dest=tmp_path / "x.png")
    assert "error" in out
    assert "firecrawl_scrape_failed" in out["error"]


def test_fetch_firecrawl_screenshot_download_failure(monkeypatch, tmp_path):
    fake = FakeDoc(markdown="m", html="h", screenshot="https://cdn.example.com/x.png", metadata={})
    client = MagicMock()
    client.scrape.return_value = fake
    monkeypatch.setattr(_firecrawl, "_get_client", lambda: client)

    dest = tmp_path / "x.png"
    with requests_mock.Mocker() as m:
        m.get("https://cdn.example.com/x.png", status_code=500, text="boom")
        out = _firecrawl.fetch_firecrawl("https://x.com", screenshot_dest=dest)
    assert out["screenshot_path"] is None
    assert out["screenshot_url"] == "https://cdn.example.com/x.png"
    assert not Path(dest).exists()
