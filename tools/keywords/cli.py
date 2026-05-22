"""Keywords CLI — generate keywords.json for one lead or batch."""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer

from tools.keywords.pipeline import build_keywords

app = typer.Typer(add_completion=False, help="NLP keyword pipeline.")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _slug_dir(out_root: Path, site_url: str, lead_id: str) -> Path:
    host = urlparse(site_url).hostname or lead_id
    return out_root / host.replace(".", "-")


@app.command("one")
def one(
    lead_id: str = typer.Option(..., "--lead-id"),
    business: str = typer.Option(..., "--business"),
    vertical: str = typer.Option(..., "--vertical"),
    site_url: str = typer.Option(..., "--site-url"),
    tagline: Optional[str] = typer.Option(None, "--tagline"),
    services: list[str] = typer.Option([], "--service"),
    out_root: Path = typer.Option(Path("data/outputs"), "--out-root"),
    max_pages: int = typer.Option(3, "--max-pages", min=1, max=10),
    skip_llm: bool = typer.Option(False, "--skip-llm"),
) -> None:
    """Generate keywords.json for one lead."""
    lead_dir = _slug_dir(out_root, site_url, lead_id)
    res = build_keywords(
        lead_id=lead_id, business=business, vertical=vertical,
        site_url=site_url, lead_dir=lead_dir,
        tagline=tagline, services=services or None,
        max_pages=max_pages, skip_llm=skip_llm,
    )
    typer.echo(json.dumps({
        "lead_id": res["lead_id"],
        "bucket_tokens": res["bucket_tokens"],
        "keywords": res["keywords"],
        "candidate_count": res["candidate_count"],
        "pages_fetched": res["diagnostics"]["pages_fetched"],
        "timings": res["diagnostics"]["timings"],
    }, indent=2))


@app.command("batch")
def batch(
    leads: Path = typer.Option(..., "--leads", exists=True, dir_okay=False),
    out_root: Path = typer.Option(Path("data/outputs"), "--out-root"),
    max_pages: int = typer.Option(3, "--max-pages", min=1, max=10),
    skip_llm: bool = typer.Option(False, "--skip-llm"),
) -> None:
    """Generate keywords.json for every lead in a CSV."""
    results = []
    with leads.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                lead_dir = _slug_dir(out_root, row.get("site_url", ""), row["lead_id"])
                services = [s.strip() for s in (row.get("services") or "").split("|") if s.strip()]
                res = build_keywords(
                    lead_id=row["lead_id"], business=row["business"], vertical=row["vertical"],
                    site_url=row["site_url"], lead_dir=lead_dir,
                    tagline=row.get("tagline") or None, services=services or None,
                    max_pages=max_pages, skip_llm=skip_llm,
                )
                results.append({
                    "lead_id": row["lead_id"], "ok": True,
                    "keywords": res["keywords"], "bucket_tokens": res["bucket_tokens"],
                })
            except Exception as exc:  # noqa: BLE001
                results.append({"lead_id": row["lead_id"], "ok": False, "error": str(exc)})
    typer.echo(json.dumps(results, indent=2))
