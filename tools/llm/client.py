"""Provider-agnostic LLM client with fallback chain + manual input."""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """Raised when no provider can serve the call and manual is disabled."""


def _default_providers() -> list[str]:
    raw = os.getenv("LLM_PROVIDERS", "gemini,openai,anthropic,groq,manual")
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


# ---- Per-provider implementations -----------------------------------------


def _call_gemini(prompt: str, *, json_mode: bool) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise LLMUnavailable("GEMINI_API_KEY missing")
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise LLMUnavailable(f"google-generativeai not installed: {exc}") from exc
    genai.configure(api_key=key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    model = genai.GenerativeModel(model_name)
    resp = model.generate_content(prompt)
    return (resp.text or "").strip()


def _call_openai(prompt: str, *, json_mode: bool) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise LLMUnavailable("OPENAI_API_KEY missing")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMUnavailable(f"openai not installed: {exc}") from exc
    client = OpenAI(api_key=key)
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    kwargs: dict = {"model": model_name, "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "").strip()


def _call_anthropic(prompt: str, *, json_mode: bool) -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise LLMUnavailable("ANTHROPIC_API_KEY missing")
    try:
        import anthropic
    except ImportError as exc:
        raise LLMUnavailable(f"anthropic not installed: {exc}") from exc
    client = anthropic.Anthropic(api_key=key)
    model_name = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    msg = client.messages.create(
        model=model_name,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip() if msg.content else ""


def _call_groq(prompt: str, *, json_mode: bool) -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise LLMUnavailable("GROQ_API_KEY missing")
    try:
        from groq import Groq
    except ImportError as exc:
        raise LLMUnavailable(f"groq not installed: {exc}") from exc
    client = Groq(api_key=key)
    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    kwargs: dict = {"model": model_name, "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "").strip()


def _call_manual(prompt: str, *, json_mode: bool) -> str:
    if os.getenv("ALLOW_MANUAL_LLM") != "1":
        raise LLMUnavailable("manual input disabled (set ALLOW_MANUAL_LLM=1)")
    if not sys.stdin.isatty():
        raise LLMUnavailable("manual input requires a TTY")
    print("\n" + "=" * 70, file=sys.stderr)
    print("MANUAL LLM INPUT REQUESTED", file=sys.stderr)
    print("Paste the prompt below into ChatGPT / Claude / Gemini, copy the response,", file=sys.stderr)
    print("paste it back here, then send EOF (Ctrl-D on macOS/Linux, Ctrl-Z then Enter on Windows).", file=sys.stderr)
    if json_mode:
        print("Output must be a single JSON object, no markdown fences.", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    print("\n--- PROMPT ---", file=sys.stderr)
    print(prompt, file=sys.stderr)
    print("--- END PROMPT ---\n", file=sys.stderr)
    print("Paste response below and finish with EOF:", file=sys.stderr)
    return sys.stdin.read().strip()


_PROVIDERS: dict[str, Callable[..., str]] = {
    "gemini": _call_gemini,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "groq": _call_groq,
    "manual": _call_manual,
}


# ---- Public API -----------------------------------------------------------


def call_llm(prompt: str, *, json_mode: bool = False, providers: Optional[list[str]] = None) -> str:
    """Run prompt through fallback chain; return raw response text.

    Raises LLMUnavailable when every provider in the chain fails.
    """
    chain = providers if providers is not None else _default_providers()
    errors: list[str] = []
    for name in chain:
        fn = _PROVIDERS.get(name)
        if fn is None:
            errors.append(f"{name}: unknown provider")
            continue
        try:
            text = fn(prompt, json_mode=json_mode)
            if text:
                logger.info("LLM ok via %s", name)
                return text
            errors.append(f"{name}: empty response")
        except LLMUnavailable as exc:
            errors.append(f"{name}: {exc}")
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    raise LLMUnavailable("; ".join(errors) or "no providers attempted")


def call_llm_json(prompt: str, *, providers: Optional[list[str]] = None) -> dict:
    """Run prompt expecting JSON output; strip fences, parse, return dict."""
    text = call_llm(prompt, json_mode=True, providers=providers)
    # Strip markdown fences if present.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
        text = text.strip("`").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMUnavailable(f"non-JSON output: {text[:200]}") from exc
    if not isinstance(data, dict):
        raise LLMUnavailable(f"JSON output was not an object: {type(data).__name__}")
    return data
