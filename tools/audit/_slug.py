"""Slug helper that reuses tools.scrapers._slug.slugify_url."""
from __future__ import annotations

from tools.scrapers._slug import slugify_url


def url_to_slug(url: str) -> str:
    """Filesystem-safe slug from a URL (netloc + path)."""
    return slugify_url(url)
