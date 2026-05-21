"""Autotag tests."""
from tools.polisher._autotag import autotag
from tools.polisher._html import parse


def test_autotag_sections_and_headings():
    html = """
    <html><body>
    <nav><a href="/">Home</a></nav>
    <header><h1>Skipped</h1></header>
    <main>
      <section><h1>Title</h1><p>x</p></section>
      <article><h2>Story</h2></article>
    </main>
    <footer><a href="/">Footer</a></footer>
    </body></html>
    """
    soup = parse(html)
    counts = autotag(soup)
    assert counts["reveal"] >= 2
    # section + article have data-reveal
    assert soup.find("section").get("data-reveal") == "fade-up"
    # heading inside header skipped
    assert not soup.select_one("header h1").has_attr("data-split")
    # heading inside section tagged
    assert soup.select_one("section h1").get("data-split") == "lines"
    assert counts["split"] >= 2


def test_autotag_buttons_and_marquee():
    html = """
    <html><body>
    <section>
      <button>Click</button>
      <a class="btn" href="/x">Buy</a>
      <ul>
        <li><img src="a.png"></li>
        <li><img src="b.png"></li>
        <li><img src="c.png"></li>
        <li><img src="d.png"></li>
        <li><img src="e.png"></li>
      </ul>
    </section>
    </body></html>
    """
    soup = parse(html)
    counts = autotag(soup)
    assert counts["magnetic"] == 2
    assert counts["marquee"] == 1
    assert soup.find("ul").has_attr("data-marquee")


def test_autotag_idempotent():
    html = "<html><body><section><h1>X</h1></section></body></html>"
    soup = parse(html)
    autotag(soup)
    rendered_once = str(soup)
    counts2 = autotag(soup)
    assert counts2["reveal"] == 0
    assert counts2["split"] == 0
    assert str(soup) == rendered_once


def test_autotag_parallax_on_first_section_media():
    html = """
    <html><body>
    <section><img src="hero.jpg"></section>
    <section><img src="x.jpg"></section>
    </body></html>
    """
    soup = parse(html)
    counts = autotag(soup)
    assert counts["parallax"] == 1
    imgs = soup.find_all("img")
    assert imgs[0].has_attr("data-parallax")
    assert not imgs[1].has_attr("data-parallax")
