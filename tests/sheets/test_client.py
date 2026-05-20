"""SheetsClient behavior tests against a fake gspread worksheet."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.sheets._schema import COLUMNS
from tools.sheets.client import SheetsClient

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "apollo_sample.csv"


def test_missing_credentials_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_SHEETS_SPREADSHEET_ID", raising=False)
    # Block .env from re-populating.
    from tools.sheets import client as client_mod

    monkeypatch.setattr(client_mod, "load_dotenv", lambda *a, **kw: None)
    sc = SheetsClient()
    with pytest.raises(RuntimeError) as exc:
        sc.ensure_schema()
    assert "GOOGLE_SHEETS_CREDENTIALS" in str(exc.value)


def test_missing_spreadsheet_id_raises(monkeypatch, tmp_path):
    creds = tmp_path / "sa.json"
    creds.write_text("{}")
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", str(creds))
    monkeypatch.delenv("GOOGLE_SHEETS_SPREADSHEET_ID", raising=False)
    from tools.sheets import client as client_mod

    monkeypatch.setattr(client_mod, "load_dotenv", lambda *a, **kw: None)
    sc = SheetsClient()
    with pytest.raises(RuntimeError) as exc:
        sc.ensure_schema()
    assert "GOOGLE_SHEETS_SPREADSHEET_ID" in str(exc.value)


def test_ensure_schema_writes_header(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    assert fake_ws.rows[0] == list(COLUMNS)


def test_ensure_schema_idempotent(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    sheets_client.ensure_schema()
    assert fake_ws.rows[0] == list(COLUMNS)
    # No extra writes besides the initial header.
    assert len(fake_ws.rows) == 1


def test_upsert_lead_insert(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    sheets_client.upsert_lead("L1", {"name": "Alice", "vertical": "dental"})
    assert len(fake_ws.rows) == 2
    row = fake_ws.rows[1]
    assert row[COLUMNS.index("lead_id")] == "L1"
    assert row[COLUMNS.index("name")] == "Alice"
    assert row[COLUMNS.index("vertical")] == "dental"
    assert row[COLUMNS.index("last_updated")]


def test_upsert_lead_update_path_uses_batch(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    sheets_client.upsert_lead("L1", {"name": "Alice"})
    fake_ws.batch_calls.clear()
    sheets_client.upsert_lead("L1", {"vertical": "realtor"})
    # update path uses batch_update.
    assert len(fake_ws.batch_calls) == 1
    row = fake_ws.rows[1]
    assert row[COLUMNS.index("vertical")] == "realtor"
    # name preserved.
    assert row[COLUMNS.index("name")] == "Alice"


def test_upsert_lead_never_overwrites_lead_id(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    sheets_client.upsert_lead("L1", {"name": "A"})
    sheets_client.upsert_lead("L1", {"lead_id": "HACKED", "name": "B"})
    assert fake_ws.rows[1][COLUMNS.index("lead_id")] == "L1"
    assert fake_ws.rows[1][COLUMNS.index("name")] == "B"


def test_update_status_sets_phase_and_appends_note(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    sheets_client.upsert_lead("L1", {"name": "A"})
    sheets_client.update_status("L1", "audit", "done", note="1h")
    row = fake_ws.rows[1]
    assert row[COLUMNS.index("audit_status")] == "done"
    notes = row[COLUMNS.index("notes")]
    assert "[audit] done" in notes
    assert "1h" in notes


def test_update_status_appends_multiple_notes(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    sheets_client.update_status("L1", "audit", "started")
    sheets_client.update_status("L1", "audit", "done")
    notes = fake_ws.rows[1][COLUMNS.index("notes")]
    assert "started" in notes
    assert "done" in notes
    # newest at bottom
    assert notes.index("started") < notes.index("done")


def test_update_status_invalid_phase(sheets_client):
    with pytest.raises(ValueError):
        sheets_client.update_status("L1", "bogus", "done")


def test_append_error(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    sheets_client.upsert_lead("L1", {"name": "A"})
    sheets_client.append_error("L1", "scraper", "timeout")
    sheets_client.append_error("L1", "audit", "404")
    log = fake_ws.rows[1][COLUMNS.index("error_log")]
    assert "[scraper] timeout" in log
    assert "[audit] 404" in log
    assert log.index("timeout") < log.index("404")


def test_get_lead_hit_and_miss(sheets_client):
    sheets_client.ensure_schema()
    sheets_client.upsert_lead("L1", {"name": "Alice", "vertical": "fnb"})
    row = sheets_client.get_lead("L1")
    assert row is not None
    assert row["name"] == "Alice"
    assert row["vertical"] == "fnb"
    assert sheets_client.get_lead("nope") is None


def test_find_leads(sheets_client):
    sheets_client.ensure_schema()
    sheets_client.upsert_lead("L1", {"vertical": "restaurant", "audit_status": "done"})
    sheets_client.upsert_lead("L2", {"vertical": "restaurant", "audit_status": "pending"})
    sheets_client.upsert_lead("L3", {"vertical": "dental", "audit_status": "done"})
    rows = sheets_client.find_leads(vertical="restaurant", audit_status="done")
    assert len(rows) == 1
    assert rows[0]["lead_id"] == "L1"


def test_last_updated_set_on_every_write(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    sheets_client.upsert_lead("L1", {"name": "A"})
    ts1 = fake_ws.rows[1][COLUMNS.index("last_updated")]
    assert ts1
    sheets_client.update_status("L1", "audit", "done")
    ts2 = fake_ws.rows[1][COLUMNS.index("last_updated")]
    assert ts2
    sheets_client.append_error("L1", "x", "y")
    ts3 = fake_ws.rows[1][COLUMNS.index("last_updated")]
    assert ts3


def test_bulk_import_csv(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    n = sheets_client.bulk_import_csv(FIXTURE, dedupe_by="email")
    assert n == 5
    # second import dedupes; no new inserts.
    n2 = sheets_client.bulk_import_csv(FIXTURE, dedupe_by="email")
    assert n2 == 0
    # data rows: header + 5
    assert len(fake_ws.rows) == 6
    verticals = [r[COLUMNS.index("vertical")] for r in fake_ws.rows[1:]]
    assert "restaurant" in verticals
    assert "dental" in verticals
    assert "realtor" in verticals
    assert "fnb" in verticals
    assert "other" in verticals


def test_delete_lead(sheets_client, fake_ws):
    sheets_client.ensure_schema()
    sheets_client.upsert_lead("L1", {"name": "A"})
    assert sheets_client.delete_lead("L1") is True
    assert sheets_client.get_lead("L1") is None
    assert sheets_client.delete_lead("L1") is False
