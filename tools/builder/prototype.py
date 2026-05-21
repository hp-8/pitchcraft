"""build_prototype orchestrator — read approved.json → assemble site → deploy."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from tools.builder._models import BuildResult
from tools.builder._site import PAGE_ORDER, project_slug, write_site
from tools.builder._transform import TransformContext, transform_html
from tools.builder._vercel import deploy as vercel_deploy

if TYPE_CHECKING:
    from tools.sheets.client import SheetsClient

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_approved(lead_dir: Path) -> dict[str, int]:
    path = lead_dir / "approved.json"
    if not path.exists():
        raise FileNotFoundError(
            f"approved.json missing at {path}. Phase 5 must approve variants first."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    approved = data.get("approved") or {}
    if not isinstance(approved, dict):
        raise ValueError(f"approved.json 'approved' must be a dict, got {type(approved)}")
    return {str(k): int(v) for k, v in approved.items()}


def build_prototype(
    lead_id: str,
    lead_dir: str | Path,
    business: str,
    vertical: str,
    sheets_client: "SheetsClient | None" = None,
    skip_deploy: bool = False,
) -> BuildResult:
    """Assemble static site from approved Stitch HTML and (optionally) deploy to Vercel."""
    lead_dir_p = Path(lead_dir)
    site_dir = lead_dir_p / "site"
    errors: list[str] = []

    try:
        approved = _load_approved(lead_dir_p)
    except (FileNotFoundError, ValueError) as exc:
        errors.append(str(exc))
        return BuildResult(
            lead_id=lead_id,
            site_dir=str(site_dir),
            pages=[],
            skipped_deploy=skip_deploy,
            errors=errors,
        )

    transformed: dict[str, str] = {}
    for page in PAGE_ORDER:
        idx = approved.get(page)
        if idx is None:
            errors.append(f"no approved variant for page={page}")
            continue
        src = lead_dir_p / "stitch" / f"{page}-v{idx}.html"
        if not src.exists():
            errors.append(f"missing source HTML: {src}")
            continue
        raw = src.read_text(encoding="utf-8")
        ctx = TransformContext(page=page, business=business, vertical=vertical)
        transformed[page] = transform_html(raw, ctx, rewrite_nav=True)

    if not transformed:
        return BuildResult(
            lead_id=lead_id,
            site_dir=str(site_dir),
            pages=[],
            skipped_deploy=skip_deploy,
            errors=errors,
        )

    write_site(site_dir, transformed)
    pages = list(transformed.keys())

    deploy_url: str | None = None
    deploy_id: str | None = None
    deployed_at: str | None = None

    if skip_deploy:
        _sheet_update(sheets_client, lead_id, status="built", url=None, errors=errors)
        return BuildResult(
            lead_id=lead_id,
            site_dir=str(site_dir),
            pages=pages,
            skipped_deploy=True,
            errors=errors,
        )

    slug = project_slug(business, lead_id)
    try:
        result = vercel_deploy(site_dir, slug)
        if result.success:
            deploy_url = result.url
            deploy_id = result.deploy_id
            deployed_at = _utc_now_iso()
        else:
            errors.append(f"deploy failed: {result.error}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"deploy raised: {exc}")
        logger.exception("vercel deploy failed for %s", lead_id)

    status = "deployed" if deploy_url else "built"
    _sheet_update(
        sheets_client,
        lead_id,
        status=status,
        url=deploy_url,
        deployed_at=deployed_at,
        errors=errors,
    )

    return BuildResult(
        lead_id=lead_id,
        site_dir=str(site_dir),
        pages=pages,
        deploy_url=deploy_url,
        deploy_id=deploy_id,
        deployed_at=deployed_at,
        skipped_deploy=False,
        errors=errors,
    )


def _sheet_update(
    sheets_client: "SheetsClient | None",
    lead_id: str,
    status: str,
    url: str | None = None,
    deployed_at: str | None = None,
    errors: list[str] | None = None,
) -> None:
    if sheets_client is None:
        return
    fields: dict[str, object] = {"prototype_status": status}
    if url:
        fields["prototype_url"] = url
    if deployed_at:
        fields["deployed_at"] = deployed_at
    try:
        sheets_client.upsert_lead(lead_id, fields)
        note = (
            f"built+deployed → {url}"
            if status == "deployed" and url
            else "built (no deploy)"
        )
        sheets_client.update_status(lead_id, "prototype", status, note=note)
        if errors:
            for e in errors:
                sheets_client.append_error(lead_id, "prototype", e)
    except Exception as exc:  # noqa: BLE001
        logger.warning("sheet update failed for %s: %s", lead_id, exc)
