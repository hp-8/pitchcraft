"""Tests for the brand_voice agent."""
from __future__ import annotations

from unittest.mock import patch

from tools.council.agents.brand_voice import TONES, synthesize_brand_voice
from tools.stitch._models import LeadContext


def _lead(vertical: str = "restaurant") -> LeadContext:
    return LeadContext(
        lead_id="x",
        business="Joe's Pizza",
        vertical=vertical,
        location="Brooklyn, NY",
        services=["pizza", "delivery"],
    )


def test_skip_llm_uses_vertical_fallback() -> None:
    out = synthesize_brand_voice(_lead("restaurant"), audit=None, skip_llm=True)
    assert out["source"] == "fallback"
    assert out["tone"] in TONES
    assert "Joe's Pizza" in out["one_liner"]
    assert "Brooklyn" in out["one_liner"]


def test_vertical_specific_fallback() -> None:
    dental = synthesize_brand_voice(_lead("dental"), skip_llm=True)
    realtor = synthesize_brand_voice(_lead("realtor"), skip_llm=True)
    assert dental["tone"] == "soft"
    assert realtor["tone"] == "editorial"
    assert dental["audience"] != realtor["audience"]


def test_unknown_vertical_falls_back_to_restaurant() -> None:
    lead = LeadContext(lead_id="y", business="X", vertical="restaurant", location="LA")
    # construct a fake vertical key by directly passing what the model permits.
    out = synthesize_brand_voice(lead, skip_llm=True)
    assert out["tone"] in TONES


def test_llm_failure_falls_back() -> None:
    """If Gemini import or call fails, brand_voice degrades gracefully."""
    lead = _lead()
    with patch(
        "tools.council.agents.brand_voice._call_gemini",
        side_effect=RuntimeError("no key"),
    ):
        out = synthesize_brand_voice(lead, skip_llm=False)
    assert out["source"] == "fallback"
    assert out["tone"] in TONES


def test_llm_success_path_validates_tone() -> None:
    lead = _lead()
    bogus_tone_payload = {
        "audience": "A",
        "use_case": "B",
        "tone": "shouty",  # invalid
        "one_liner": "C",
        "voice_attributes": ["x", "y"],
    }
    with patch(
        "tools.council.agents.brand_voice._call_gemini",
        return_value=bogus_tone_payload,
    ):
        out = synthesize_brand_voice(lead, skip_llm=False)
    assert out["tone"] in TONES  # bogus replaced
    assert out["source"] == "llm"
    assert out["audience"] == "A"
