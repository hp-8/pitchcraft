"""Animation wiring — CDN tags + shared prototype.js generator."""
from __future__ import annotations

from bs4 import BeautifulSoup

from tools.polisher._html import ensure_body, ensure_head
from tools.polisher._models import BriefSummary

CDN_LIBS = [
    ("lenis", "https://cdn.jsdelivr.net/gh/studio-freight/lenis@1.0.42/bundled/lenis.min.js"),
    ("gsap", "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"),
    ("ScrollTrigger", "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"),
    ("splitting", "https://cdn.jsdelivr.net/npm/splitting/dist/splitting.min.js"),
]
SPLITTING_CSS = "https://cdn.jsdelivr.net/npm/splitting/dist/splitting.css"

INJECTION_MARKER = "polisher-animation-cdn"


def _strip_scroll_smooth(soup: BeautifulSoup) -> None:
    """Tailwind ships `<html class='scroll-smooth'>` which fights Lenis. Remove it."""
    html = soup.find("html")
    if html is None:
        return
    cls = html.get("class") or []
    if isinstance(cls, str):
        cls = cls.split()
    cls = [c for c in cls if c != "scroll-smooth"]
    if cls:
        html["class"] = cls
    elif "class" in html.attrs:
        del html["class"]


def _inject_intro_curtain(soup: BeautifulSoup, brand: str) -> None:
    body = ensure_body(soup)
    if soup.find(attrs={"data-polisher-curtain": "1"}):
        return
    curtain = soup.new_tag("div")
    curtain["data-polisher-curtain"] = "1"
    curtain["class"] = "polisher-curtain"
    inner = soup.new_tag("div")
    inner["class"] = "polisher-curtain__inner"
    wordmark = soup.new_tag("span")
    wordmark["class"] = "polisher-curtain__wordmark"
    wordmark.string = (brand or "").upper() or "·"
    bar = soup.new_tag("span")
    bar["class"] = "polisher-curtain__bar"
    inner.append(wordmark)
    inner.append(bar)
    curtain.append(inner)
    body.insert(0, curtain)


def inject_cdn(soup: BeautifulSoup, brand: str | None = None) -> list[str]:
    """Add CDN scripts before </body> + splitting.css + intro curtain. Idempotent."""
    _strip_scroll_smooth(soup)

    libs_loaded: list[str] = []
    if soup.find(attrs={"data-polisher-cdn": INJECTION_MARKER}):
        _inject_intro_curtain(soup, brand or "")
        return [name for name, _ in CDN_LIBS]

    head = ensure_head(soup)
    body = ensure_body(soup)

    css_link = soup.new_tag("link", rel="stylesheet", href=SPLITTING_CSS)
    css_link["data-polisher-cdn"] = INJECTION_MARKER
    head.append(css_link)
    proto_css = soup.new_tag("link", rel="stylesheet", href="/assets/prototype.css")
    proto_css["data-polisher-cdn"] = INJECTION_MARKER
    head.append(proto_css)

    _inject_intro_curtain(soup, brand or "")

    for name, url in CDN_LIBS:
        tag = soup.new_tag("script", src=url)
        tag["data-polisher-cdn"] = INJECTION_MARKER
        body.append(tag)
        libs_loaded.append(name)

    proto_js = soup.new_tag("script", src="/assets/prototype.js", defer="")
    proto_js["data-polisher-cdn"] = INJECTION_MARKER
    body.append(proto_js)
    return libs_loaded


