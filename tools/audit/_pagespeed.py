"""PageSpeed Insights API wrapper.

Returns dict (never raises). Extracts Core Web Vitals + Lighthouse scores
+ top opportunities.
"""
from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
CATEGORIES = ["performance", "seo", "accessibility", "best-practices"]


def _get_key() -> str:
    load_dotenv()
    key = os.getenv("PAGESPEED_API_KEY")
    if not key:
        raise RuntimeError("PAGESPEED_API_KEY missing in env.")
    return key


def _audit_ms(audit: dict[str, Any], key: str = "numericValue") -> int | None:
    val = audit.get(key)
    if val is None:
        return None
    try:
        return int(round(float(val)))
    except (TypeError, ValueError):
        return None


def _audit_float(audit: dict[str, Any], key: str = "numericValue") -> float | None:
    val = audit.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _category_score(categories: dict[str, Any], name: str) -> float | None:
    cat = categories.get(name) or {}
    score = cat.get("score")
    if score is None:
        return None
    try:
        return float(score)
    except (TypeError, ValueError):
        return None


def _top_opportunities(audits: dict[str, Any], n: int = 3) -> list[dict[str, Any]]:
    opps: list[dict[str, Any]] = []
    for aid, a in audits.items():
        if not isinstance(a, dict):
            continue
        score = a.get("score")
        if score is None or score >= 0.9:
            continue
        details = a.get("details") or {}
        savings = details.get("overallSavingsMs") or 0
        opps.append(
            {
                "id": aid,
                "title": a.get("title"),
                "score": score,
                "savings_ms": int(savings) if isinstance(savings, (int, float)) else 0,
            }
        )
    opps.sort(key=lambda o: o["savings_ms"], reverse=True)
    return opps[:n]


def fetch_pagespeed(url: str, strategy: str = "mobile") -> dict[str, Any]:
    """Call PSI v5 and extract summary metrics. Returns {} on success, {error} on failure."""
    try:
        key = _get_key()
        params = [("url", url), ("strategy", strategy), ("key", key)]
        for cat in CATEGORIES:
            params.append(("category", cat))
        resp = requests.get(PSI_URL, params=params, timeout=60)
        if resp.status_code != 200:
            return {"error": f"pagespeed_http_{resp.status_code}: {resp.text[:200]}"}
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 — defensive boundary
        return {"error": f"pagespeed_failed: {exc}"}

    lighthouse = data.get("lighthouseResult") or {}
    audits = lighthouse.get("audits") or {}
    categories = lighthouse.get("categories") or {}

    lcp = audits.get("largest-contentful-paint") or {}
    cls_audit = audits.get("cumulative-layout-shift") or {}
    inp = audits.get("interaction-to-next-paint") or audits.get("experimental-interaction-to-next-paint") or {}
    fid = audits.get("max-potential-fid") or {}
    tbt = audits.get("total-blocking-time") or {}

    return {
        "performance_score": _category_score(categories, "performance"),
        "seo_score": _category_score(categories, "seo"),
        "accessibility_score": _category_score(categories, "accessibility"),
        "best_practices_score": _category_score(categories, "best-practices"),
        "lcp_ms": _audit_ms(lcp),
        "cls": _audit_float(cls_audit),
        "inp_ms": _audit_ms(inp) if inp else _audit_ms(fid),
        "tbt_ms": _audit_ms(tbt),
        "opportunities": _top_opportunities(audits, n=3),
    }
