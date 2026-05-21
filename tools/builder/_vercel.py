"""Vercel CLI wrapper. No network calls happen in tests (mock subprocess)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from tools.builder._models import DeployResult, VercelNotInstalledError

_URL_RE = re.compile(r"https://[A-Za-z0-9._-]+\.vercel\.app[^\s]*")


def _parse_url(stdout: str) -> str | None:
    matches = _URL_RE.findall(stdout or "")
    return matches[-1].rstrip(".,") if matches else None


def deploy(
    site_dir: str | Path,
    project_name: str,
    token: str | None = None,
    timeout: int = 600,
) -> DeployResult:
    """Run `vercel deploy --prod --yes --name <project_name>` from site_dir."""
    if shutil.which("vercel") is None:
        raise VercelNotInstalledError(
            "vercel CLI not found on PATH. Install with: npm i -g vercel"
        )
    tok = token or os.getenv("VERCEL_TOKEN") or ""
    if not tok:
        raise RuntimeError(
            "VERCEL_TOKEN missing. Set it in .env or pass token= to deploy()."
        )

    env = {**os.environ, "VERCEL_TOKEN": tok}
    cmd = [
        "vercel",
        "deploy",
        "--prod",
        "--yes",
        "--name",
        project_name,
        "--token",
        tok,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(site_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return DeployResult(
            url="",
            raw_stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            success=False,
            error=f"timeout after {timeout}s",
        )

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    url = _parse_url(combined) or ""
    if proc.returncode != 0:
        return DeployResult(
            url=url,
            raw_stdout=combined,
            success=False,
            error=f"vercel exit {proc.returncode}: {(proc.stderr or '').strip()[:500]}",
        )
    return DeployResult(
        url=url,
        deploy_id=None,
        raw_stdout=combined,
        success=bool(url),
        error=None if url else "no vercel.app URL found in stdout",
    )
