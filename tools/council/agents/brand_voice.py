"""Brand voice agent — synthesizes audience/tone/one-liner.

Single optional Gemini Flash call; deterministic fallback when `skip_llm=True`
or when Gemini is unavailable.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from tools.audit._models import AuditResult
from tools.stitch._models import LeadContext

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.0-flash-exp"

# Hallmark tone vocabulary (mirrors hallmark voice register).
TONES = {"editorial", "brutalist", "soft", "utilitarian", "luxury", "playful", "technical", "austere"}

# Deterministic per-vertical fallback so brief is reproducible without LLM.
_VERTICAL_DEFAULTS: dict[str, dict[str, Any]] = {
    "restaurant": {
        "audience": "Diners within 15 minutes of the storefront looking for a memorable but unfussy meal.",
        "use_case": "Browse the menu, check hours, reserve a table, find the address.",
        "tone": "editorial",
        "voice_attributes": ["warm", "specific", "place-rooted"],
        "one_liner_template": "{business} — a {location_short} kitchen built on {first_service}.",
    },
    "dental": {
        "audience": "Adults choosing a long-term family or cosmetic dentist within their zip code.",
        "use_case": "Verify credentials, book a first appointment, understand pricing and insurance.",
        "tone": "soft",
        "voice_attributes": ["calm", "credible", "specific"],
        "one_liner_template": "{business} — {location_short} dentistry that respects your time.",
    },
    "realtor": {
        "audience": "Buyers and sellers researching local agents before a 30-minute consult.",
        "use_case": "Browse listings, read past sales, request a market estimate.",
        "tone": "editorial",
        "voice_attributes": ["confident", "data-led", "neighborhood-fluent"],
        "one_liner_template": "{business} — {location_short} real estate, sold honestly.",
    },
    "fnb": {
        "audience": "Wholesale and retail buyers comparing small-batch food and beverage suppliers.",
        "use_case": "Skim provenance, sample range, order or request a wholesale price sheet.",
        "tone": "editorial",
        "voice_attributes": ["crafted", "honest", "production-led"],
        "one_liner_template": "{business} — small-batch from {location_short}.",
    },
}


def _fallback(lead: LeadContext) -> dict[str, Any]:
    defaults = _VERTICAL_DEFAULTS.get(lead.vertical, _VERTICAL_DEFAULTS["restaurant"])
    location_short = (lead.location or "your city").split(",")[0]
    first_service = lead.services[0] if lead.services else "what we do"
    one_liner = defaults["one_liner_template"].format(
        business=lead.business,
        location_short=location_short,
        first_service=first_service,
    )
    return {
        "audience": defaults["audience"],
        "use_case": defaults["use_case"],
        "tone": defaults["tone"],
        "one_liner": one_liner,
        "voice_attributes": list(defaults["voice_attributes"]),
        "source": "fallback",
    }


_PROMPT = """You are a senior brand strategist. Return ONE JSON object — no prose, no fences.

Schema:
{{
  "audience": "1 sentence — who exactly visits this site",
  "use_case": "1 sentence — what they came to do",
  "tone": "ONE WORD from this set: editorial, brutalist, soft, utilitarian, luxury, playful, technical, austere",
  "one_liner": "12 words max, no superlatives, no fabricated metrics",
  "voice_attributes": ["3 short attributes"]
}}

Inputs:
- Business: {business}
- Vertical: {vertical}
- Location: {location}
- Services: {services}
- Audit problems: {problems}

Respond with JSON only.
"""


def _call_gemini(lead: LeadContext, audit: AuditResult | None) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing")
    import google.generativeai as genai  # type: ignore[import-untyped]

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = _PROMPT.format(
        business=lead.business,
        vertical=lead.vertical,
        location=lead.location or "(unspecified)",
        services=", ".join(lead.services) or "(unspecified)",
        problems=", ".join(p.code for p in (audit.problems if audit else [])) or "(none)",
    )
    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
        text = text.strip("`").strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise RuntimeError("Gemini returned non-object JSON")
    return data


def synthesize_brand_voice(
    lead: LeadContext,
    audit: AuditResult | None = None,
    skip_llm: bool = False,
) -> dict[str, Any]:
    """Produce {audience, use_case, tone, one_liner, voice_attributes}.

    Deterministic when skip_llm=True or when Gemini fails.
    """
    if skip_llm:
        return _fallback(lead)
    try:
        data = _call_gemini(lead, audit)
    except Exception as exc:
        logger.info("brand_voice LLM unavailable, using fallback: %s", exc)
        return _fallback(lead)

    fb = _fallback(lead)
    tone = str(data.get("tone") or fb["tone"]).strip().lower()
    if tone not in TONES:
        tone = fb["tone"]
    attrs = data.get("voice_attributes")
    if not isinstance(attrs, list):
        attrs = fb["voice_attributes"]
    return {
        "audience": str(data.get("audience") or fb["audience"]),
        "use_case": str(data.get("use_case") or fb["use_case"]),
        "tone": tone,
        "one_liner": str(data.get("one_liner") or fb["one_liner"]),
        "voice_attributes": [str(a) for a in attrs][:5],
        "source": "llm",
    }
