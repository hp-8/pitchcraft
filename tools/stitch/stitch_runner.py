"""Stitch MCP boundary stub.

Stitch is exposed only as MCP tools inside a Claude Code session
(`mcp__stitch__create_design_system_from_design_md`, etc.). Plain Python
processes cannot invoke MCP tools, so this module exists purely to:

1. Document the interface the orchestrator promises to honor.
2. Give the design-ref agent something importable + mockable in tests.
3. Fail loudly if called from a non-orchestrator context.

The Phase 10 orchestrator will read `stitch_request.json` artifacts and
dispatch the corresponding MCP calls via Claude Code. See
``stitch_runner.md`` (alongside this file) for the dispatch contract.
"""
from __future__ import annotations

from typing import Any, Dict


def create_design_system(name: str, design_md_path: str) -> Dict[str, Any]:
    """Stub. The real call lives in the Claude Code orchestrator.

    Args:
        name: Human-readable name for the Stitch design system.
        design_md_path: Filesystem path to the DESIGN.md to upload.

    Raises:
        NotImplementedError: Always — see module docstring.
    """
    raise NotImplementedError(
        "Stitch MCP calls must be made by the Claude Code orchestrator, "
        "not Python. See stitch_runner.md."
    )
