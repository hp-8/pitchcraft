"""End-to-end keyword pipeline: crawl → bucket LLM → NLP extract → validator LLM."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.keywords.bucket import classify
from tools.keywords.crawl import crawl_lead_pages
from tools.keywords.extract import extract_keywords
from tools.keywords.validate import validate

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_keywords(
    lead_id: str,
    business: str,
    vertical: str,
    site_url: str,
    lead_dir: Path,
    tagline: str | None = None,
    services: list[str] | None = None,
    max_pages: int = 3,
    skip_llm: bool = False,
    target_count: int = 12,
) -> dict[str, Any]:
    """Run the full pipeline. Returns dict with keywords + diagnostics. Writes keywords.json."""
    t0 = time.perf_counter()
    diag: dict[str, Any] = {"timings": {}, "stages": []}

    # 1) Crawl
    crawl_start = time.perf_counter()
    crawl_res = crawl_lead_pages(site_url, vertical, lead_dir, max_pages=max_pages)
    diag["timings"]["crawl_s"] = round(time.perf_counter() - crawl_start, 2)
    diag["pages_fetched"] = len(crawl_res["pages"])
    diag["chars"] = crawl_res["char_count"]
    text = crawl_res["combined_text"]
    diag["stages"].append("crawl")

    # 2) Bucket LLM
    b_start = time.perf_counter()
    bucket = classify(
        business=business, vertical=vertical, tagline=tagline,
        services=services, sample_text=text[:3000], skip_llm=skip_llm,
    )
    diag["timings"]["bucket_s"] = round(time.perf_counter() - b_start, 2)
    diag["stages"].append("bucket")

    # 3) NLP extract
    e_start = time.perf_counter()
    candidates = extract_keywords(text, bucket_tokens=bucket, top_k=40)
    diag["timings"]["extract_s"] = round(time.perf_counter() - e_start, 2)
    diag["candidate_count"] = len(candidates)
    diag["stages"].append("extract")

    # 4) Validator LLM
    v_start = time.perf_counter()
    keywords = validate(
        business=business, vertical=vertical, bucket_tokens=bucket,
        candidates=candidates, skip_llm=skip_llm, target_count=target_count,
    )
    diag["timings"]["validate_s"] = round(time.perf_counter() - v_start, 2)
    diag["stages"].append("validate")

    diag["timings"]["total_s"] = round(time.perf_counter() - t0, 2)

    result = {
        "lead_id": lead_id,
        "business": business,
        "vertical": vertical,
        "site_url": site_url,
        "generated_at": _now(),
        "bucket_tokens": bucket,
        "candidate_count": len(candidates),
        "candidates": candidates[:50],
        "keywords": keywords,
        "diagnostics": diag,
    }

    out_path = lead_dir / "keywords.json"
    lead_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
