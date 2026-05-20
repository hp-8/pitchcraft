"""Shared SQLite cache for scrapers.

Schema:
    cache(source TEXT, query TEXT, fetched_at TEXT, payload JSON,
          PRIMARY KEY (source, query))
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Union

DEFAULT_DB_PATH = Path("data/cache/scrapers.db")
DEFAULT_TTL_SECONDS = 24 * 60 * 60
DEFAULT_TTL = timedelta(seconds=DEFAULT_TTL_SECONDS)


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Create cache table if it doesn't exist."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                source TEXT NOT NULL,
                query TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (source, query)
            )
            """
        )
        conn.commit()


def get(
    source: str,
    query: str,
    ttl_seconds: Union[int, timedelta] = DEFAULT_TTL_SECONDS,
    db_path: Optional[Path] = None,
) -> Optional[dict[str, Any]]:
    """Return cached payload dict if fresh (within ttl_seconds), else None."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    ttl = ttl_seconds if isinstance(ttl_seconds, timedelta) else timedelta(seconds=ttl_seconds)
    init_db(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT fetched_at, payload FROM cache WHERE source=? AND query=?",
            (source, query),
        ).fetchone()
    if row is None:
        return None
    try:
        fetched_at = datetime.fromisoformat(row["fetched_at"])
    except ValueError:
        return None
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - fetched_at > ttl:
        return None
    return json.loads(row["payload"])


def set(  # noqa: A001 - public API name
    source: str,
    query: str,
    payload: dict[str, Any],
    db_path: Optional[Path] = None,
) -> None:
    """Write payload to cache, replacing existing row for (source, query)."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    init_db(db_path)
    fetched_at = payload.get("fetched_at") or datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO cache (source, query, fetched_at, payload)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source, query) DO UPDATE SET
                fetched_at=excluded.fetched_at,
                payload=excluded.payload
            """,
            (source, query, fetched_at, json.dumps(payload)),
        )
        conn.commit()
