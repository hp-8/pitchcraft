"""Council orchestrator — fuses 5 agents into a Hallmark-compatible brief."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from tools.audit._models import AuditResult
from tools.council._models import CouncilResult
from tools.council.agents.animation import pick_motion_primitives
from tools.council.agents.audit_ux import map_audit_to_sections
from tools.council.agents.brand_voice import synthesize_brand_voice
from tools.council.agents.hallmark_picker import (
    infer_genre,
    pick_macrostructure_and_theme,
)
from tools.council.agents.inspiration import rank_moodboard
from tools.council.moderator import fuse
from tools.stitch._models import LeadContext

logger = logging.getLogger(__name__)


def _load_audit(path: str | Path | None) -> AuditResult | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        logger.warning("audit path not found: %s", p)
        return None
    raw = json.loads(p.read_text(encoding="utf-8"))
    return AuditResult.model_validate(raw)


def run_council(
    lead: LeadContext,
    audit_result: AuditResult | None = None,
    audit_json_path: str | Path | None = None,
    moodboard_path: str | Path | None = None,
    design_md_path: str | Path | None = None,
    out_dir: str | Path = "data/outputs",
    sheets_client: Any | None = None,
    skip_llm: bool = False,
    log_path: str | Path = ".hallmark/log.json",
) -> CouncilResult:
    """Run all 5 agents, fuse into design_brief.md, optionally update Sheet."""
    load_dotenv()

    audit = audit_result if audit_result is not None else _load_audit(audit_json_path)
    style = "modern"  # phase 3 moodboard always carries vertical/style; this is a hint only.

    # ---- run agents ------------------------------------------------------
    bv = synthesize_brand_voice(lead, audit=audit, skip_llm=skip_llm)
    insp = rank_moodboard(moodboard_path, vertical=lead.vertical, style=style)
    genre = infer_genre(bv.get("tone"), vertical=lead.vertical)
    hp = pick_macrostructure_and_theme(genre, log_path=log_path)
    ux = map_audit_to_sections(audit, vertical=lead.vertical, skip_llm=True)
    motion = pick_motion_primitives(
        genre=hp["genre"],
        theme=hp.get("theme"),
        moodboard_libs=insp.get("motion_lib_distribution"),
    )

    agent_outputs = {
        "brand_voice": bv,
        "inspiration": insp,
        "hallmark_picker": hp,
        "audit_ux": ux,
        "animation": motion,
    }

    design_md = Path(design_md_path) if design_md_path else None
    brief_path, summary = fuse(agent_outputs, lead, Path(out_dir), design_md_path=design_md)

    warnings: list[str] = list(summary.get("warnings", []))

    # ---- sheets ----------------------------------------------------------
    if sheets_client is not None:
        try:
            sheets_client.upsert_lead(lead.lead_id, {
                "ref_status": "council-done",
                "moodboard_url": str(brief_path),
            })
            note = (
                f"[council] {summary['macrostructure']} + {summary['theme']}; "
                f"nav={summary['nav']}; footer={summary['footer']}"
            )
            sheets_client.update_status(lead.lead_id, "ref", "council-done", note=note)
        except Exception as exc:
            logger.warning("sheets update failed: %s", exc)
            warnings.append(f"sheets update failed: {exc}")

    return CouncilResult(
        lead_id=lead.lead_id,
        brief_path=str(brief_path),
        chosen_macrostructure=summary["macrostructure"],
        chosen_theme=summary["theme"],
        chosen_nav=summary["nav"],
        chosen_footer=summary["footer"],
        genre=summary["genre"],
        must_have_sections=summary["must_have_sections"],
        motion_primitives=summary["motion_per_page"],
        agent_outputs=agent_outputs,
        warnings=warnings,
    )
