"""Tests for tools.scrapers.r3f_examples."""
from __future__ import annotations

import importlib

import pytest
import requests_mock

from tools.scrapers import _cache, r3f_examples
from tools.scrapers._models import ScraperResult

HTML = """
<a href="https://codesandbox.io/s/r3f-suspense-abc123">Suspense demo</a>
<a href="https://codesandbox.io/p/sandbox/cool-shader-xyz789">Shader cool</a>
"""


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", tmp_path / "db.sqlite")
    importlib.reload(r3f_examples)


def test_happy():
    with requests_mock.Mocker() as m:
        m.get(r3f_examples.EXAMPLES_URL, text=HTML, status_code=200)
        r = r3f_examples.fetch_r3f_examples(query="", limit=10, use_cache=False)
    assert len(r.items) >= 1
    first = r.items[0]
    assert "three" in first.libs_detected
    assert first.image_url.startswith("https://codesandbox.io/api/v1/sandboxes/")


def test_empty():
    with requests_mock.Mocker() as m:
        m.get(r3f_examples.EXAMPLES_URL, status_code=500, text="boom")
        r = r3f_examples.fetch_r3f_examples(query="z", limit=5, use_cache=False)
    assert r.items == []


def test_cache():
    with requests_mock.Mocker() as m:
        m.get(r3f_examples.EXAMPLES_URL, text=HTML, status_code=200)
        r3f_examples.fetch_r3f_examples(query="c", limit=2, use_cache=True)
        r3f_examples.fetch_r3f_examples(query="c", limit=2, use_cache=True)
        assert m.call_count == 1


def test_schema():
    with requests_mock.Mocker() as m:
        m.get(r3f_examples.EXAMPLES_URL, text=HTML, status_code=200)
        r = r3f_examples.fetch_r3f_examples(query="", limit=1, use_cache=False)
    ScraperResult.model_validate(r.model_dump())
