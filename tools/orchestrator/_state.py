"""Sheet status driver — central place to read/write per-phase status.

Wraps SheetsClient. Locks are per-row (gspread already batches; we just serialize
writes per lead via an asyncio.Lock map).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Phase → sheet column mapping for status writes.
PHASE_TO_STATUS_FIELD: dict[str, str] = {
    "scrape": "ref_status",          # moodboard kept under ref_status alongside design_ref
    "audit": "audit_status",
    "design_ref": "ref_status",
    "council": "ref_status",
    "stitch_envelope": "stitch_status",
    "stitch_fulfill": "stitch_status",
    "polish": "prototype_status",
    "build": "prototype_status",
    "email": "email_status",
}


class StateDriver:
    """Thin async-friendly wrapper over SheetsClient with per-lead locks."""

    def __init__(self, sheets_client: Any | None = None) -> None:
        self._sc = sheets_client
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, lead_id: str) -> asyncio.Lock:
        if lead_id not in self._locks:
            self._locks[lead_id] = asyncio.Lock()
        return self._locks[lead_id]

    async def upsert(self, lead_id: str, fields: dict[str, Any]) -> None:
        if self._sc is None:
            return
        async with self._lock(lead_id):
            await asyncio.to_thread(self._sc.upsert_lead, lead_id, fields)

    async def update_status(
        self,
        lead_id: str,
        phase: str,
        status: str,
        note: str | None = None,
    ) -> None:
        if self._sc is None:
            return
        # Map orchestrator phase to sheet phase if needed
        sheet_phase = {
            "scrape": "ref",
            "design_ref": "ref",
            "council": "ref",
            "stitch_envelope": "stitch",
            "stitch_fulfill": "stitch",
            "polish": "prototype",
            "build": "prototype",
        }.get(phase, phase)
        async with self._lock(lead_id):
            try:
                await asyncio.to_thread(
                    self._sc.update_status, lead_id, sheet_phase, status, note
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("sheet update_status failed for %s/%s: %s", lead_id, phase, exc)

    async def append_error(self, lead_id: str, where: str, message: str) -> None:
        if self._sc is None:
            return
        async with self._lock(lead_id):
            try:
                await asyncio.to_thread(self._sc.append_error, lead_id, where, message)
            except Exception as exc:  # noqa: BLE001
                logger.warning("sheet append_error failed: %s", exc)