_PROTOTYPE_JS_TEMPLATE = r"""/* polisher: animation primitives — generated */
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var doc = document.documentElement;
  doc.classList.add('is-loading');

  // --- Intro curtain ---------------------------------------------------------
  function killAllCurtains() {
    document.querySelectorAll('.polisher-curtain').forEach(function (c) {
      c.parentNode && c.parentNode.removeChild(c);
    });
    doc.classList.remove('is-loading');
    doc.classList.add('is-ready');
  }
  function dismissCurtain() {
    var curtain = document.querySelector('[data-polisher-curtain]');
    doc.classList.remove('is-loading');
    doc.classList.add('is-ready');
    if (curtain) {
      curtain.classList.add('is-out');
      setTimeout(function () { curtain.parentNode && curtain.parentNode.removeChild(curtain); }, 900);
    }
  }
  window.addEventListener('load', function () { setTimeout(dismissCurtain, reduce ? 200 : 600); });
  setTimeout(dismissCurtain, 2500); // safety fallback
  // bfcache restore: wipe any leftover curtain instantly
  window.addEventListener('pageshow', function (e) { if (e.persisted) killAllCurtains(); });
  // before navigating away, strip transition curtain so bfcache doesn't keep it
  window.addEventListener('pagehide', function () {
    document.querySelectorAll('.polisher-curtain--out').forEach(function (c) {
      c.parentNode && c.parentNode.removeChild(c);
    });
  });

  // --- Lenis smooth scroll (driven by gsap.ticker; fallback RAF if no gsap) -
  var lenis = null;
  if (!reduce && window.Lenis) {
    lenis = new window.Lenis({
      duration: 1.25,
      easing: function (t) { return Math.min(1, 1.001 - Math.pow(2, -10 * t)); },
      smoothWheel: true,
      smoothTouch: false
    });
    if (!(window.gsap && window.ScrollTrigger)) {
      function lenisRaf(time) { lenis.raf(time); requestAnimationFrame(lenisRaf); }
      requestAnimationFrame(lenisRaf);
    }
  }

  // --- GSAP + ScrollTrigger -------------------------------------------------
  if (window.gsap && window.ScrollTrigger) {
    var gsap = window.gsap;
    var ST = window.ScrollTrigger;
    gsap.registerPlugin(ST);

    if (lenis) {
      lenis.on('scroll', ST.update);
      gsap.ticker.add(function (t) { lenis.raf(t * 1000); });
      gsap.ticker.lagSmoothing(0);
    } else if (!reduce && window.Lenis) {
      // Lenis exists but reduced-motion path — skip
    }

    // Force ScrollTrigger to recompute after layout settles + on resize/load
    window.addEventListener('load', function () { ST.refresh(); });
    ST.config({ ignoreMobileResize: true });

    // Section reveals
    document.querySelectorAll('[data-reveal]').forEach(function (el) {
      var dir = el.getAttribute('data-reveal') || 'fade-up';
      var from = { opacity: 0, y: dir === 'fade-up' ? 48 : 0,
        x: dir === 'fade-left' ? 48 : dir === 'fade-right' ? -48 : 0 };
      if (reduce) from = { opacity: 0 };
      gsap.fromTo(el, from, Object.assign({}, from, {
        opacity: 1, x: 0, y: 0,
        duration: reduce ? 0.2 : 1.0,
        ease: 'power3.out',
        scrollTrigger: { trigger: el, start: 'top 88%', once: true }
      }));
    });

    // Image clip-path reveal
    document.querySelectorAll('[data-img-reveal]').forEach(function (el) {
      if (reduce) { el.style.clipPath = 'none'; return; }
      gsap.to(el, {
        clipPath: 'inset(0% 0% 0% 0%)',
        duration: 1.4,
        ease: 'expo.out',
        scrollTrigger: { trigger: el, start: 'top 90%', once: true }
      });
    });

    // Parallax media (subtle — element pre-scaled in CSS so no blank space)
    document.querySelectorAll('[data-parallax]').forEach(function (el) {
      if (reduce) return;
      var amount = parseFloat(el.getAttribute('data-parallax') || '0.15');
      // amount is a fraction of element height; cap at 0.15 so scale(1.25) covers
      amount = Math.min(amount, 0.15);
      gsap.fromTo(el,
        { yPercent: amount * 50 },
        {
          yPercent: -amount * 50,
          ease: 'none',
          scrollTrigger: { trigger: el.closest('section,[data-reveal]') || el, start: 'top bottom', end: 'bottom top', scrub: true }
        }
      );
    });

    // Splitting kinetic typography
    if (window.Splitting) {
      document.querySelectorAll('[data-split]').forEach(function (el) {
        if (el.dataset.splitDone) return;
        var kind = el.getAttribute('data-split') || 'words';
        try {
          window.Splitting({ target: el, by: kind === 'chars' ? 'chars' : 'words' });
          el.dataset.splitDone = '1';
        } catch (e) { return; }
        var parts = el.querySelectorAll(kind === 'chars' ? '.char' : '.word');
        if (!parts.length) return;
        gsap.set(parts, { yPercent: 110, opacity: 0 });
        gsap.to(parts, {
          yPercent: 0,
          opacity: 1,
          duration: reduce ? 0.2 : 0.95,
          ease: 'expo.out',
          stagger: reduce ? 0 : 0.045,
          scrollTrigger: { trigger: el, start: 'top 92%', once: true }
        });
      });
    }
  }

  // --- Magnetic interactive elements ---------------------------------------
  if (!reduce) {
    document.querySelectorAll('[data-magnetic]').forEach(function (el) {
      el.addEventListener('mousemove', function (e) {
        var r = el.getBoundingClientRect();
        var x = e.clientX - r.left - r.width / 2;
        var y = e.clientY - r.top - r.height / 2;
        el.style.transform = 'translate(' + (x * 0.22) + 'px, ' + (y * 0.22) + 'px)';
      });
      el.addEventListener('mouseleave', function () { el.style.transform = ''; });
    });
  }

  // --- Marquee dup loop -----------------------------------------------------
  document.querySelectorAll('[data-marquee]').forEach(function (el) {
    if (el.dataset.marqueeReady) return;
    el.dataset.marqueeReady = '1';
    el.innerHTML = el.innerHTML + el.innerHTML;
    el.style.animation = 'polisher-marquee ' + (reduce ? '0s' : '45s') + ' linear infinite';
  });

  // --- Page transitions: disabled to keep nav snappy + avoid bfcache flash ---
  // (kept code path off — full-page navigation is faster + plays nice with browser back)
})();
"""


def build_prototype_js(brief: BriefSummary) -> str:
    page_transitions = "true" if brief.page_transitions else "false"
    return _PROTOTYPE_JS_TEMPLATE.replace("__PAGE_TRANSITIONS__", page_transitions)
