"""Tests for agents.design_ref."""
from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from pydantic import ValidationError

from agents.design_ref import _color_extract, _llm, _render, agent
from agents.design_ref._models import (
    ColorPalette,
    DesignSpec,
    Moodboard,
    MoodboardItem,
    TypographySpec,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
MOODBOARD = FIXTURES / "moodboard_sample.json"
SWATCH = FIXTURES / "swatch.png"


# --------------------------- model validation ---------------------------

def test_moodboard_valid():
    raw = json.loads(MOODBOARD.read_text())
    m = Moodboard.model_validate(raw)
    assert m.vertical == "restaurant"
    assert m.style == "modern"
    assert len(m.items) == 3
    assert m.items[1].has_animation is True
    assert "gsap" in m.items[1].libs_detected


def test_moodboard_invalid_missing_required():
    with pytest.raises(ValidationError):
        Moodboard.model_validate({"vertical": "restaurant"})  # no style


def test_moodboard_item_invalid_no_url():
    with pytest.raises(ValidationError):
        MoodboardItem.model_validate({"id": "x", "source": "arena"})  # no url


# --------------------------- render ---------------------------

def _sample_spec() -> DesignSpec:
    items = [
        MoodboardItem(
            id="a1", title="Arena ref", url="https://a", source="arena",
        ),
        MoodboardItem(
            id="aw1", title="Animated", url="https://aw", source="awwwards",
            libs_detected=["gsap"], has_animation=True,
        ),
    ]
    return DesignSpec(
        vertical="restaurant",
        style="modern",
        slug="restaurant-modern-test",
        brand_mood="Warm, editorial, confident.",
        palette=ColorPalette(),
        typography=TypographySpec(),
        component_patterns=["Hero", "Marquee"],
        motion_references=[items[1]],
        image_direction="Daylight, candid.",
        all_references=items,
    )


def test_render_design_md_has_all_sections():
    md = _render.render_design_md(_sample_spec())
    required = [
        "# Design System: Restaurant — Modern",
        "## Brand mood",
        "## Color palette",
        "## Typography",
        "## Spacing & radius",
        "## Component patterns",
        "## Motion section (NON-NEGOTIABLE",
        "Smooth scroll: Lenis",
        "At least 1 marquee",
        "Intro loader",
        "## Image direction",
        "## Inspirational references",
        "### arena",
        "### awwwards",
        "libs: gsap",
    ]
    for needle in required:
        assert needle in md, f"missing section: {needle!r}"


# --------------------------- color extraction ---------------------------

def test_kmeans_palette_on_synthetic_image():
    img = Image.new("RGB", (40, 40), (255, 0, 0))
    for x in range(20):
        for y in range(40):
            img.putpixel((x, y), (0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    palette = _color_extract.kmeans_palette(buf.getvalue(), k=3)
    assert len(palette) >= 2
    # All hex strings
    for c in palette:
        assert c.startswith("#") and len(c) == 7
    # Should include something close to red and blue
    joined = " ".join(palette)
    assert any(c.startswith("#ff") or c.startswith("#fe") for c in palette) or "ff00" in joined


def test_aggregate_palettes_dedups():
    out = _color_extract.aggregate_palettes(
        [["#ff0000", "#00ff00"], ["#00ff00", "#0000ff"]]
    )
    assert out == ["#ff0000", "#00ff00", "#0000ff"]


# --------------------------- LLM wrapper ---------------------------

def test_synthesize_design_notes_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(_llm.LLMError) as exc:
        _llm.synthesize_design_notes(
            {"vertical": "r", "style": "m", "palette": [], "libs": [], "items": []}
        )
    assert "GEMINI_API_KEY" in str(exc.value)


def test_synthesize_design_notes_happy_path(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    fake_resp = MagicMock()
    fake_resp.text = json.dumps(
        {
            "mood": "moody",
            "typography_block": "Display: X",
            "image_direction": "soft light",
            "component_patterns": ["hero", "marquee"],
        }
    )
    fake_model = MagicMock()
    fake_model.generate_content.return_value = fake_resp
    fake_genai = MagicMock()
    fake_genai.GenerativeModel.return_value = fake_model

    with patch.dict("sys.modules", {"google.generativeai": fake_genai}):
        out = _llm.synthesize_design_notes(
            {"vertical": "r", "style": "m", "palette": ["#fff"], "libs": ["gsap"], "items": []}
        )
    assert out["mood"] == "moody"
    assert out["component_patterns"] == ["hero", "marquee"]


def test_synthesize_design_notes_strips_fences(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    fake_resp = MagicMock()
    fake_resp.text = "```json\n{\"mood\":\"ok\",\"typography_block\":\"x\",\"image_direction\":\"y\",\"component_patterns\":[]}\n```"
    fake_model = MagicMock()
    fake_model.generate_content.return_value = fake_resp
    fake_genai = MagicMock()
    fake_genai.GenerativeModel.return_value = fake_model

    with patch.dict("sys.modules", {"google.generativeai": fake_genai}):
        out = _llm.synthesize_design_notes(
            {"vertical": "r", "style": "m", "palette": [], "libs": [], "items": []}
        )
    assert out["mood"] == "ok"


# --------------------------- end-to-end build ---------------------------

def test_build_design_system_e2e(tmp_path):
    result = agent.build_design_system(
        moodboard_path=MOODBOARD,
        out_dir=tmp_path,
        skip_llm=True,
        skip_colors=True,
    )
    out = Path(result["out_dir"])
    assert out.is_dir()
    design_md = Path(result["design_md_path"])
    assert design_md.exists()
    text = design_md.read_text()
    assert "Motion section" in text
    assert "Smooth scroll: Lenis" in text

    req = json.loads(Path(result["stitch_request_path"]).read_text())
    assert req["tool"] == "create_design_system_from_design_md"
    assert req["args"]["design_md_path"].endswith("DESIGN.md")
    assert req["fulfilled"] is False

    record = json.loads(Path(result["stitch_record_path"]).read_text())
    assert record["id"] is None  # stub raised NotImplementedError
    assert "Stitch MCP" in (record["error"] or "")
    assert record["source_design_md_path"].endswith("DESIGN.md")


def test_stitch_runner_stub_raises():
    from tools.stitch import stitch_runner

    with pytest.raises(NotImplementedError) as exc:
        stitch_runner.create_design_system(name="x", design_md_path="/tmp/x.md")
    assert "orchestrator" in str(exc.value)
