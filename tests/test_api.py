import json

import pytest
from fastapi.testclient import TestClient

import api.server as srv

H = {"Authorization": "Bearer t0ken"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PITCHCRAFT_API_TOKEN", "t0ken")
    monkeypatch.setattr(srv, "LEADS_DIR", tmp_path / "leads")
    monkeypatch.setattr(srv, "OUT_DIR", tmp_path / "outputs")
    monkeypatch.setattr(srv, "RUNS_DIR", tmp_path / "runs")
    return TestClient(srv.app)


CSV = b"lead_id,business,vertical,site_url\nL1,Joe's Pizza,restaurant,https://joespizza.com\n"


def test_auth_required(client):
    assert client.get("/api/batches").status_code == 401


def test_upload_rejects_bad_vertical(client):
    bad = b"lead_id,business,vertical,site_url\nL1,X,plumber,https://x.com\n"
    r = client.post("/api/batches", headers=H, files={"file": ("b.csv", bad)})
    assert r.status_code == 400


def test_upload_status_and_decision(client):
    r = client.post("/api/batches", headers=H, files={"file": ("May Batch.csv", CSV)})
    assert r.status_code == 200, r.text
    bid = r.json()["id"]

    lead_dir = srv.OUT_DIR / "joespizza-com"
    lead_dir.mkdir(parents=True)
    (lead_dir / "audit.json").write_text(json.dumps(
        {"problems": [{"severity": "high"}], "dollar_impact": {"monthly_loss_low": 400}}))
    (lead_dir / "stitch_screens_request.json").write_text("{}")

    lead = client.get(f"/api/batches/{bid}", headers=H).json()["leads"][0]
    assert lead["phases"]["audit"] == "done"
    assert lead["phases"]["screens"] == "waiting"
    assert lead["high_count"] == 1 and lead["loss_low"] == 400

    r = client.post("/api/leads/joespizza-com/decision", headers=H, json={"decision": "approved"})
    assert r.status_code == 200
    assert client.get("/api/batches", headers=H).json()[0]["approved"] == 1


def test_path_traversal_blocked(client):
    assert client.get("/api/leads/..%2F..%2Fetc/file/site", headers=H).status_code in (400, 404)
