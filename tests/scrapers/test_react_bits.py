"""Tests for tools.scrapers.react_bits."""
from __future__ import annotations

import importlib

import pytest
import requests_mock

from tools.scrapers import _cache, react_bits
from tools.scrapers._models import ScraperResult

HTML = """
<a href="/default/TextAnimations/SplitText"><img src="https://cdn/split.png" /></a>
<a href="/default/Components/Carousel"><img src="https://cdn/carousel.png" /></a>
"""


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", tmp_path / "db.sqlite")
    importlib.reload(react_bits)


def test_happy(monkeypatch, tmp_path):
    monkeypatch.setattr(react_bits, "_fetch_site", lambda u: HTML)
    with requests_mock.Mocker() as m:
        # First candidate URL for SplitText returns 200; first for Carousel returns 200 too.
        m.get(requests_mock.ANY, text="export const X = () => null;", status_code=200)
        r = react_bits.fetch_react_bits(
            query="", limit=5, use_cache=False, artifact_root=tmp_path
        )
    assert len(r.items) == 2
    assert all(it.components_tsx_path for it in r.items)
    assert "framer-motion" in r.items[0].libs_detected


def test_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(react_bits, "_fetch_site", lambda u: "")
    r = react_bits.fetch_react_bits(query="x", limit=5, use_cache=False, artifact_root=tmp_path)
    assert r.items == []


def test_cache(monkeypatch, tmp_path):
    calls = {"n": 0}

    def _s(u):
        calls["n"] += 1
        return HTML

    monkeypatch.setattr(react_bits, "_fetch_site", _s)
    with requests_mock.Mocker() as m:
        m.get(requests_mock.ANY, text="x", status_code=404)
        react_bits.fetch_react_bits(query="c", limit=2, use_cache=True, artifact_root=tmp_path)
        n = calls["n"]
        react_bits.fetch_react_bits(query="c", limit=2, use_cache=True, artifact_root=tmp_path)
    assert calls["n"] == n


def test_schema(monkeypatch, tmp_path):
    monkeypatch.setattr(react_bits, "_fetch_site", lambda u: HTML)
    with requests_mock.Mocker() as m:
        m.get(requests_mock.ANY, status_code=404)
        r = react_bits.fetch_react_bits(query="", limit=1, use_cache=False, artifact_root=tmp_path)
    ScraperResult.model_validate(r.model_dump())
