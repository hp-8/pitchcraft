"""Pydantic models for the prototype builder."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str
    site_dir: str
    pages: list[str]
    deploy_url: str | None = None
    deploy_id: str | None = None
    deployed_at: str | None = None
    skipped_deploy: bool = False
    errors: list[str] = []


class DeployResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    deploy_id: str | None = None
    raw_stdout: str = ""
    success: bool = False
    error: str | None = None


class VercelNotInstalledError(RuntimeError):
    """Raised when the `vercel` CLI is not installed on PATH."""
