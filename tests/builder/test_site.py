"""Tests for site assembly."""
from __future__ import annotations

import json
from pathlib import Path

from tools.builder._site import PAGE_FILENAMES, project_slug, write_site


def test_write_site_creates_all_pages_and_assets(tmp_path: Path) -> None:
    pages = {
        "landing": "<html><body>landing</body></html>",
        "services": "<html><body>services</body></html>",
        "about": "<html><body>about</body></html>",
        "contact": "<html><body>contact</body></html>",
    }
    site = tmp_path / "site"
    written = write_site(site, pages)
    assert set(written.keys()) == set(pages.keys())
    assert (site / "index.html").exists()
    assert (site / "services.html").exists()
    assert (site / "about.html").exists()
    assert (site / "contact.html").exists()
    assert (site / "assets" / "prototype.js").exists()
    assert (site / "assets" / "prototype.css").exists()
    assert (site / "vercel.json").exists()


def test_vercel_json_has_clean_urls(tmp_path: Path) -> None:
    write_site(tmp_path / "site", {"landing": "<html></html>"})
    cfg = json.loads((tmp_path / "site" / "vercel.json").read_text())
    assert cfg["cleanUrls"] is True
    assert cfg["trailingSlash"] is False


def test_page_filenames_landing_is_index() -> None:
    assert PAGE_FILENAMES["landing"] == "index.html"


def test_project_slug_basic() -> None:
    assert project_slug("Joe's Pizza", "x") == "joe-s-pizza"
    assert project_slug("Acme & Co.", "x") == "acme-co"


def test_project_slug_fallback_to_lead_id() -> None:
    assert project_slug("", "test-pizza") == "test-pizza"


def test_project_slug_truncates() -> None:
    long = "x" * 200
    assert len(project_slug(long, "x")) <= 63
