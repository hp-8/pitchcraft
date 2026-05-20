"""Tests for tools.scrapers.cosmos."""
from __future__ import annotations

import importlib

import pytest

from tools.scrapers import _cache, cosmos
from tools.scrapers._models import ScraperResult

HTML = """
<a href="/e/abc-123"><img src="https://cdn.cosmos/1.jpg" alt="Card one" /></a>
<a href="/e/def-456"><img src="https://cdn.cosmos/2.jpg" alt="Card two" /></a>
<a href="/e/abc-123"><img src="https://cdn.cosmos/1.jpg" alt="dup" /></a>
"""


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", tmp_path / "db.sqlite")
    importlib.reload(cosmos)


def test_happy_path(monkeypatch):
    monkeypatch.setattr(cosmos, "_stealth_get", lambda url: HTML)
    r = cosmos.fetch_cosmos(query="x", limit=10, use_cache=False)
    assert len(r.items) == 2
    assert r.items[0].image_url == "https://cdn.cosmos/1.jpg"
    assert r.items[0].title == "Card one"


def test_empty_when_blocked(monkeypatch):
    monkeypatch.setattr(cosmos, "_stealth_get", lambda url: None)
    r = cosmos.fetch_cosmos(query="z", limit=5, use_cache=False)
    assert r.items == []


def test_cache_hit(monkeypatch):
    calls = {"n": 0}

    def _stub(url):
        calls["n"] += 1
        return HTML

    monkeypatch.setattr(cosmos, "_stealth_get", _stub)
    cosmos.fetch_cosmos(query="c", limit=5, use_cache=True)
    cosmos.fetch_cosmos(query="c", limit=5, use_cache=True)
    assert calls["n"] == 1


def test_schema(monkeypatch):
    monkeypatch.setattr(cosmos, "_stealth_get", lambda url: HTML)
    r = cosmos.fetch_cosmos(query="s", limit=5, use_cache=False)
    ScraperResult.model_validate(r.model_dump())
