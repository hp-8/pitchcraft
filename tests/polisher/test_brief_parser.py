"""Brief parser tests."""
from pathlib import Path

from tools.polisher._brief_parser import parse_brief

FIXTURE = Path(__file__).parent.parent / "fixtures" / "design_brief_sample.md"


def test_parse_brief_extracts_core_fields():
    s = parse_brief(FIXTURE)
    assert s.business == "Joe's Pizza"
    assert s.vertical == "restaurant"
    assert s.genre == "editorial"
    assert s.macrostructure == "Bento Grid"
    assert s.theme == "Specimen"
    assert s.paper_band == "light"
    assert s.display_style == "italic-serif"
    assert s.accent_hue == "warm"
    assert s.nav.startswith("N1")
    assert s.footer.startswith("Ft")


def test_parse_brief_motion_table():
    s = parse_brief(FIXTURE)
    assert "landing" in s.per_page_motion
    assert "smooth_scroll" in s.per_page_motion["landing"]
    assert "gsap" in s.libs_required


def test_parse_brief_handles_missing(tmp_path: Path):
    p = tmp_path / "nope.md"
    s = parse_brief(p)
    assert s.business == ""
    assert s.theme == ""
    assert s.per_page_motion == {}


def test_parse_brief_page_transitions_and_mesh():
    s = parse_brief(FIXTURE)
    # about page lists page_transition; landing lists depth
    assert s.page_transitions is True
    assert s.gradient_mesh is True
