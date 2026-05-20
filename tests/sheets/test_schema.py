"""Schema sanity tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from tools.sheets._schema import COLUMNS, PHASES, Lead

# Count from PLAN.md "Master Sheet Columns".
EXPECTED_COLUMN_COUNT = 38


def test_columns_count_matches_plan():
    assert len(COLUMNS) == EXPECTED_COLUMN_COUNT


def test_columns_first_and_last():
    assert COLUMNS[0] == "lead_id"
    assert COLUMNS[-1] == "error_log"


def test_columns_unique():
    assert len(set(COLUMNS)) == len(COLUMNS)


def test_phases_set():
    assert PHASES == {
        "audit", "ref", "stitch", "prototype", "email", "proposal", "deal"
    }


def test_lead_model_accepts_partial():
    lead = Lead(lead_id="x", vertical="restaurant")
    assert lead.lead_id == "x"
    assert lead.vertical == "restaurant"


def test_lead_model_rejects_extra():
    with pytest.raises(ValidationError):
        Lead(lead_id="x", garbage_field="nope")


def test_lead_model_numeric_fields():
    lead = Lead(amount_usd=1200.0, audit_dollar_impact=450.5, open_count=3)
    assert lead.amount_usd == 1200.0
    assert lead.open_count == 3
