"""Worker pool primitives — bounded asyncio semaphores per phase."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from tools.orchestrator._models import DEFAULT_CONCURRENCY

_CAPS_FILE = Path(".orchestrator/stitch_caps.json")


def load_caps() -> dict[str, int]:
    """Merge defaults w/ probed caps from .orchestrator/stitch_caps.json."""
    caps = dict(DEFAULT_CONCURRENCY)
    if _CAPS_FILE.exists():
        try:
            data = json.loads(_CAPS_FILE.read_text())
            recommended = int(data.get("recommended_concurrency", 0))
            if recommended > 0:
                caps["stitch_fulfill"] = recommended
        except Exception:
            pass
    return caps


def build_semaphores(caps: dict[str, int] | None = None) -> dict[str, asyncio.Semaphore]:
    caps = caps or load_caps()
    return {phase: asyncio.Semaphore(n) for phase, n in caps.items()}
