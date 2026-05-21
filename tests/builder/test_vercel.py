"""Tests for the Vercel CLI wrapper (mocked subprocess)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.builder._models import VercelNotInstalledError
from tools.builder._vercel import _parse_url, deploy


def test_parse_url_extracts_last_vercel_url() -> None:
    stdout = (
        "Deploying...\n"
        "Inspect: https://vercel.com/teamx/joes-pizza/inspect\n"
        "Production: https://joes-pizza-abc123.vercel.app\n"
    )
    assert _parse_url(stdout) == "https://joes-pizza-abc123.vercel.app"


def test_parse_url_returns_none_when_missing() -> None:
    assert _parse_url("nothing here") is None


def test_deploy_raises_when_vercel_missing(tmp_path: Path) -> None:
    with patch("tools.builder._vercel.shutil.which", return_value=None):
        with pytest.raises(VercelNotInstalledError):
            deploy(tmp_path, "joes-pizza", token="x")


def test_deploy_raises_when_token_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("VERCEL_TOKEN", raising=False)
    with patch("tools.builder._vercel.shutil.which", return_value="/usr/bin/vercel"):
        with pytest.raises(RuntimeError, match="VERCEL_TOKEN"):
            deploy(tmp_path, "joes-pizza")


def test_deploy_success_parses_url(tmp_path: Path) -> None:
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="Production: https://joes-pizza.vercel.app\n",
        stderr="",
    )
    with patch("tools.builder._vercel.shutil.which", return_value="/usr/bin/vercel"), \
        patch("tools.builder._vercel.subprocess.run", return_value=fake) as mrun:
        result = deploy(tmp_path, "joes-pizza", token="tkn")
    assert result.success
    assert result.url == "https://joes-pizza.vercel.app"
    # token forwarded
    args, kwargs = mrun.call_args
    assert kwargs["env"]["VERCEL_TOKEN"] == "tkn"
    assert "--prod" in args[0]


def test_deploy_failure_returns_error(tmp_path: Path) -> None:
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="Error: not authenticated",
    )
    with patch("tools.builder._vercel.shutil.which", return_value="/usr/bin/vercel"), \
        patch("tools.builder._vercel.subprocess.run", return_value=fake):
        result = deploy(tmp_path, "joes-pizza", token="tkn")
    assert not result.success
    assert "not authenticated" in (result.error or "")
