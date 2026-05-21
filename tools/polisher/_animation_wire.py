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


def inject_cdn(soup: BeautifulSoup) -> list[str]:
    """Add CDN scripts before </body> + splitting.css in <head>. Idempotent."""
    libs_loaded: list[str] = []
    if soup.find(attrs={"data-polisher-cdn": INJECTION_MARKER}):
        return [name for name, _ in CDN_LIBS]

    head = ensure_head(soup)
    body = ensure_body(soup)

    css_link = soup.new_tag("link", rel="stylesheet", href=SPLITTING_CSS)
    css_link["data-polisher-cdn"] = INJECTION_MARKER
    head.append(css_link)
    proto_css = soup.new_tag("link", rel="stylesheet", href="/assets/prototype.css")
    proto_css["data-polisher-cdn"] = INJECTION_MARKER
    head.append(proto_css)

    for name, url in CDN_LIBS:
        tag = soup.new_tag("script", src=url)
        tag["data-polisher-cdn"] = INJECTION_MARKER
        body.append(tag)
        libs_loaded.append(name)

    proto_js = soup.new_tag("script", src="/assets/prototype.js", defer="")
    proto_js["data-polisher-cdn"] = INJECTION_MARKER
    body.append(proto_js)
    return libs_loaded


def build_prototype_js(brief: BriefSummary) -> str:
    page_transitions = "true" if brief.page_transitions else "false"
    return (
        "/* polisher: animation primitives — generated */\n"
        "(function () {\n"
        "  var reduce = window.matchMedia && "
        "window.matchMedia('(prefers-reduced-motion: reduce)').matches;\n"
        "  document.documentElement.classList.add('is-loading');\n"
        "  window.addEventListener('load', function () {\n"
        "    setTimeout(function () {\n"
        "      document.documentElement.classList.remove('is-loading');\n"
        "    }, 400);\n"
        "  });\n"
        "  if (!reduce && window.Lenis) {\n"
        "    var lenis = new window.Lenis({ duration: 1.1, easing: function (t) "
        "{ return 1 - Math.pow(1 - t, 3); } });\n"
        "    function raf(t) { lenis.raf(t); requestAnimationFrame(raf); }\n"
        "    requestAnimationFrame(raf);\n"
        "  }\n"
        "  if (window.Splitting) { try { window.Splitting(); } catch (e) {} }\n"
        "  if (window.gsap && window.ScrollTrigger) {\n"
        "    window.gsap.registerPlugin(window.ScrollTrigger);\n"
        "    document.querySelectorAll('[data-reveal]').forEach(function (el) {\n"
        "      var dir = el.getAttribute('data-reveal') || 'fade-up';\n"
        "      var from = { opacity: 0, y: dir === 'fade-up' ? 40 : 0, "
        "x: dir === 'fade-left' ? 40 : dir === 'fade-right' ? -40 : 0 };\n"
        "      if (reduce) { from = { opacity: 0 }; }\n"
        "      window.gsap.from(el, Object.assign(from, "
        "{ duration: reduce ? 0.15 : 0.9, ease: 'power3.out', "
        "scrollTrigger: { trigger: el, start: 'top 85%' } }));\n"
        "    });\n"
        "    document.querySelectorAll('[data-split] .word, [data-split] .char').forEach("
        "function (el, i) {\n"
        "      window.gsap.from(el, { opacity: 0, y: reduce ? 0 : 20, "
        "duration: reduce ? 0.15 : 0.7, delay: i * 0.02, "
        "scrollTrigger: { trigger: el, start: 'top 90%' } });\n"
        "    });\n"
        "    document.querySelectorAll('[data-parallax]').forEach(function (el) {\n"
        "      if (reduce) return;\n"
        "      var amount = parseFloat(el.getAttribute('data-parallax') || '0.3');\n"
        "      window.gsap.to(el, { yPercent: -amount * 100, ease: 'none', "
        "scrollTrigger: { trigger: el, start: 'top bottom', end: 'bottom top', scrub: true } });\n"
        "    });\n"
        "  }\n"
        "  if (!reduce) {\n"
        "    document.querySelectorAll('[data-magnetic]').forEach(function (el) {\n"
        "      el.addEventListener('mousemove', function (e) {\n"
        "        var r = el.getBoundingClientRect();\n"
        "        var x = e.clientX - r.left - r.width / 2;\n"
        "        var y = e.clientY - r.top - r.height / 2;\n"
        "        el.style.transform = 'translate(' + (x * 0.25) + 'px, "
        "' + (y * 0.25) + 'px)';\n"
        "      });\n"
        "      el.addEventListener('mouseleave', function () { el.style.transform = ''; });\n"
        "    });\n"
        "  }\n"
        "  document.querySelectorAll('[data-marquee]').forEach(function (el) {\n"
        "    if (el.dataset.marqueeReady) return;\n"
        "    el.dataset.marqueeReady = '1';\n"
        "    el.innerHTML = el.innerHTML + el.innerHTML;\n"
        "    el.style.animation = 'marquee ' + (reduce ? '0s' : '30s') + ' linear infinite';\n"
        "  });\n"
        f"  var pageTransitions = {page_transitions};\n"
        "  if (pageTransitions && !reduce) {\n"
        "    document.querySelectorAll('a[href^=\"/\"]').forEach(function (a) {\n"
        "      a.addEventListener('click', function (e) {\n"
        "        if (a.target === '_blank') return;\n"
        "        e.preventDefault();\n"
        "        document.body.style.transition = 'opacity .3s ease';\n"
        "        document.body.style.opacity = '0';\n"
        "        setTimeout(function () { window.location.href = a.href; }, 280);\n"
        "      });\n"
        "    });\n"
        "  }\n"
        "})();\n"
    )
