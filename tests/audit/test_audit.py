"""End-to-end test for tools.audit.audit (all external calls mocked)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.audit import audit as audit_mod
from tools.audit._models import AuditResult


@pytest.fixture
def mocked_externals(monkeypatch, tmp_path):
    def fake_firecrawl(url, screenshot_dest=None):
        if screenshot_dest is not None:
            Path(screenshot_dest).parent.mkdir(parents=True, exist_ok=True)
            Path(screenshot_dest).write_bytes(b"PNG")
        return {
            "markdown": "Joe's Pizza menu, reservation",
            "html": "<html><head><meta name='viewport' content='width=device-width'></head>"
                    "<body><h1>Joe</h1><a>Book</a><p>(212) 555-1212</p>"
                    "<p>123 Main Street</p><p>5 stars</p></body></html>",
            "screenshot_url": "https://cdn/x.png",
            "screenshot_path": str(screenshot_dest) if screenshot_dest else None,
            "metadata": {"title": "Joe"},
        }

    def fake_pagespeed(url, strategy="mobile"):
        return {
            "performance_score": 0.55,
            "seo_score": 0.9,
            "accessibility_score": 0.8,
            "best_practices_score": 0.85,
            "lcp_ms": 2200,
            "cls": 0.05,
            "inp_ms": 180,
            "tbt_ms": 200,
            "opportunities": [{"id": "x", "title": "t", "score": 0.5, "savings_ms": 100}],
        }

    monkeypatch.setattr(audit_mod, "fetch_firecrawl", fake_firecrawl)
    monkeypatch.setattr(audit_mod, "fetch_pagespeed", fake_pagespeed)
    return tmp_path


def test_audit_end_to_end(mocked_externals):
    out_dir = mocked_externals / "outputs"
    result = audit_mod.audit(
        url="https://joespizza.com/",
        vertical="restaurant",
        out_dir=out_dir,
    )
    assert isinstance(result, AuditResult)
    assert result.url == "https://joespizza.com/"
    assert result.vertical == "restaurant"
    assert result.slug
    assert result.pagespeed is not None
    assert result.pagespeed.lcp_ms == 2200
    assert result.firecrawl_error is None
    assert result.pagespeed_error is None
    # File written
    out_file = out_dir / result.slug / "audit.json"
    assert out_file.exists()
    payload = json.loads(out_file.read_text())
    assert payload["url"] == "https://joespizza.com/"
    # Screenshot saved
    shot = out_dir / result.slug / "screenshot.png"
    assert shot.exists()
    assert result.screenshot_path == str(shot)


def test_audit_propagates_firecrawl_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        audit_mod, "fetch_firecrawl", lambda url, screenshot_dest=None: {"error": "boom"}
    )
    monkeypatch.setattr(
        audit_mod, "fetch_pagespeed", lambda url, strategy="mobile": {"error": "nope"}
    )
    result = audit_mod.audit("https://x.com", "dental", out_dir=tmp_path)
    assert result.firecrawl_error == "boom"
    assert result.pagespeed_error == "nope"
    assert result.pagespeed is None
    # Still writes audit.json even on errors
    assert (tmp_path / result.slug / "audit.json").exists()


def test_audit_rejects_bad_vertical(tmp_path):
    with pytest.raises(ValueError):
        audit_mod.audit("https://x.com", "bakery", out_dir=tmp_path)
