"""Tests for the hallmark_picker agent."""
from __future__ import annotations

import json
from pathlib import Path

from tools.council.agents.hallmark_picker import (
    GENRE_THEMES,
    MACROSTRUCTURES,
    THEMES,
    infer_genre,
    pick_macrostructure_and_theme,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "hallmark_log_sample.json"


def test_first_time_pick_creates_log(tmp_path: Path) -> None:
    log = tmp_path / "log.json"
    out = pick_macrostructure_and_theme("editorial", log_path=log)
    assert out["macrostructure"] in MACROSTRUCTURES
    assert out["theme"] in THEMES
    assert log.exists()
    entries = json.loads(log.read_text())
    assert len(entries) == 1
    assert entries[0]["macrostructure"] == out["macrostructure"]


def test_macrostructure_diversification(tmp_path: Path) -> None:
    log = tmp_path / "log.json"
    # seed with last 3 picks
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(FIXTURE.read_text())
    out = pick_macrostructure_and_theme("editorial", log_path=log, append=False)
    recent = {"Bento Grid", "Long Document", "Marquee Hero"}
    assert out["macrostructure"] not in recent


def test_genre_scoping_atmospheric(tmp_path: Path) -> None:
    log = tmp_path / "log.json"
    out = pick_macrostructure_and_theme("atmospheric", log_path=log)
    assert out["theme"] in GENRE_THEMES["atmospheric"]


def test_genre_scoping_modern_minimal(tmp_path: Path) -> None:
    log = tmp_path / "log.json"
    out = pick_macrostructure_and_theme("modern-minimal", log_path=log)
    assert out["theme"] in GENRE_THEMES["modern-minimal"]


def test_genre_scoping_playful(tmp_path: Path) -> None:
    log = tmp_path / "log.json"
    out = pick_macrostructure_and_theme("playful", log_path=log)
    assert out["theme"] in GENRE_THEMES["playful"]


def test_unknown_genre_falls_back_to_editorial(tmp_path: Path) -> None:
    log = tmp_path / "log.json"
    out = pick_macrostructure_and_theme("nonsense", log_path=log)
    assert out["genre"] == "editorial"
    assert out["theme"] in GENRE_THEMES["editorial"]


def test_log_trimmed_to_20(tmp_path: Path) -> None:
    log = tmp_path / "log.json"
    log.write_text(json.dumps([{"macrostructure": f"m{i}", "theme": "Atelier"} for i in range(30)]))
    pick_macrostructure_and_theme("editorial", log_path=log)
    entries = json.loads(log.read_text())
    assert len(entries) == 20


def test_nav_and_footer_differ_from_last(tmp_path: Path) -> None:
    log = tmp_path / "log.json"
    log.write_text(json.dumps([{"macrostructure": "X", "theme": "Atelier", "nav": "N1", "footer": "Ft1"}]))
    out = pick_macrostructure_and_theme("editorial", log_path=log, append=False)
    assert not out["nav"].startswith("N1 ")
    assert not out["footer"].startswith("Ft1 ")


def test_infer_genre_from_tone() -> None:
    assert infer_genre("editorial") == "editorial"
    assert infer_genre("luxury") == "editorial"
    assert infer_genre("technical") == "modern-minimal"
    assert infer_genre("playful") == "playful"
    assert infer_genre(None, vertical="dental") == "modern-minimal"
    assert infer_genre(None, vertical="restaurant") == "editorial"


def test_theme_axes_differ(tmp_path: Path) -> None:
    """Pick after Specimen should differ on at least 1 axis."""
    log = tmp_path / "log.json"
    log.write_text(json.dumps([{"macrostructure": "Bento Grid", "theme": "Specimen", "nav": "N1", "footer": "Ft1"}]))
    out = pick_macrostructure_and_theme("editorial", log_path=log, append=False)
    spec_axes = THEMES["Specimen"]
    new_axes = THEMES[out["theme"]]
    diffs = sum(1 for k in ("paper_band", "display_style", "accent_hue") if spec_axes[k] != new_axes[k])
    assert diffs >= 1
