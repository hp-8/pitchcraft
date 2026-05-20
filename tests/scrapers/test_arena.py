"""Tests for tools.scrapers.arena."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import requests_mock

from tools.scrapers import _cache, arena
from tools.scrapers._models import ScraperResult

SAMPLE_RESPONSE = {
    "blocks": [
        {
            "id": 12345,
            "title": "Cool restaurant hero",
            "class": "Image",
            "image": {
                "original": {"url": "https://d2w9rnfcy7mm78.cloudfront.net/orig.jpg"},
                "thumb": {"url": "https://d2w9rnfcy7mm78.cloudfront.net/thumb.jpg"},
            },
            "connections": [{"title": "Modern restaurants"}],
        },
        {
            "id": 67890,
            "title": "Just text",
            "class": "Text",
            "image": None,
        },
        {
            "id": 11111,
            "title": "Link block",
            "class": "Link",
            "image": {"large": {"url": "https://example.com/large.jpg"}},
        },
    ]
}


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """Point the shared cache + arena at a temp SQLite file per test."""
    db = tmp_path / "scrapers.db"
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", db)
    monkeypatch.setenv("ARENA_ACCESS_TOKEN", "test-token-123")
    # Reload arena so it sees patched cache default if it captured it.
    importlib.reload(arena)
    yield db


def test_fetch_arena_happy_path(_isolated_cache):
    with requests_mock.Mocker() as m:
        m.get(arena.API_URL, json=SAMPLE_RESPONSE, status_code=200)
        result = arena.fetch_arena(query="restaurant", limit=5, use_cache=False)

    assert isinstance(result, ScraperResult)
    assert result.source == "arena"
    assert result.query == "restaurant"
    # Text block with no image filtered out.
    assert len(result.items) == 2
    ids = {item.id for item in result.items}
    assert ids == {"arena_12345", "arena_11111"}
    first = next(i for i in result.items if i.id == "arena_12345")
    assert first.image_url.endswith("orig.jpg")
    assert first.url == "https://www.are.na/block/12345"
    assert first.channel == "Modern restaurants"
    assert first.source == "arena"


def test_cache_hit_skips_http(_isolated_cache):
    with requests_mock.Mocker() as m:
        m.get(arena.API_URL, json=SAMPLE_RESPONSE, status_code=200)
        first = arena.fetch_arena(query="cached", limit=5, use_cache=True)
        assert m.call_count == 1

        second = arena.fetch_arena(query="cached", limit=5, use_cache=True)
        # No additional HTTP call -> served from cache.
        assert m.call_count == 1

    assert first.fetched_at == second.fetched_at
    assert [i.id for i in first.items] == [i.id for i in second.items]


def test_no_cache_flag_forces_refetch(_isolated_cache):
    with requests_mock.Mocker() as m:
        m.get(arena.API_URL, json=SAMPLE_RESPONSE, status_code=200)
        arena.fetch_arena(query="x", limit=3, use_cache=True)
        arena.fetch_arena(query="x", limit=3, use_cache=False)
        assert m.call_count == 2


def test_api_error_401(_isolated_cache):
    with requests_mock.Mocker() as m:
        m.get(arena.API_URL, status_code=401, text="Unauthorized")
        with pytest.raises(arena.ArenaAPIError) as exc:
            arena.fetch_arena(query="boom", limit=5, use_cache=False)
    assert "401" in str(exc.value)
    assert "Unauthorized" in str(exc.value)


def test_api_error_500(_isolated_cache):
    with requests_mock.Mocker() as m:
        m.get(arena.API_URL, status_code=500, text="server died")
        with pytest.raises(arena.ArenaAPIError) as exc:
            arena.fetch_arena(query="boom", limit=5, use_cache=False)
    assert "500" in str(exc.value)


def test_missing_token_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", tmp_path / "db.sqlite")
    monkeypatch.delenv("ARENA_ACCESS_TOKEN", raising=False)
    # Prevent .env from repopulating the var.
    monkeypatch.setattr(arena, "load_dotenv", lambda *a, **kw: None)
    with pytest.raises(RuntimeError) as exc:
        arena.fetch_arena(query="x", limit=2, use_cache=False)
    assert "ARENA_ACCESS_TOKEN" in str(exc.value)


def test_result_schema_serializable(_isolated_cache):
    with requests_mock.Mocker() as m:
        m.get(arena.API_URL, json=SAMPLE_RESPONSE, status_code=200)
        result = arena.fetch_arena(query="schema", limit=5, use_cache=False)
    dumped = result.model_dump()
    assert set(dumped.keys()) == {"source", "query", "fetched_at", "items"}
    for item in dumped["items"]:
        assert set(item.keys()) >= {
            "id", "title", "url", "image_url", "tags", "channel", "source"
        }


def test_cache_init_creates_file(tmp_path):
    db = tmp_path / "nested" / "scrapers.db"
    _cache.init_db(db)
    assert db.exists()


def test_limit_clamped_to_max(_isolated_cache):
    with requests_mock.Mocker() as m:
        m.get(arena.API_URL, json={"blocks": []}, status_code=200)
        arena.fetch_arena(query="big", limit=99999, use_cache=False)
        req = m.last_request
        assert req.qs["per"] == ["100"]


def test_isolated_cache_path_exists(_isolated_cache):
    # Sanity check that fixture wired up properly.
    assert isinstance(_isolated_cache, Path)
