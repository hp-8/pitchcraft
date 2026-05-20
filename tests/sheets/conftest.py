"""Shared sheets test fixtures: fake gspread worksheet + client."""
from __future__ import annotations

from typing import Any

import gspread
import pytest

from tools.sheets import client as client_mod
from tools.sheets._schema import COLUMNS


class FakeWorksheet:
    def __init__(self, title: str = "leads", rows: list[list[str]] | None = None):
        self.title = title
        self.rows: list[list[str]] = rows if rows is not None else []
        self.batch_calls: list[list[dict]] = []
        self.appended: list[list[str]] = []

    def _ensure_width(self, row: list[str]) -> list[str]:
        return list(row) + [""] * max(0, len(COLUMNS) - len(row))

    def row_values(self, idx: int) -> list[str]:
        if idx < 1 or idx > len(self.rows):
            return []
        return list(self.rows[idx - 1])

    def get_all_values(self) -> list[list[str]]:
        return [list(r) for r in self.rows]

    def append_row(self, row: list[str], value_input_option: str = "RAW") -> None:
        self.appended.append(list(row))
        self.rows.append(self._ensure_width(row))

    def update(self, a1: str, values: list[list[str]]) -> None:
        # only used by ensure_schema for header row, A1:??1
        if a1.startswith("A1:") or a1 == "A1":
            if not self.rows:
                self.rows.append(list(values[0]))
            else:
                self.rows[0] = list(values[0])
        else:
            raise NotImplementedError(f"FakeWorksheet.update({a1})")

    def batch_update(self, data: list[dict]) -> None:
        self.batch_calls.append(list(data))
        for entry in data:
            a1 = entry["range"]
            val = entry["values"][0][0]
            # parse a1 like "C5"
            col_letters = "".join(c for c in a1 if c.isalpha())
            row_num = int("".join(c for c in a1 if c.isdigit()))
            col_idx = 0
            for c in col_letters:
                col_idx = col_idx * 26 + (ord(c.upper()) - ord("A") + 1)
            # ensure row exists & wide enough
            while len(self.rows) < row_num:
                self.rows.append([""] * len(COLUMNS))
            row = self.rows[row_num - 1]
            while len(row) < col_idx:
                row.append("")
            row[col_idx - 1] = val
            self.rows[row_num - 1] = row

    def delete_rows(self, idx: int) -> None:
        if 1 <= idx <= len(self.rows):
            self.rows.pop(idx - 1)


class FakeSpreadsheet:
    def __init__(self, ws: FakeWorksheet):
        self._ws = ws
        self._added: list[str] = []

    def worksheet(self, name: str) -> FakeWorksheet:
        if self._ws.title == name:
            return self._ws
        raise gspread.WorksheetNotFound(name)

    def add_worksheet(self, title: str, rows: int, cols: int) -> FakeWorksheet:
        self._ws = FakeWorksheet(title=title)
        self._added.append(title)
        return self._ws


class FakeGspreadClient:
    def __init__(self, ss: FakeSpreadsheet):
        self._ss = ss

    def open_by_key(self, key: str) -> FakeSpreadsheet:
        return self._ss


@pytest.fixture
def fake_ws() -> FakeWorksheet:
    return FakeWorksheet(title="leads")


@pytest.fixture
def fake_ss(fake_ws: FakeWorksheet) -> FakeSpreadsheet:
    return FakeSpreadsheet(fake_ws)


@pytest.fixture
def sheets_client(monkeypatch, fake_ss, tmp_path) -> Any:
    """SheetsClient wired to fakes, with env stubbed."""
    creds = tmp_path / "sa.json"
    creds.write_text("{}")
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", str(creds))
    monkeypatch.setenv("GOOGLE_SHEETS_SPREADSHEET_ID", "fake-id")
    monkeypatch.setattr(
        client_mod.gspread, "service_account", lambda filename: FakeGspreadClient(fake_ss)
    )
    sc = client_mod.SheetsClient()
    return sc
