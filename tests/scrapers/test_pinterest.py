"""Tests for tools.scrapers.pinterest."""
from __future__ import annotations

import importlib

import pytest

from tools.scrapers import _cache, pinterest
from tools.scrapers._models import ScraperResult

HTML = """
<a href="/pin/12345/"><img src="https://i.pinimg.com/1.jpg" alt="hero ideas" /></a>
<a href="/pin/67890/"><img src="https://i.pinimg.com/2.jpg" alt="navbar inspo" /></a>
"""


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", tmp_path / "db.sqlite")
    importlib.reload(pinterest)


def test_happy(monkeypatch):
    monkeypatch.setattr(pinterest, "_stealth_get", lambda u: HTML)
    r = pinterest.fetch_pinterest(query="hero", limit=5, use_cache=False)
    assert len(r.items) == 2
    assert r.items[0].id == "pinterest_12345"
    assert r.items[0].image_url == "https://i.pinimg.com/1.jpg"


def test_empty(monkeypatch):
    monkeypatch.setattr(pinterest, "_stealth_get", lambda u: None)
    r = pinterest.fetch_pinterest(query="z", limit=5, use_cache=False)
    assert r.items == []


def test_cache(monkeypatch):
    calls = {"n": 0}

    def _s(u):
        calls["n"] += 1
        return HTML

    monkeypatch.setattr(pinterest, "_stealth_get", _s)
    pinterest.fetch_pinterest(query="c", limit=5, use_cache=True)
    pinterest.fetch_pinterest(query="c", limit=5, use_cache=True)
    assert calls["n"] == 1


def test_schema(monkeypatch):
    monkeypatch.setattr(pinterest, "_stealth_get", lambda u: HTML)
    r = pinterest.fetch_pinterest(query="s", limit=5, use_cache=False)
    ScraperResult.model_validate(r.model_dump())
