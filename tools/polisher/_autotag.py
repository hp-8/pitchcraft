"""Autotag pass — add data-reveal / data-split / data-magnetic / data-marquee / data-parallax.

Idempotent: running twice produces the same DOM.
"""
from __future__ import annotations

from bs4 import BeautifulSoup, Tag

_SKIP_ANCESTORS = {"nav", "header", "footer"}
_HEADING_LIMIT = 6


def _has_ancestor(tag: Tag, names: set[str]) -> bool:
    parent = tag.parent
    while parent is not None and getattr(parent, "name", None):
        if parent.name in names:
            return True
        parent = parent.parent
    return False


def _tag_section(el: Tag) -> bool:
    if el.has_attr("data-reveal"):
        return False
    el["data-reveal"] = "fade-up"
    return True


def _tag_heading(el: Tag, kind: str) -> bool:
    if el.has_attr("data-split"):
        return False
    el["data-split"] = kind
    return True


def _tag_button(el: Tag) -> bool:
    if el.has_attr("data-magnetic"):
        return False
    el["data-magnetic"] = ""
    return True


def _tag_marquee(el: Tag) -> bool:
    if el.has_attr("data-marquee"):
        return False
    el["data-marquee"] = ""
    return True


def _tag_parallax(el: Tag) -> bool:
    if el.has_attr("data-parallax"):
        return False
    el["data-parallax"] = "0.3"
    return True


def autotag(soup: BeautifulSoup) -> dict[str, int]:
    """Apply autotag heuristics in place. Returns count per tag type."""
    counts = {"reveal": 0, "split": 0, "magnetic": 0, "marquee": 0, "parallax": 0}

    # Section reveals
    section_selectors = ["section", "article"]
    seen_sections: set[int] = set()
    for sel in section_selectors:
        for el in soup.find_all(sel):
            if id(el) in seen_sections:
                continue
            if _has_ancestor(el, _SKIP_ANCESTORS):
                continue
            seen_sections.add(id(el))
            if _tag_section(el):
                counts["reveal"] += 1
    # div.section
    for el in soup.find_all("div", class_="section"):
        if _has_ancestor(el, _SKIP_ANCESTORS):
            continue
        if _tag_section(el):
            counts["reveal"] += 1
    # top-level main > *
    main = soup.find("main")
    if main is not None:
        for el in main.find_all(recursive=False):
            if not isinstance(el, Tag):
                continue
            if el.name in _SKIP_ANCESTORS:
                continue
            if _tag_section(el):
                counts["reveal"] += 1

    # Headings (first N)
    heading_count = 0
    for el in soup.find_all(["h1", "h2", "h3"]):
        if heading_count >= _HEADING_LIMIT:
            break
        if _has_ancestor(el, _SKIP_ANCESTORS):
            continue
        kind = "words" if el.name == "h3" else "lines"
        if _tag_heading(el, kind):
            counts["split"] += 1
            heading_count += 1

    # Buttons / btn anchors
    for el in soup.find_all("button"):
        if _tag_button(el):
            counts["magnetic"] += 1
    for el in soup.find_all("a"):
        cls = el.get("class") or []
        if isinstance(cls, str):
            cls = cls.split()
        if any(c in ("btn", "button") for c in cls):
            if _tag_button(el):
                counts["magnetic"] += 1

    # Logo strips: ul/div containing 5+ img
    for el in soup.find_all(["ul", "div"]):
        imgs = el.find_all("img", recursive=True)
        if len(imgs) >= 5 and not _has_ancestor(el, _SKIP_ANCESTORS):
            if _tag_marquee(el):
                counts["marquee"] += 1

    # Parallax: first hero img/video in first non-nav section
    first_section = None
    for sel in ("section", "article"):
        for cand in soup.find_all(sel):
            if _has_ancestor(cand, _SKIP_ANCESTORS):
                continue
            first_section = cand
            break
        if first_section is not None:
            break
    if first_section is not None:
        media = first_section.find(["img", "video"])
        if media is not None and _tag_parallax(media):
            counts["parallax"] += 1

    return counts
