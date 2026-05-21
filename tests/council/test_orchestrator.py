"""End-to-end test for the council orchestrator."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from tools.council._models import CouncilResult
from tools.council.orchestrator import run_council
from tools.stitch._models import LeadContext

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def _lead() -> LeadContext:
    return LeadContext(
        lead_id="test-pizza",
        business="Joe's Pizza",
        vertical="restaurant",
        location="Brooklyn, NY",
        services=["pizza", "delivery"],
    )


def test_end_to_end_skip_llm_no_sheet(tmp_path: Path) -> None:
    log = tmp_path / "log.json"
    result = run_council(
        lead=_lead(),
        audit_json_path=FIX / "audit_sample.json",
        moodboard_path=FIX / "moodboard_sample.json",
        out_dir=tmp_path,
        sheets_client=None,
        skip_llm=True,
        log_path=log,
    )
    assert isinstance(result, CouncilResult)
    assert Path(result.brief_path).exists()
    assert result.lead_id == "test-pizza"
    assert result.chosen_macrostructure
    assert result.chosen_theme
    assert result.chosen_nav.startswith("N")
    assert result.chosen_footer.startswith("Ft")
    assert result.genre in {"editorial", "modern-minimal", "atmospheric", "playful"}
    assert set(result.motion_primitives.keys()) >= {"landing", "services", "about", "contact"}
    assert "brand_voice" in result.agent_outputs
    assert log.exists()


def test_sheets_client_called(tmp_path: Path) -> None:
    sheets = MagicMock()
    log = tmp_path / "log.json"
    result = run_council(
        lead=_lead(),
        audit_json_path=FIX / "audit_sample.json",
        moodboard_path=FIX / "moodboard_sample.json",
        out_dir=tmp_path,
        sheets_client=sheets,
        skip_llm=True,
        log_path=log,
    )
    sheets.upsert_lead.assert_called_once()
    args, _ = sheets.upsert_lead.call_args
    assert args[0] == "test-pizza"
    assert args[1]["ref_status"] == "council-done"
    assert args[1]["moodboard_url"] == result.brief_path
    sheets.update_status.assert_called_once()
    _, kwargs = sheets.update_status.call_args
    assert "macrostructure" not in kwargs  # note is positional kw
    note_kw = sheets.update_status.call_args.kwargs.get("note", "")
    assert result.chosen_macrostructure in note_kw


def test_runs_without_audit_or_moodboard(tmp_path: Path) -> None:
    result = run_council(
        lead=_lead(),
        out_dir=tmp_path,
        sheets_client=None,
        skip_llm=True,
        log_path=tmp_path / "log.json",
    )
    assert Path(result.brief_path).exists()
    assert any("moodboard" in w for w in result.warnings + [
        w for ao in result.agent_outputs.values() for w in (ao.get("warnings") or [])
    ])
