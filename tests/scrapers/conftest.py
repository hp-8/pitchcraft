"""Shared test fixtures for scraper tests."""
from __future__ import annotations

import pytest

from tools.scrapers import _cache


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    db = tmp_path / "scrapers.db"
    monkeypatch.setattr(_cache, "DEFAULT_DB_PATH", db)
    return db


class StubResp:
    def __init__(self, html: str = "", text: str | None = None):
        self.html_content = html
        self.text = text if text is not None else html
        self.status = 200
        self.content = html.encode("utf-8")


@pytest.fixture
def stub_resp():
    return StubResp
