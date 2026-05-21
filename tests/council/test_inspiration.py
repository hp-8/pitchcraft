"""Tests for the inspiration agent."""
from __future__ import annotations

import json
from pathlib import Path

from tools.council.agents.inspiration import rank_moodboard

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "moodboard_sample.json"


def test_motion_first_ordering() -> None:
    out = rank_moodboard(FIXTURE, vertical="restaurant", style="modern")
    refs = out["top_refs"]
    assert len(refs) == 3
    # awwwards (animated + libs) should come before arena (static, no libs)
    sources_in_order = [r["source"] for r in refs]
    assert sources_in_order.index("awwwards") < sources_in_order.index("arena")
    # codrops (animated + libs) outranks arena too
    assert sources_in_order.index("codrops") < sources_in_order.index("arena")


def test_by_source_and_lib_distribution() -> None:
    out = rank_moodboard(FIXTURE, vertical="restaurant")
    assert out["by_source"]["awwwards"] == 1
    assert out["by_source"]["arena"] == 1
    assert "gsap" in out["motion_lib_distribution"]
    assert out["motion_lib_distribution"]["gsap"] == 1


def test_missing_path() -> None:
    out = rank_moodboard(None, vertical="restaurant")
    assert out["top_refs"] == []
    assert any("not supplied" in w for w in out["warnings"])


def test_nonexistent_path() -> None:
    out = rank_moodboard("/tmp/does-not-exist-xyz.json", vertical="restaurant")
    assert out["top_refs"] == []
    assert any("not found" in w for w in out["warnings"])


def test_top_n_caps_results(tmp_path: Path) -> None:
    # create a bigger fake moodboard
    items = [
        {
            "id": f"i{n}", "url": f"https://example.com/{n}", "image_url": f"img-{n}.png",
            "source": "arena", "has_animation": False, "libs_detected": [],
        }
        for n in range(20)
    ]
    path = tmp_path / "big.json"
    path.write_text(json.dumps({"items": items}))
    out = rank_moodboard(path, vertical="restaurant", top_n=5)
    assert len(out["top_refs"]) == 5


def test_dedupe_by_image_url(tmp_path: Path) -> None:
    items = [
        {"id": "a", "url": "u1", "image_url": "same.png", "source": "arena"},
        {"id": "b", "url": "u2", "image_url": "same.png", "source": "arena"},
        {"id": "c", "url": "u3", "image_url": "other.png", "source": "arena"},
    ]
    path = tmp_path / "dup.json"
    path.write_text(json.dumps({"items": items}))
    out = rank_moodboard(path, vertical="restaurant")
    assert len(out["top_refs"]) == 2
