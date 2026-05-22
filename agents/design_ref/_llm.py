"""LLM wrapper for brand mood / typography synthesis. Uses tools.llm fallback chain."""
from __future__ import annotations

from typing import Any, Dict

from tools.llm import LLMUnavailable, call_llm_json


class LLMError(RuntimeError):
    """Raised when every provider in the fallback chain fails."""


_PROMPT = """You are a senior brand designer. Given the inputs below, return ONE JSON object — no prose, no markdown fences.

Schema:
{{
  "mood": "2-3 sentence brand mood description",
  "typography_block": "markdown bullet list: Display / Body / Mono with concrete font family + weight + size guidance",
  "image_direction": "1-2 sentences on lighting, composition, subject choice for stock photo selection",
  "component_patterns": ["bullet 1", "bullet 2", "..."]
}}

Inputs:
- Vertical: {vertical}
- Style keyword: {style}
- Sampled palette hexes: {palette}
- Detected animation libs in refs: {libs}
- Reference items (title — source — tags):
{refs}

Respond with JSON only.
"""


def _build_prompt(payload: Dict[str, Any]) -> str:
    refs_lines = []
    for item in payload.get("items", [])[:20]:
        title = item.get("title") or "(untitled)"
        tags = ",".join(item.get("tags") or [])
        refs_lines.append(f"  - {title} — {item.get('source')} — [{tags}]")
    return _PROMPT.format(
        vertical=payload.get("vertical"),
        style=payload.get("style"),
        palette=", ".join(payload.get("palette") or []) or "(none extracted)",
        libs=", ".join(payload.get("libs") or []) or "(none)",
        refs="\n".join(refs_lines) or "  (no refs supplied)",
    )


def synthesize_design_notes(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run design synthesis through the LLM fallback chain.

    Raises LLMError when every provider fails (and manual is disabled).
    """
    prompt = _build_prompt(payload)
    try:
        return call_llm_json(prompt)
    except LLMUnavailable as exc:
        raise LLMError(str(exc)) from exc
