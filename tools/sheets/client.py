"""SheetsClient — thin gspread wrapper around the master leads worksheet.

Lazy auth: missing credentials raise RuntimeError only on first network call.

Usage:
    from tools.sheets.client import SheetsClient
    sc = SheetsClient()
    sc.ensure_schema()
    sc.upsert_lead("lead_123", {"name": "Joe", "vertical": "restaurant"})
    sc.update_status("lead_123", "audit", "done", note="impact $400/mo")
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gspread
from dotenv import load_dotenv
from gspread.utils import rowcol_to_a1

from tools.sheets._apollo import iter_apollo_rows, row_to_fields
from tools.sheets._schema import COLUMNS, PHASES

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SheetsClient:
    """Master-sheet client. All writes idempotent; updates batched."""

    def __init__(
        self,
        spreadsheet_id: str | None = None,
        credentials_path: str | Path | None = None,
        worksheet_name: str = "leads",
    ) -> None:
        self._spreadsheet_id = spreadsheet_id
        self._credentials_path: str | None = (
            str(credentials_path) if credentials_path else None
        )
        self._worksheet_name = worksheet_name
        self._gc: gspread.Client | None = None
        self._ss: Any = None
        self._ws: Any = None

    # ---- lazy auth -------------------------------------------------------

    def _resolve_config(self) -> tuple[str, str]:
        load_dotenv()
        creds = self._credentials_path or os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        if not creds:
            raise RuntimeError(
                "GOOGLE_SHEETS_CREDENTIALS missing. Set it in .env (path to service "
                "account JSON, e.g. ./secrets/sheets-sa.json)."
            )
        if not Path(creds).exists():
            raise RuntimeError(
                f"GOOGLE_SHEETS_CREDENTIALS path does not exist: {creds}"
            )
        sid = self._spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        if not sid:
            raise RuntimeError(
                "GOOGLE_SHEETS_SPREADSHEET_ID missing. Set it in .env."
            )
        return creds, sid

    def _connect(self) -> None:
        if self._ws is not None:
            return
        creds, sid = self._resolve_config()
        self._gc = gspread.service_account(filename=creds)
        self._ss = self._gc.open_by_key(sid)
        try:
            self._ws = self._ss.worksheet(self._worksheet_name)
        except gspread.WorksheetNotFound:
            self._ws = self._ss.add_worksheet(
                title=self._worksheet_name, rows=1000, cols=len(COLUMNS)
            )

    # ---- schema ----------------------------------------------------------

    def ensure_schema(self) -> None:
        """Create worksheet if missing and write/repair the header row."""
        self._connect()
        header = self._ws.row_values(1)
        if list(header) == list(COLUMNS):
            return
        end_a1 = rowcol_to_a1(1, len(COLUMNS))
        self._ws.update(f"A1:{end_a1}", [list(COLUMNS)])

    # ---- read ------------------------------------------------------------

    def _all_rows(self) -> list[list[str]]:
        self._connect()
        return self._ws.get_all_values()

    def _row_to_dict(self, row: list[str]) -> dict[str, str]:
        # pad/truncate to header length
        padded = list(row) + [""] * max(0, len(COLUMNS) - len(row))
        return {col: padded[i] for i, col in enumerate(COLUMNS)}

    def _find_row_index(self, lead_id: str) -> int | None:
        """1-based row index of lead_id (excluding header), else None."""
        rows = self._all_rows()
        for idx, row in enumerate(rows[1:], start=2):
            if row and row[0] == lead_id:
                return idx
        return None

    def get_lead(self, lead_id: str) -> dict | None:
        idx = self._find_row_index(lead_id)
        if idx is None:
            return None
        row = self._ws.row_values(idx)
        return self._row_to_dict(row)

    def find_leads(self, **filters: Any) -> list[dict]:
        rows = self._all_rows()
        if len(rows) < 2:
            return []
        out: list[dict] = []
        for row in rows[1:]:
            if not row or not row[0]:
                continue
            d = self._row_to_dict(row)
            if all(str(d.get(k, "")) == str(v) for k, v in filters.items()):
                out.append(d)
        return out

    # ---- write -----------------------------------------------------------

    def _build_row(self, fields: dict[str, Any]) -> list[str]:
        return [str(fields.get(col, "") or "") for col in COLUMNS]

    def _batch_update_row(self, row_idx: int, fields: dict[str, Any]) -> None:
        """Write only the changed cells of a row in one batch_update call."""
        data = []
        for col_name, value in fields.items():
            if col_name not in COLUMNS:
                continue
            col_idx = COLUMNS.index(col_name) + 1
            a1 = rowcol_to_a1(row_idx, col_idx)
            data.append({"range": a1, "values": [[str(value) if value is not None else ""]]})
        if data:
            self._ws.batch_update(data)

    def upsert_lead(self, lead_id: str, fields: dict[str, Any]) -> None:
        if not lead_id:
            raise ValueError("lead_id required")
        self._connect()
        clean = {k: v for k, v in fields.items() if k in COLUMNS and k != "lead_id"}
        clean["last_updated"] = _utc_now_iso()
        idx = self._find_row_index(lead_id)
        if idx is None:
            new = {"lead_id": lead_id, **clean}
            self._ws.append_row(self._build_row(new), value_input_option="USER_ENTERED")
        else:
            self._batch_update_row(idx, clean)

    def update_status(
        self, lead_id: str, phase: str, status: str, note: str = ""
    ) -> None:
        if phase not in PHASES:
            raise ValueError(f"unknown phase: {phase!r} (valid: {sorted(PHASES)})")
        self._connect()
        idx = self._find_row_index(lead_id)
        ts = _utc_now_iso()
        existing_notes = ""
        if idx is not None:
            row = self._ws.row_values(idx)
            existing_notes = self._row_to_dict(row).get("notes", "")
        note_line = f"{ts} [{phase}] {status}"
        if note:
            note_line += f" — {note}"
        new_notes = f"{existing_notes}\n{note_line}".strip() if existing_notes else note_line
        fields = {
            f"{phase}_status": status,
            "notes": new_notes,
            "last_updated": ts,
        }
        if idx is None:
            new = {"lead_id": lead_id, **fields}
            self._ws.append_row(self._build_row(new), value_input_option="USER_ENTERED")
        else:
            self._batch_update_row(idx, fields)

    def append_error(self, lead_id: str, where: str, message: str) -> None:
        self._connect()
        idx = self._find_row_index(lead_id)
        ts = _utc_now_iso()
        existing = ""
        if idx is not None:
            row = self._ws.row_values(idx)
            existing = self._row_to_dict(row).get("error_log", "")
        line = f"{ts} [{where}] {message}"
        new_log = f"{existing}\n{line}".strip() if existing else line
        fields = {"error_log": new_log, "last_updated": ts}
        if idx is None:
            new = {"lead_id": lead_id, **fields}
            self._ws.append_row(self._build_row(new), value_input_option="USER_ENTERED")
        else:
            self._batch_update_row(idx, fields)

    # ---- bulk ------------------------------------------------------------

    def bulk_import_csv(self, csv_path: str | Path, dedupe_by: str = "email") -> int:
        """Upsert rows from Apollo CSV. Returns count of NEW inserts."""
        if dedupe_by not in COLUMNS:
            raise ValueError(f"dedupe_by must be a sheet column: {dedupe_by!r}")
        self._connect()
        existing = {
            row[COLUMNS.index(dedupe_by)]
            for row in self._all_rows()[1:]
            if len(row) > COLUMNS.index(dedupe_by) and row[COLUMNS.index(dedupe_by)]
        }
        inserted = 0
        for raw in iter_apollo_rows(csv_path):
            fields = row_to_fields(raw)
            key = fields.get(dedupe_by, "")
            if not key:
                logger.warning("skipping row missing dedupe key %r", dedupe_by)
                continue
            # lead_id: stable from dedupe key
            lead_id = f"apollo_{key}"
            if key in existing:
                # update fields only
                self.upsert_lead(lead_id, fields)
            else:
                self.upsert_lead(lead_id, fields)
                existing.add(key)
                inserted += 1
        return inserted

    # ---- test ------------------------------------------------------------

    def delete_lead(self, lead_id: str) -> bool:
        """Delete a row by lead_id. Returns True if deleted."""
        self._connect()
        idx = self._find_row_index(lead_id)
        if idx is None:
            return False
        self._ws.delete_rows(idx)
        return True
