"""Phase 6b: Stitch envelope fulfiller (state machine).

Pure-Python helpers that maintain envelope state. The actual MCP dispatch
(`mcp__stitch__generate_screen_from_text`, `mcp__stitch__get_screen`, etc.)
is performed by the Claude Code orchestrator session driving this module.

State machine per screen:
    fulfilled=false                            -> pending
    fulfilled=true,  error absent              -> ok
    fulfilled=true,  error present             -> failed

Envelope-level status (derived):
    any pending                                -> "queued"
    all fulfilled, any error                   -> "partial"
    all fulfilled, no error                    -> "ready"
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from tools.sheets.client import SheetsClient

__all__ = [
    "load_envelope",
    "save_envelope",
    "iter_pending_envelopes",
    "iter_pending_screens",
    "mark_screen_fulfilled",
    "mark_screen_error",
    "envelope_status",
    "finalize_envelope",
]


def load_envelope(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_envelope(path: str | Path, env: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(env, indent=2), encoding="utf-8")


def iter_pending_envelopes(out_root: str | Path = "data/outputs") -> list[Path]:
    """Envelope paths with >=1 unfulfilled screen, alphabetical."""
    out: list[Path] = []
    for env_path in sorted(Path(out_root).glob("*/stitch_screens_request.json")):
        try:
            env = load_envelope(env_path)
        except (OSError, json.JSONDecodeError):
            continue
        if any(not s.get("fulfilled") for s in env.get("screens", [])):
            out.append(env_path)
    return out


def iter_pending_screens(
    envelope_path: str | Path,
) -> Iterator[tuple[int, dict[str, Any]]]:
    """Yield (idx, screen_dict) for each unfulfilled screen in order."""
    env = load_envelope(envelope_path)
    for idx, screen in enumerate(env.get("screens", [])):
        if not screen.get("fulfilled"):
            yield idx, screen


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def mark_screen_fulfilled(
    envelope_path: str | Path,
    idx: int,
    result_payload: Any,
    *,
    html_content: str | bytes | None = None,
) -> None:
    """Persist Stitch result + flip fulfilled flag.

    Writes ``result_payload`` (JSON-serializable) to ``screen.target_path``.
    If ``html_content`` is provided, writes it alongside as ``<stem>.html``.
    """
    env_path = Path(envelope_path)
    env = load_envelope(env_path)
    screen = env["screens"][idx]
    target = Path(screen["target_path"])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
    if html_content is not None:
        html_path = target.with_suffix(".html")
        if isinstance(html_content, bytes):
            html_path.write_bytes(html_content)
        else:
            html_path.write_text(html_content, encoding="utf-8")
    screen["fulfilled"] = True
    screen["fulfilled_at"] = _now_iso()
    screen.pop("error", None)
    save_envelope(env_path, env)


def mark_screen_error(envelope_path: str | Path, idx: int, error: str) -> None:
    """Mark screen fulfilled with an error string; do not write target_path."""
    env_path = Path(envelope_path)
    env = load_envelope(env_path)
    screen = env["screens"][idx]
    screen["fulfilled"] = True
    screen["fulfilled_at"] = _now_iso()
    screen["error"] = error
    save_envelope(env_path, env)


def envelope_status(envelope_path: str | Path) -> str:
    """Return one of: queued | partial | ready."""
    env = load_envelope(envelope_path)
    screens = env.get("screens", [])
    if not screens or any(not s.get("fulfilled") for s in screens):
        return "queued"
    if any(s.get("error") for s in screens):
        return "partial"
    return "ready"


def finalize_envelope(
    envelope_path: str | Path,
    sheets_client: "SheetsClient | None" = None,
) -> str:
    """Stamp final status onto envelope; optionally update master sheet."""
    env_path = Path(envelope_path)
    env = load_envelope(env_path)
    status = envelope_status(env_path)
    env["status"] = status
    env["finalized_at"] = _now_iso()
    save_envelope(env_path, env)
    if sheets_client is not None and status in ("ready", "partial"):
        screens = env.get("screens", [])
        ok = sum(1 for s in screens if s.get("fulfilled") and not s.get("error"))
        sheets_client.upsert_lead(
            env["lead_id"],
            {"stitch_status": status, "stitch_variants_url": str(env_path)},
        )
        sheets_client.update_status(
            env["lead_id"],
            "stitch",
            status,
            note=f"fulfilled {ok}/{len(screens)}",
        )
    return status
