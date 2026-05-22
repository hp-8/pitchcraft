"""LLM call #1 — bucket classifier.

Given (business, vertical, tagline, services, sampled site text), returns 3-5
sub-vertical / niche tokens that anchor keyword extraction downstream.

Deterministic fallback when Gemini unavailable.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Vertical → fallback bucket tokens.
_FALLBACK_BUCKETS: dict[str, list[str]] = {
    "fnb": ["wine", "winery", "vineyard", "hospitality", "cellar"],
    "restaurant": ["restaurant", "hospitality", "menu", "dining"],
    "dental": ["dental clinic", "healthcare", "wellness", "medical"],
    "realtor": ["real estate", "property", "architecture", "interior"],
}

_PROMPT = """You classify a small local-business lead into a specific niche bucket
for keyword search downstream. Return ONLY a JSON object: {"bucket_tokens": ["...", "..."]}.

Constraints:
- 3-5 tokens total
- Each token is 1-3 words, lowercase, no punctuation
- Tokens should be SPECIFIC enough to disambiguate (e.g. "wine importer" not just "business")
- No competitor brand names, no superlatives ("best", "premium", "luxury"), no PII
- Prefer concrete category nouns + region/specialization markers

INPUT:
"""


def classify(
    business: str,
    vertical: str,
    tagline: str | None = None,
    services: list[str] | None = None,
    sample_text: str | None = None,
    skip_llm: bool = False,
) -> list[str]:
    if skip_llm:
        return _FALLBACK_BUCKETS.get(vertical.lower(), [vertical])

    from tools.llm import LLMUnavailable, call_llm_json

    payload = json.dumps({
        "business": business,
        "vertical": vertical,
        "tagline": tagline,
        "services": services or [],
        "sample_text": (sample_text or "")[:2000],
    }, indent=2)

    try:
        data = call_llm_json(_PROMPT + payload)
        tokens = data.get("bucket_tokens") or []
        clean: list[str] = []
        for t in tokens:
            t = (t or "").strip().lower()
            if t and t not in clean:
                clean.append(t)
        if clean:
            return clean[:5]
    except LLMUnavailable as exc:
        logger.warning("bucket LLM unavailable: %s; using fallback", exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("bucket LLM failed: %s; using fallback", exc)

    return _FALLBACK_BUCKETS.get(vertical.lower(), [vertical])
