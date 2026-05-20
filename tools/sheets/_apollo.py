"""Apollo CSV import helpers."""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

# Vertical classifier keyword map. First match wins; fallback "other".
# Keywords are matched case-insensitively as substrings of the Apollo Industry field.
VERTICAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "restaurant": (
        "restaurant",
        "food service",
        "hospitality",
        "cafe",
        "coffee",
        "bakery",
        "catering",
        "dining",
    ),
    "dental": (
        "dental",
        "dentist",
        "orthodont",
        "oral health",
    ),
    "realtor": (
        "real estate",
        "realtor",
        "realty",
        "property management",
        "broker",
    ),
    "fnb": (
        "food & beverage",
        "food and beverage",
        "beverage",
        "brewery",
        "winery",
        "distillery",
        "f&b",
    ),
}


def industry_to_vertical(industry: str | None) -> str:
    """Map a free-form Apollo Industry string to one of our verticals or 'other'."""
    if not industry:
        return "other"
    norm = industry.strip().lower()
    if not norm:
        return "other"
    for vertical, keywords in VERTICAL_KEYWORDS.items():
        for kw in keywords:
            if kw in norm:
                return vertical
    return "other"


def _ci_get(row: dict[str, str], *candidates: str) -> str:
    """Case-insensitive lookup across candidate keys."""
    lowered = {k.lower().strip(): v for k, v in row.items() if k}
    for cand in candidates:
        v = lowered.get(cand.lower().strip())
        if v is not None and v.strip():
            return v.strip()
    return ""


def row_to_fields(row: dict[str, str]) -> dict[str, str]:
    """Map one Apollo CSV row to master-sheet field dict.

    Missing optional columns warn but don't raise.
    """
    first = _ci_get(row, "First Name", "FirstName", "first_name")
    last = _ci_get(row, "Last Name", "LastName", "last_name")
    name_parts = [p for p in (first, last) if p]
    name = " ".join(name_parts)

    business = _ci_get(row, "Company", "Company Name", "Organization", "business")
    email = _ci_get(row, "Email", "Email Address", "email")
    site_url = _ci_get(row, "Website", "Company Website", "Website URL", "site_url")
    industry = _ci_get(row, "Industry", "Sector", "vertical")
    vertical = industry_to_vertical(industry)

    fields: dict[str, str] = {}
    if name:
        fields["name"] = name
    else:
        logger.warning("Apollo row missing name (First Name + Last Name)")
    if business:
        fields["business"] = business
    else:
        logger.warning("Apollo row missing Company/business")
    if email:
        fields["email"] = email
    else:
        logger.warning("Apollo row missing Email")
    if site_url:
        fields["site_url"] = site_url
    else:
        logger.warning("Apollo row missing Website/site_url")
    fields["vertical"] = vertical
    return fields


def iter_apollo_rows(csv_path: str | Path) -> Iterator[dict[str, str]]:
    """Yield raw row dicts from an Apollo CSV file."""
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield row
