"""Tests for tools.scrapers.codrops."""
from __future__ import annotations

import importlib

import pytest
import requests_mock

from tools.scrapers import _cache, codrops
from tools.scrapers._models import ScraperResult

SAMPLE = [
    {
        "id": 1,
        "link": "https://tympanus.net/codrops/post-1/",
        "title": {"rendered": "Scroll Animation Demo"},
        "_embedded": {
            "wp:featuredmedia": [{"source_url": "https://example.com/img1.jpg"}],
            "wp:term": [[{"name": "Tutorial"}, {"name": "Animation"}]],
        },
        "content": {
            "rendered": '<p>see <a href="https://github.com/codrops/Demo1">code</a></p>'
        },
    },
    {
        "id": 2,
        "link": "https://tympanus.net/codrops/post-2/",
        "title": {"rendered": "Another"},
        "_embedded": {"wp:featuredmedia": [{"source_url": "https://example.com/img2.jpg"}]},
        "content": {"rendered": "<p>no repo</p>"},
    },
]


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", tmp_path / "db.sqlite")
    importlib.reload(codrops)


def test_happy_path():
    with requests_mock.Mocker() as m:
        m.get(codrops.API_URL, json=SAMPLE, status_code=200)
        result = codrops.fetch_codrops(query="animation", limit=5, use_cache=False)
    assert isinstance(result, ScraperResult)
    assert result.source == "codrops"
    assert len(result.items) == 2
    first = result.items[0]
    assert first.id == "codrops_1"
    assert first.image_url == "https://example.com/img1.jpg"
    assert first.has_animation is True
    assert any(t.startswith("repo:") for t in first.tags)
    assert "Tutorial" in first.tags


def test_empty_or_error_returns_empty():
    with requests_mock.Mocker() as m:
        m.get(codrops.API_URL, status_code=500, text="boom")
        result = codrops.fetch_codrops(query="x", limit=5, use_cache=False)
    assert result.items == []


def test_cache_hit():
    with requests_mock.Mocker() as m:
        m.get(codrops.API_URL, json=SAMPLE, status_code=200)
        codrops.fetch_codrops(query="c", limit=5, use_cache=True)
        codrops.fetch_codrops(query="c", limit=5, use_cache=True)
        assert m.call_count == 1


def test_schema_validates():
    with requests_mock.Mocker() as m:
        m.get(codrops.API_URL, json=SAMPLE, status_code=200)
        result = codrops.fetch_codrops(query="s", limit=5, use_cache=False)
    ScraperResult.model_validate(result.model_dump())
