"""Tests for tools.audit._pagespeed."""
from __future__ import annotations

import pytest
import requests_mock

from tools.audit import _pagespeed


SAMPLE = {
    "lighthouseResult": {
        "categories": {
            "performance": {"score": 0.42},
            "seo": {"score": 0.95},
            "accessibility": {"score": 0.71},
            "best-practices": {"score": 0.83},
        },
        "audits": {
            "largest-contentful-paint": {"numericValue": 5200, "score": 0.2, "title": "LCP"},
            "cumulative-layout-shift": {"numericValue": 0.18, "score": 0.4, "title": "CLS"},
            "interaction-to-next-paint": {"numericValue": 350, "score": 0.3, "title": "INP"},
            "total-blocking-time": {"numericValue": 980, "score": 0.1, "title": "TBT"},
            "unused-css-rules": {
                "score": 0.3,
                "title": "Remove unused CSS",
                "details": {"overallSavingsMs": 1200},
            },
            "render-blocking-resources": {
                "score": 0.5,
                "title": "Eliminate render-blocking resources",
                "details": {"overallSavingsMs": 800},
            },
            "uses-text-compression": {
                "score": 0.4,
                "title": "Enable text compression",
                "details": {"overallSavingsMs": 200},
            },
            "modern-image-formats": {
                "score": 0.6,
                "title": "Serve modern image formats",
                "details": {"overallSavingsMs": 50},
            },
            "first-paint": {"score": 1.0, "title": "First paint"},
        },
    }
}


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv("PAGESPEED_API_KEY", "k")


def test_fetch_pagespeed_extracts_metrics():
    with requests_mock.Mocker() as m:
        m.get(_pagespeed.PSI_URL, json=SAMPLE, status_code=200)
        out = _pagespeed.fetch_pagespeed("https://x.com")
    assert out["performance_score"] == pytest.approx(0.42)
    assert out["seo_score"] == pytest.approx(0.95)
    assert out["lcp_ms"] == 5200
    assert out["cls"] == pytest.approx(0.18)
    assert out["inp_ms"] == 350
    assert out["tbt_ms"] == 980
    # Top 3 by savings_ms, excluding score >= 0.9.
    titles = [o["title"] for o in out["opportunities"]]
    assert titles[0] == "Remove unused CSS"
    assert "First paint" not in titles
    assert len(out["opportunities"]) == 3


def test_fetch_pagespeed_http_error_returns_dict():
    with requests_mock.Mocker() as m:
        m.get(_pagespeed.PSI_URL, status_code=500, text="kaboom")
        out = _pagespeed.fetch_pagespeed("https://x.com")
    assert "error" in out
    assert "pagespeed_http_500" in out["error"]


def test_fetch_pagespeed_missing_fields():
    with requests_mock.Mocker() as m:
        m.get(_pagespeed.PSI_URL, json={"lighthouseResult": {}}, status_code=200)
        out = _pagespeed.fetch_pagespeed("https://x.com")
    assert out["performance_score"] is None
    assert out["lcp_ms"] is None
    assert out["opportunities"] == []
