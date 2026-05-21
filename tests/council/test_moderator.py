"""Tests for the moderator (brief renderer)."""
from __future__ import annotations

from pathlib import Path

from tools.council.moderator import fuse
from tools.stitch._models import LeadContext


def _agent_outputs() -> dict:
    return {
        "brand_voice": {
            "audience": "Diners in Brooklyn.",
            "use_case": "Reserve a table and find the address.",
            "tone": "editorial",
            "one_liner": "Joe's Pizza — a Brooklyn kitchen.",
            "voice_attributes": ["warm", "place-rooted"],
        },
        "inspiration": {
            "top_refs": [
                {"title": "Kinetic landing", "source": "awwwards", "url": "https://a/1"},
                {"title": "Marquee card", "source": "codrops", "url": "https://b/2"},
            ],
            "by_source": {"awwwards": 1, "codrops": 1},
            "motion_lib_distribution": {"gsap": 1},
            "warnings": [],
        },
        "hallmark_picker": {
            "macrostructure": "Marquee Hero",
            "theme": "Bloom",
            "nav": "N5 Floating pill",
            "footer": "Ft5 Statement",
            "genre": "atmospheric",
            "axes": {"paper_band": "dark", "display_style": "display-serif", "accent_hue": "violet"},
            "rotation_note": "first-time pick",
        },
        "audit_ux": {
            "must_have_sections": ["primary CTA above fold + repeated in footer band", "phone in header + footer"],
            "per_page_requirements": {
                "landing": ["primary CTA mandatory above fold; repeat in footer band"],
                "services": [],
                "about": [],
                "contact": ["phone number visible in header and footer"],
            },
            "priority_problems": ["weak_cta"],
            "narrative": "Top audit pressures: weak_cta.",
        },
        "animation": {
            "per_page": {
                "landing": ["smooth_scroll", "kinetic_typography", "scroll_reveals"],
                "services": ["scroll_reveals"],
                "about": ["page_transition"],
                "contact": ["hover_micro"],
            },
            "libs_required": ["gsap", "lenis"],
            "reduced_motion_fallback": True,
            "reduced_motion_note": "prefers-reduced-motion: reduce",
        },
    }


def _lead() -> LeadContext:
    return LeadContext(
        lead_id="test-pizza",
        business="Joe's Pizza",
        vertical="restaurant",
        location="Brooklyn, NY",
        services=["pizza"],
    )


def test_renders_all_required_sections(tmp_path: Path) -> None:
    path, summary = fuse(_agent_outputs(), _lead(), tmp_path)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    for header in (
        "# Design Brief: Joe's Pizza",
        "## Pre-flight context",
        "## Audience",
        "## Use case",
        "## Tone",
        "## Genre",
        "## Macrostructure",
        "## Theme",
        "## Nav archetype",
        "## Footer archetype",
        "## Must-have sections",
        "## Page-specific requirements",
        "## Motion plan",
        "## Inspirational references",
        "## Honesty constraints",
        "## Hallmark slop-test gates",
    ):
        assert header in text, f"missing: {header}"
    assert summary["macrostructure"] == "Marquee Hero"


def test_honesty_constraints_block_present(tmp_path: Path) -> None:
    path, _ = fuse(_agent_outputs(), _lead(), tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "No fabricated metrics" in text
    assert "Jane Doe" in text


def test_motion_table_per_page(tmp_path: Path) -> None:
    path, _ = fuse(_agent_outputs(), _lead(), tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "| landing | smooth_scroll" in text
    assert "| contact | hover_micro" in text


def test_design_md_quoting(tmp_path: Path) -> None:
    design = tmp_path / "DESIGN.md"
    design.write_text(
        "# DESIGN\n\n## Palette\nprimary: #ff0000\n\n## Typography\nDisplay: Inter\n\n## Motion\nlibs: gsap\n",
        encoding="utf-8",
    )
    path, _ = fuse(_agent_outputs(), _lead(), tmp_path, design_md_path=design)
    text = path.read_text(encoding="utf-8")
    assert "primary: #ff0000" in text
    assert "Display: Inter" in text
    assert "libs: gsap" in text


def test_deterministic_output(tmp_path: Path) -> None:
    out1, _ = fuse(_agent_outputs(), _lead(), tmp_path / "a")
    out2, _ = fuse(_agent_outputs(), _lead(), tmp_path / "b")
    assert out1.read_text() == out2.read_text()
