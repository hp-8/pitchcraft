"""LLM call #2 — filter and validate the candidate keyword list.

Drops irrelevant/spammy/PII noise. Returns a clean subset suitable for
scraper queries. Falls back to top-N by score when LLM unavailable.
"""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_PROMPT = """You filter a candidate keyword list for use as search queries against
design-reference scrapers (Unsplash, Pexels, Are.na, Codrops).

For the given business + vertical + bucket tokens, return ONLY a JSON object:
{"keywords": ["...", "..."]}.

Drop keywords that are:
- Pure PII (person names, phone numbers, addresses)
- Generic chrome ("home", "menu", "footer", "subscribe", "click here")
- Irrelevant to visual design references (e.g. shipping policy terms)
- Overly verbose (>3 words)
- Hex codes, URLs, dates

KEEP keywords that are:
- Concrete category nouns relevant to the business
- Style / mood descriptors (e.g. "rustic", "modern", "minimal", "warm")
- Region / origin markers (e.g. "niagara", "tuscany")
- Materials, mediums, objects relevant to the business's product/service

Return 8-15 keywords. Lowercase. No duplicates.

INPUT:
"""


def validate(
    business: str,
    vertical: str,
    bucket_tokens: list[str],
    candidates: list[dict],
    skip_llm: bool = False,
    target_count: int = 12,
) -> list[str]:
    # Fallback: top-N by score, deduped
    fallback = []
    seen: set[str] = set()
    for c in sorted(candidates, key=lambda x: -float(x.get("score", 0)))[:target_count * 2]:
        k = (c.get("keyword") or "").strip().lower()
        if k and k not in seen:
            seen.add(k)
            fallback.append(k)
        if len(fallback) >= target_count:
            break

    if skip_llm or not candidates:
        return fallback

    from tools.llm import LLMUnavailable, call_llm_json

    payload = json.dumps({
        "business": business,
        "vertical": vertical,
        "bucket_tokens": bucket_tokens,
        "candidates": [c.get("keyword") for c in candidates[:50]],
    }, indent=2)

    try:
        data = call_llm_json(_PROMPT + payload)
        kws = data.get("keywords") or []
        out: list[str] = []
        seen2: set[str] = set()
        for k in kws:
            k = (k or "").strip().lower()
            if k and k not in seen2:
                seen2.add(k)
                out.append(k)
        if out:
            return out[:target_count + 3]
    except LLMUnavailable as exc:
        logger.warning("validate LLM unavailable: %s; using fallback", exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("validate LLM failed: %s; using fallback", exc)

    return fallback
