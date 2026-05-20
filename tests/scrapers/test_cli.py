"""Tests for tools.scrapers.cli."""
from __future__ import annotations

from datetime import datetime, timezone

from tools.scrapers import cli
from tools.scrapers._models import ScraperItem, ScraperResult


def _make_result(source: str, items: list[ScraperItem]) -> ScraperResult:
    return ScraperResult(
        source=source,
        query="q",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )


def _item(source: str, _id: str, url: str, image: str | None, motion: bool = False) -> ScraperItem:
    return ScraperItem(
        id=_id, title=_id, url=url, image_url=image,
        source=source, has_animation=motion,
        libs_detected=["gsap"] if motion else [],
    )


def test_dedupe_by_image_and_url(monkeypatch):
    def make_fn(name, items):
        return lambda query, limit, use_cache: _make_result(name, items)

    dummy = {
        "arena": make_fn("arena", [
            _item("arena", "a1", "https://a.com/x", "https://img/1"),
        ]),
        "codrops": make_fn("codrops", [
            _item("codrops", "c1", "https://a.com/x", "https://img/1"),  # dup
            _item("codrops", "c2", "https://b.com/y", "https://img/2"),
        ]),
    }
    monkeypatch.setattr(cli, "SOURCES", dummy)
    payload = cli.run(vertical="restaurant", style="modern", limit=10)
    urls = [i["url"] for i in payload["items"]]
    assert urls.count("https://a.com/x") == 1
    assert "https://b.com/y" in urls


def test_motion_sort(monkeypatch):
    def make_fn(name, items):
        return lambda query, limit, use_cache: _make_result(name, items)

    dummy = {
        "arena": make_fn("arena", [
            _item("arena", "a1", "https://a.com/1", "https://img/1", motion=False),
            _item("arena", "a2", "https://a.com/2", "https://img/2", motion=True),
        ]),
    }
    monkeypatch.setattr(cli, "SOURCES", dummy)
    payload = cli.run(vertical="v", limit=10, include_motion=True)
    assert payload["items"][0]["id"] == "a2"


def test_error_in_one_does_not_break(monkeypatch):
    def bad(query, limit, use_cache):
        raise RuntimeError("boom")

    def good(query, limit, use_cache):
        return _make_result("good", [_item("good", "g1", "https://g/1", "https://img/g1")])

    monkeypatch.setattr(cli, "SOURCES", {"bad": bad, "good": good})
    payload = cli.run(vertical="v", limit=10)
    assert any(i["id"] == "g1" for i in payload["items"])
    assert payload["by_source"]["good"] >= 1


def test_source_only(monkeypatch):
    def make_fn(name):
        return lambda query, limit, use_cache: _make_result(
            name, [_item(name, f"{name}-1", f"https://{name}/1", f"https://img/{name}")]
        )

    monkeypatch.setattr(cli, "SOURCES", {"arena": make_fn("arena"), "codrops": make_fn("codrops")})
    payload = cli.run(vertical="v", limit=10, source_only="arena")
    assert all(i["source"] == "arena" for i in payload["items"])


def test_cap_to_limit(monkeypatch):
    big = [_item("x", f"x{i}", f"https://x/{i}", f"https://img/{i}") for i in range(50)]

    def fn(query, limit, use_cache):
        return _make_result("x", big)

    monkeypatch.setattr(cli, "SOURCES", {"x": fn})
    payload = cli.run(vertical="v", limit=5)
    assert len(payload["items"]) == 5


def test_build_queries():
    qs = cli.build_queries("dentist", "modern")
    assert len(qs) >= 3
    assert any("dentist" in q for q in qs)
