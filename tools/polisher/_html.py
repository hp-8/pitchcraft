"""BeautifulSoup helpers — stdlib html.parser only (no lxml dependency)."""
from __future__ import annotations

from bs4 import BeautifulSoup


def parse(html: str) -> BeautifulSoup:
    """Parse HTML with stdlib parser for portability."""
    return BeautifulSoup(html, "html.parser")


def render(soup: BeautifulSoup) -> str:
    return str(soup)


def ensure_head(soup: BeautifulSoup):
    """Return existing <head> or create one."""
    head = soup.find("head")
    if head is None:
        html = soup.find("html") or soup
        head = soup.new_tag("head")
        if html.contents:
            html.insert(0, head)
        else:
            html.append(head)
    return head


def ensure_body(soup: BeautifulSoup):
    body = soup.find("body")
    if body is None:
        html = soup.find("html") or soup
        body = soup.new_tag("body")
        html.append(body)
    return body
