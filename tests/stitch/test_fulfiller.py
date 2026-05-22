"""Tests for tools.stitch.fulfiller — envelope state machine."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from tools.stitch._models import LeadContext
from tools.stitch.cli import app as cli_app
from tools.stitch.fulfiller import (
    envelope_status,
    finalize_envelope,
    iter_pending_envelopes,
    iter_pending_screens,
    load_envelope,
    mark_screen_error,
    mark_screen_fulfilled,
)
from tools.stitch.screens import write_screens_request


@pytest.fixture
def envelope(tmp_path: Path) -> Path:
    lead = LeadContext(
        lead_id="lead_ff",
        business="Joe's Pizza",
        vertical="restaurant",
        services=["pizza"],
    )
    return write_screens_request(lead, "ds_ff", out_root=tmp_path)


def test_initial_status_queued(envelope: Path) -> None:
    assert envelope_status(envelope) == "queued"


def test_iter_pending_envelopes_finds_it(envelope: Path, tmp_path: Path) -> None:
    found = iter_pending_envelopes(tmp_path)
    assert envelope in found


def test_iter_pending_envelopes_skips_fully_fulfilled(
    envelope: Path, tmp_path: Path
) -> None:
    env = load_envelope(envelope)
    for s in env["screens"]:
        s["fulfilled"] = True
    envelope.write_text(json.dumps(env), encoding="utf-8")
    assert iter_pending_envelopes(tmp_path) == []


def test_iter_pending_screens_in_order(envelope: Path) -> None:
    pending = list(iter_pending_screens(envelope))
    assert len(pending) == 12
    assert [i for i, _ in pending] == list(range(12))


def test_mark_screen_fulfilled_writes_target_and_flips_flag(envelope: Path) -> None:
    payload = {"screen_instance_id": "sid_001", "project_id": "proj_1"}
    mark_screen_fulfilled(envelope, 0, payload, html_content="<h1>hi</h1>")
    env = load_envelope(envelope)
    s0 = env["screens"][0]
    assert s0["fulfilled"] is True
    assert "fulfilled_at" in s0
    assert "error" not in s0
    target = Path(s0["target_path"])
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == payload
    html_path = target.with_suffix(".html")
    assert html_path.exists()
    assert html_path.read_text(encoding="utf-8") == "<h1>hi</h1>"
    # other screens untouched
    assert env["screens"][1]["fulfilled"] is False


def test_mark_screen_fulfilled_bytes_html(envelope: Path) -> None:
    mark_screen_fulfilled(envelope, 1, {"id": "x"}, html_content=b"<b>bytes</b>")
    target = Path(load_envelope(envelope)["screens"][1]["target_path"])
    assert target.with_suffix(".html").read_bytes() == b"<b>bytes</b>"


def test_mark_screen_fulfilled_without_html(envelope: Path) -> None:
    mark_screen_fulfilled(envelope, 2, {"id": "y"})
    target = Path(load_envelope(envelope)["screens"][2]["target_path"])
    assert target.exists()
    assert not target.with_suffix(".html").exists()


def test_mark_screen_error_no_target_written(envelope: Path) -> None:
    mark_screen_error(envelope, 3, "stitch timeout")
    env = load_envelope(envelope)
    s = env["screens"][3]
    assert s["fulfilled"] is True
    assert s["error"] == "stitch timeout"
    assert not Path(s["target_path"]).exists()


def test_envelope_status_ready_when_all_ok(envelope: Path) -> None:
    for i in range(12):
        mark_screen_fulfilled(envelope, i, {"id": f"s{i}"})
    assert envelope_status(envelope) == "ready"


def test_envelope_status_partial_when_some_errored(envelope: Path) -> None:
    for i in range(11):
        mark_screen_fulfilled(envelope, i, {"id": f"s{i}"})
    mark_screen_error(envelope, 11, "boom")
    assert envelope_status(envelope) == "partial"


def test_finalize_stamps_status_and_calls_sheets(envelope: Path) -> None:
    for i in range(12):
        mark_screen_fulfilled(envelope, i, {"id": f"s{i}"})
    client = MagicMock()
    result = finalize_envelope(envelope, sheets_client=client)
    assert result == "ready"
    env = load_envelope(envelope)
    assert env["status"] == "ready"
    assert "finalized_at" in env
    client.upsert_lead.assert_called_once()
    lead_id, fields = client.upsert_lead.call_args.args
    assert lead_id == "lead_ff"
    assert fields["stitch_status"] == "ready"
    assert fields["stitch_variants_url"] == str(envelope)
    client.update_status.assert_called_once_with(
        "lead_ff", "stitch", "ready", note="fulfilled 12/12"
    )


def test_finalize_partial_note_counts_only_ok(envelope: Path) -> None:
    for i in range(10):
        mark_screen_fulfilled(envelope, i, {"id": f"s{i}"})
    mark_screen_error(envelope, 10, "x")
    mark_screen_error(envelope, 11, "y")
    client = MagicMock()
    assert finalize_envelope(envelope, sheets_client=client) == "partial"
    client.update_status.assert_called_once_with(
        "lead_ff", "stitch", "partial", note="fulfilled 10/12"
    )


def test_finalize_skips_sheets_when_still_queued(envelope: Path) -> None:
    client = MagicMock()
    assert finalize_envelope(envelope, sheets_client=client) == "queued"
    client.upsert_lead.assert_not_called()
    client.update_status.assert_not_called()


def test_cli_pending_emits_jsonl(envelope: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli_app, ["pending", "--out-dir", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    lines = [json.loads(line) for line in result.stdout.strip().splitlines()]
    assert len(lines) == 12
    assert lines[0]["envelope"] == str(envelope)
    assert lines[0]["idx"] == 0
    assert lines[0]["tool"] == "mcp__stitch__generate_screen_from_text"
    assert "prompt" in lines[0]["args"]


def test_cli_fulfill_and_finalize(envelope: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    result_file = tmp_path / "result.json"
    result_file.write_text(json.dumps({"sid": "abc"}), encoding="utf-8")
    html_file = tmp_path / "out.html"
    html_file.write_text("<h1>hi</h1>", encoding="utf-8")

    for i in range(12):
        r = runner.invoke(
            cli_app,
            [
                "fulfill",
                "--envelope", str(envelope),
                "--idx", str(i),
                "--result-file", str(result_file),
                "--html-file", str(html_file),
            ],
        )
        assert r.exit_code == 0, r.stdout

    r = runner.invoke(cli_app, ["finalize", "--envelope", str(envelope)])
    assert r.exit_code == 0
    assert r.stdout.strip() == "ready"


def test_cli_fulfill_error(envelope: Path) -> None:
    runner = CliRunner()
    r = runner.invoke(
        cli_app,
        ["fulfill-error", "--envelope", str(envelope), "--idx", "5", "--error", "boom"],
    )
    assert r.exit_code == 0
    env = load_envelope(envelope)
    assert env["screens"][5]["error"] == "boom"
    assert env["screens"][5]["fulfilled"] is True
