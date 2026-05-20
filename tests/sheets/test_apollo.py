"""Apollo CSV helpers."""
from __future__ import annotations

from pathlib import Path

from tools.sheets._apollo import (
    industry_to_vertical,
    iter_apollo_rows,
    row_to_fields,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "apollo_sample.csv"


def test_industry_classifier_restaurant():
    assert industry_to_vertical("Restaurants") == "restaurant"
    assert industry_to_vertical("Hospitality / Catering") == "restaurant"


def test_industry_classifier_dental():
    assert industry_to_vertical("Dental Practice") == "dental"
    assert industry_to_vertical("Orthodontics") == "dental"


def test_industry_classifier_realtor():
    assert industry_to_vertical("Real Estate") == "realtor"
    assert industry_to_vertical("Realty Group") == "realtor"


def test_industry_classifier_fnb():
    assert industry_to_vertical("Food & Beverage") == "fnb"
    assert industry_to_vertical("Craft Brewery") == "fnb"


def test_industry_classifier_fallback():
    assert industry_to_vertical("Computer Software") == "other"
    assert industry_to_vertical("") == "other"
    assert industry_to_vertical(None) == "other"


def test_row_to_fields_basic():
    row = {
        "First Name": "Joe",
        "Last Name": "Pizza",
        "Company": "Joe's Pizza",
        "Email": "joe@joespizza.com",
        "Website": "https://joespizza.com",
        "Industry": "Restaurants",
    }
    fields = row_to_fields(row)
    assert fields["name"] == "Joe Pizza"
    assert fields["business"] == "Joe's Pizza"
    assert fields["email"] == "joe@joespizza.com"
    assert fields["site_url"] == "https://joespizza.com"
    assert fields["vertical"] == "restaurant"


def test_row_to_fields_missing_optional(caplog):
    row = {"Company": "Solo Co", "Email": "x@y.com"}
    fields = row_to_fields(row)
    assert fields["business"] == "Solo Co"
    assert fields["email"] == "x@y.com"
    assert fields["vertical"] == "other"
    assert "name" not in fields


def test_iter_apollo_rows_reads_fixture():
    rows = list(iter_apollo_rows(FIXTURE))
    assert len(rows) == 5
    assert rows[0]["Industry"] == "Restaurants"
