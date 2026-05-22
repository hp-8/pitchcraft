"""Optional LLM polish — rewrite template output for a more human tone.

Single Gemini Flash call per lead. Bypassed when --no-llm is set or Gemini
unavailable; raw template is shipped instead.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_PROMPT = """You are a senior sales copywriter writing cold outreach for a freelance web developer.

Rewrite the email body below to sound personal, human, and direct. Keep it under 140 words.

CONSTRAINTS:
- Preserve every fact: business name, dollar range, preview URL, the hook detail.
- Do not invent any new facts, metrics, names, or claims.
- Keep one short paragraph for the hook, one short paragraph for the dollar context + preview link, one short closing line.
- Sound like a real person who actually looked at their site — not a salesy template.
- No exclamation marks. No "Hope this email finds you well." No "I came across your business."
- Sign off as the sender exactly as given.

Output JSON ONLY: {"subject": "...", "body": "..."}.

INPUT:
"""


def polish(subject: str, body: str, lead: dict[str, Any]) -> tuple[str, str]:
    """Returns (subject, body) polished if any LLM provider succeeds, originals otherwise."""
    from tools.llm import LLMUnavailable, call_llm_json
    payload = json.dumps({
        "current_subject": subject,
        "current_body": body,
        "business": lead.get("business"),
        "lead_name": lead.get("name"),
        "vertical": lead.get("vertical"),
        "location": lead.get("location"),
    }, indent=2)
    try:
        data = call_llm_json(_PROMPT + payload)
        new_subject = (data.get("subject") or subject).strip()
        new_body = (data.get("body") or body).strip()
        if new_body:
            return new_subject, new_body + "\n"
    except LLMUnavailable as exc:
        logger.info("llm polish skipped: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm polish failed: %s; falling back to template", exc)
    return subject, body
