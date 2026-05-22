"""Multi-provider LLM client with automatic fallback chain.

Order of attempts (configurable via LLM_PROVIDERS env var, comma separated):
    gemini  -> google-generativeai (GEMINI_API_KEY)
    openai  -> openai package (OPENAI_API_KEY)
    anthropic -> anthropic package (ANTHROPIC_API_KEY)
    groq    -> groq package (GROQ_API_KEY)
    manual  -> read from stdin (only when ALLOW_MANUAL_LLM=1)

If every provider fails (no keys, rate limit, network), and manual is enabled,
the caller is prompted in the terminal to paste a response. Otherwise an
LLMUnavailable exception is raised so the pipeline can skip cleanly.
"""
from tools.llm.client import LLMUnavailable, call_llm, call_llm_json

__all__ = ["LLMUnavailable", "call_llm", "call_llm_json"]
