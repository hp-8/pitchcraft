"""Competitor lookup via Firecrawl search.

Caches results to data/outputs/<slug>/competitors.json for reuse.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_VERTICAL_QUERIES = {
    "realtor": "real estate brokerage",
    "restaurant": "restaurants",
    "dental": "dental clinic",
    "fnb": "wineries",
    "other": "businesses",
}

# Domains to drop (aggregators, listings, irrelevant).
_DROP_DOMAINS = {
    "yelp.com", "tripadvisor.com", "google.com", "facebook.com",
    "instagram.com", "linkedin.com", "wikipedia.org", "youtube.com",
    "yellowpages.com", "bbb.org", "zillow.com", "redfin.com",
    "realtor.com", "trulia.com",
    # Aggregators / directories / ranking sites
    "realtrends.com", "realestatealmanac.com", "goodfirms.co",
    "realestateuk.org", "french-property.com", "lefigaro.com",
    "vineyards.com", "aliciatenise.com", "usawineratings.com",
    "joinreal.com", "wernewyork.com",
    "clutch.co", "g2.com", "capterra.com", "crunchbase.com",
    "forbes.com", "businessinsider.com", "medium.com",
}

# Title patterns that signal a list / ranking / aggregator page.
_DROP_TITLE_PATTERNS = [
    "top ", "best ", "ranking", "rankings", "companies in ", "agents in ",
    "wine map", "wine vacation", "introduction to ", "10 best", "25 best",
    "directory", "join our team", "join real", "wine regions",
    "for sale", "houses ", "home search", "watch ", "guide", "guides",
    "itinerar", "travel ", "our agency", "homepage", "real estate in ",
    "property in ", "homes for ",
]


def _domain(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        return host.lower().lstrip("www.")
    except Exception:
        return ""


def _is_self(competitor_url: str, lead_site_url: str) -> bool:
    a = _domain(competitor_url)
    b = _domain(lead_site_url)
    if not a or not b:
        return False
    a_root = ".".join(a.split(".")[-2:])
    b_root = ".".join(b.split(".")[-2:])
    return a_root == b_root


def _is_drop(url: str) -> bool:
    d = _domain(url)
    return any(d.endswith(drop) for drop in _DROP_DOMAINS)


def _clean_title(title: str) -> str:
    # Strip trailing "| Site Tagline" or ", subordinate clause".
    title = re.sub(r"\s*[|·•].*$", "", title)
    title = re.sub(r"\s+–\s+.*$", "", title)
    title = re.sub(r"\s+-\s+.*$", "", title)
    # Cut at first comma to drop trailing descriptors.
    title = title.split(",")[0]
    # Cap length.
    title = title.strip()
    if len(title) > 60:
        title = title[:60].rstrip() + "..."
    return title


def _build_query(business: str, vertical: str, location: str | None) -> str:
    base = _VERTICAL_QUERIES.get(vertical, _VERTICAL_QUERIES["other"])
    where = location or "United States"
    return f"{base} {where}"


def _firecrawl_search(query: str, limit: int = 8, timeout: int = 60) -> list[dict]:
    cmd = ["firecrawl", "search", query, "--limit", str(limit), "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("firecrawl search failed: %s", exc)
        return []
    if proc.returncode != 0:
        logger.warning("firecrawl rc=%s stderr=%s", proc.returncode, proc.stderr[:200])
        return []
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        logger.warning("firecrawl json decode failed: %s", exc)
        return []
    items = (data.get("data") or {}).get("web") or []
    return items


def lookup_competitors(
    business: str,
    vertical: str,
    location: str | None,
    site_url: str,
    cache_path: Optional[Path] = None,
    limit: int = 4,
) -> list[dict[str, str]]:
    """Return [{name, url, snippet}] of top competitors. Cached on disk."""
    if cache_path and cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    query = _build_query(business, vertical, location)
    raw = _firecrawl_search(query, limit=limit * 3)
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    biz_lower = business.lower()
    for item in raw:
        url = item.get("url", "")
        if not url or _is_drop(url) or _is_self(url, site_url):
            continue
        title = _clean_title(item.get("title", ""))
        if not title or title.lower() == biz_lower:
            continue
        tl = title.lower()
        if any(pat in tl for pat in _DROP_TITLE_PATTERNS):
            continue
        # Skip titles that start lowercase (usually fragments, not brand names).
        if title[0].islower():
            continue
        root = ".".join(_domain(url).split(".")[-2:])
        if root in seen:
            continue
        seen.add(root)
        out.append({"name": title, "url": url, "snippet": item.get("description", "") or ""})
        if len(out) >= limit:
            break

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out
