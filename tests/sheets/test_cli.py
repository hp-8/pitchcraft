"""Typer CLI tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tools.sheets import cli as cli_mod
from tools.sheets.cli import app

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "apollo_sample.csv"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wire_client(monkeypatch, sheets_client):
    monkeypatch.setattr(cli_mod, "SheetsClient", lambda: sheets_client)
    return sheets_client


def test_ensure_schema_cmd(runner, _wire_client):
    r = runner.invoke(app, ["ensure-schema"])
    assert r.exit_code == 0
    assert "schema ok" in r.stdout


def test_upsert_and_get(runner, _wire_client):
    runner.invoke(app, ["ensure-schema"])
    r = runner.invoke(app, ["upsert-lead", "L1", "--field", "name=Alice", "--field", "vertical=dental"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["get-lead", "L1"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data["name"] == "Alice"
    assert data["vertical"] == "dental"


def test_get_missing_returns_null_exit1(runner, _wire_client):
    runner.invoke(app, ["ensure-schema"])
    r = runner.invoke(app, ["get-lead", "nope"])
    assert r.exit_code == 1
    assert "null" in r.stdout


def test_update_status_cmd(runner, _wire_client):
    runner.invoke(app, ["ensure-schema"])
    runner.invoke(app, ["upsert-lead", "L1", "--field", "name=A"])
    r = runner.invoke(app, [
        "update-status", "L1", "--phase", "audit", "--status", "done", "--note", "ok"
    ])
    assert r.exit_code == 0
    row = _wire_client.get_lead("L1")
    assert row["audit_status"] == "done"
    assert "ok" in row["notes"]


def test_update_status_invalid_phase(runner, _wire_client):
    runner.invoke(app, ["ensure-schema"])
    r = runner.invoke(app, [
        "update-status", "L1", "--phase", "bogus", "--status", "x"
    ])
    assert r.exit_code != 0


def test_bulk_import_cmd(runner, _wire_client):
    runner.invoke(app, ["ensure-schema"])
    r = runner.invoke(app, ["bulk-import", str(FIXTURE)])
    assert r.exit_code == 0
    assert "inserted 5" in r.stdout


def test_find_cmd(runner, _wire_client):
    runner.invoke(app, ["ensure-schema"])
    runner.invoke(app, ["upsert-lead", "L1", "--field", "vertical=restaurant"])
    runner.invoke(app, ["upsert-lead", "L2", "--field", "vertical=dental"])
    r = runner.invoke(app, ["find", "--vertical", "restaurant"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert len(data) == 1
    assert data[0]["lead_id"] == "L1"


def test_test_cmd(runner, _wire_client):
    r = runner.invoke(app, ["test"])
    assert r.exit_code == 0, r.stdout
    assert "ok" in r.stdout


def test_upsert_bad_field(runner, _wire_client):
    runner.invoke(app, ["ensure-schema"])
    r = runner.invoke(app, ["upsert-lead", "L1", "--field", "noequals"])
    assert r.exit_code != 0
