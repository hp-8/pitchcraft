"""Tests for tools.scrapers.twentyfirst."""
from __future__ import annotations

import importlib

import pytest

from tools.scrapers import _cache, twentyfirst
from tools.scrapers._models import ScraperResult

LIST_HTML = """
<a href="/components/hero-one"><img src="https://cdn/1.png" /></a>
<a href="/components/card-grid"><img src="https://cdn/2.png" /></a>
"""

DETAIL_HTML = """
<pre class="language-tsx">export const Hero = () =&gt; &lt;div&gt;hi&lt;/div&gt;;</pre>
"""


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", tmp_path / "db.sqlite")
    importlib.reload(twentyfirst)


def _stub_factory(list_html, detail_html):
    def _f(url):
        if url.endswith("/components") or "?q=" in url:
            return list_html
        return detail_html
    return _f


def test_happy(monkeypatch, tmp_path):
    monkeypatch.setattr(twentyfirst, "_fetch", _stub_factory(LIST_HTML, DETAIL_HTML))
    r = twentyfirst.fetch_twentyfirst(
        query="", limit=5, use_cache=False, artifact_root=tmp_path
    )
    assert len(r.items) == 2
    assert r.items[0].components_tsx_path is not None
    assert r.items[0].image_url == "https://cdn/1.png"


def test_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(twentyfirst, "_fetch", lambda u: None)
    r = twentyfirst.fetch_twentyfirst(query="z", limit=5, use_cache=False, artifact_root=tmp_path)
    assert r.items == []


def test_cache(monkeypatch, tmp_path):
    calls = {"n": 0}

    def _s(u):
        calls["n"] += 1
        if "components" in u and "/components/" not in u:
            return LIST_HTML
        return DETAIL_HTML

    monkeypatch.setattr(twentyfirst, "_fetch", _s)
    twentyfirst.fetch_twentyfirst(query="c", limit=2, use_cache=True, artifact_root=tmp_path)
    n = calls["n"]
    twentyfirst.fetch_twentyfirst(query="c", limit=2, use_cache=True, artifact_root=tmp_path)
    assert calls["n"] == n


def test_schema(monkeypatch, tmp_path):
    monkeypatch.setattr(twentyfirst, "_fetch", _stub_factory(LIST_HTML, DETAIL_HTML))
    r = twentyfirst.fetch_twentyfirst(query="", limit=1, use_cache=False, artifact_root=tmp_path)
    ScraperResult.model_validate(r.model_dump())
