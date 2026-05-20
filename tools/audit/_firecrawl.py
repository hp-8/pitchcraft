"""Firecrawl scrape wrapper.

Frugal: one scrape per audit. Returns dict (never raises).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


def _get_client() -> Any:
    """Return a Firecrawl SDK client. Import is lazy for test mocking."""
    from firecrawl import Firecrawl  # type: ignore[import-not-found]

    load_dotenv()
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise RuntimeError("FIRECRAWL_API_KEY missing in env.")
    return Firecrawl(api_key=api_key)


def _doc_to_dict(doc: Any) -> dict[str, Any]:
    """Coerce a Firecrawl Document (or dict) into a plain dict."""
    if isinstance(doc, dict):
        return doc
    if hasattr(doc, "model_dump"):
        return doc.model_dump()
    return {
        "markdown": getattr(doc, "markdown", None),
        "html": getattr(doc, "html", None),
        "screenshot": getattr(doc, "screenshot", None),
        "metadata": getattr(doc, "metadata", None),
    }


def _download_screenshot(url: str, dest: Path) -> str | None:
    """Download screenshot to dest. Returns str path on success, None on failure."""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return str(dest)
    except Exception:
        return None


def fetch_firecrawl(url: str, screenshot_dest: Path | None = None) -> dict[str, Any]:
    """Scrape with Firecrawl (markdown + html + screenshot, mobile viewport).

    Returns:
        {markdown, html, screenshot_url, screenshot_path, metadata}
        or {error: "..."} on failure.
    """
    try:
        client = _get_client()
        doc = client.scrape(
            url,
            formats=["markdown", "html", "screenshot"],
            mobile=True,
        )
    except Exception as exc:  # noqa: BLE001 — defensive boundary
        return {"error": f"firecrawl_scrape_failed: {exc}"}

    data = _doc_to_dict(doc)
    screenshot_url = data.get("screenshot")
    # screenshot may be on metadata in some versions
    metadata = data.get("metadata") or {}
    if not screenshot_url and isinstance(metadata, dict):
        screenshot_url = metadata.get("screenshot")

    screenshot_path: str | None = None
    if screenshot_url and screenshot_dest is not None:
        screenshot_path = _download_screenshot(screenshot_url, screenshot_dest)

    return {
        "markdown": data.get("markdown") or "",
        "html": data.get("html") or "",
        "screenshot_url": screenshot_url,
        "screenshot_path": screenshot_path,
        "metadata": metadata if isinstance(metadata, dict) else {},
    }
