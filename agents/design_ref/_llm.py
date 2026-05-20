"""Gemini wrapper — single shot synthesis of brand mood, typography, etc."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

GEMINI_MODEL = "gemini-2.0-flash-exp"


class LLMError(RuntimeError):
    """Raised when the LLM call fails or returns unparseable output."""


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
    """Call Gemini and return parsed JSON dict.

    Raises LLMError on missing key, network failure, or unparseable response.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise LLMError("GEMINI_API_KEY missing. Set in .env or pass --skip-llm.")

    try:
        import google.generativeai as genai
    except ImportError as exc:  # pragma: no cover - import guarded
        raise LLMError(f"google-generativeai not installed: {exc}") from exc

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = _build_prompt(payload)

    try:
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
    except Exception as exc:
        raise LLMError(f"Gemini request failed: {exc}") from exc

    # Strip accidental markdown fences if the model added them.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
        text = text.strip("`").strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Gemini returned non-JSON: {text[:200]}") from exc

    if not isinstance(data, dict):
        raise LLMError("Gemini JSON was not an object.")
    return data
