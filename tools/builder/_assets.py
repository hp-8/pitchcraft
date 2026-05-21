"""Animation primitives — JS + CSS templates injected into every prototype page."""
from __future__ import annotations

PROTOTYPE_JS = """// Prototype animation primitives — wired by tools.builder
(function () {
  // Lenis smooth scroll
  if (window.Lenis) {
    var lenis = new window.Lenis({
      duration: 1.1,
      easing: function (t) { return 1 - Math.pow(1 - t, 3); }
    });
    function raf(t) { lenis.raf(t); requestAnimationFrame(raf); }
    requestAnimationFrame(raf);
  }

  // GSAP + ScrollTrigger reveals
  if (window.gsap && window.ScrollTrigger) {
    window.gsap.registerPlugin(window.ScrollTrigger);
    document.querySelectorAll('[data-reveal]').forEach(function (el) {
      window.gsap.from(el, {
        opacity: 0,
        y: 40,
        duration: 0.9,
        ease: 'power3.out',
        scrollTrigger: { trigger: el, start: 'top 85%' }
      });
    });
  }

  // Splitting.js kinetic typography
  if (window.Splitting) { window.Splitting(); }

  // Magnetic buttons
  document.querySelectorAll('[data-magnetic]').forEach(function (el) {
    el.addEventListener('mousemove', function (e) {
      var r = el.getBoundingClientRect();
      var x = e.clientX - r.left - r.width / 2;
      var y = e.clientY - r.top - r.height / 2;
      el.style.transform = 'translate(' + (x * 0.25) + 'px, ' + (y * 0.25) + 'px)';
    });
    el.addEventListener('mouseleave', function () { el.style.transform = ''; });
  });

  // Marquee — duplicate content for seamless loop
  document.querySelectorAll('[data-marquee]').forEach(function (el) {
    el.style.display = 'flex';
    el.style.gap = '2rem';
    el.innerHTML = el.innerHTML + el.innerHTML;
    el.style.animation = 'marquee 30s linear infinite';
  });

  // Intro loader (curtain wipe)
  document.documentElement.classList.add('is-loading');
  window.addEventListener('load', function () {
    setTimeout(function () {
      document.documentElement.classList.remove('is-loading');
    }, 400);
  });
})();
"""

PROTOTYPE_CSS = """/* Prototype animation primitives — wired by tools.builder */
html.is-loading body { opacity: 0; }
body { opacity: 1; transition: opacity 0.4s ease; }
@keyframes marquee {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
[data-magnetic] { transition: transform 0.2s ease; will-change: transform; }
[data-reveal] { will-change: transform, opacity; }
"""

# Sentinel comment used to make injection idempotent.
INJECTION_MARKER = "<!-- prototype:animation-primitives -->"

CDN_HEAD_TAGS = """\
{marker}
<script src="https://cdn.jsdelivr.net/gh/studio-freight/lenis@1.0.42/bundled/lenis.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/splitting/dist/splitting.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/splitting/dist/splitting.css">
<link rel="stylesheet" href="/assets/prototype.css">
<script src="/assets/prototype.js" defer></script>
""".format(marker=INJECTION_MARKER)


VERCEL_JSON = {
    "cleanUrls": True,
    "trailingSlash": False,
}
