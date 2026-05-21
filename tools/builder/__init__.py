"""Prototype builder — static multi-page site assembly + Vercel deploy."""
from tools.builder._models import BuildResult, DeployResult
from tools.builder.prototype import build_prototype

__all__ = ["BuildResult", "DeployResult", "build_prototype"]
