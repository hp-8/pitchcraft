"""Inject scroll-linked hero background video + per-lead vibe theme.

Replaces the hero `<img class='parallax-bg'>` with `<video>` element using a
free Pexels CDN clip selected by vertical + lead_id hash. Adds per-lead
CSS variation (radius vocabulary, accent tint) to break uniform output.
"""
from __future__ import annotations

import hashlib
from bs4 import BeautifulSoup, Tag

from tools.polisher._html import ensure_body, ensure_head

# Free Pexels MP4s (CC0, direct CDN, hotlink OK).
# Curated per vertical. Pool indexed by hash(lead_id) for variety.
_VIDEO_POOL: dict[str, list[str]] = {
    "realtor": [
        "https://videos.pexels.com/video-files/3243161/3243161-hd_1920_1080_30fps.mp4",  # city skyline drone
        "https://videos.pexels.com/video-files/5158158/5158158-uhd_2560_1440_25fps.mp4",  # heritage estate
        "https://videos.pexels.com/video-files/4434242/4434242-uhd_3840_2160_24fps.mp4",  # luxury home
        "https://videos.pexels.com/video-files/2257012/2257012-uhd_2732_1440_25fps.mp4",  # coastal sunrise
        "https://videos.pexels.com/video-files/7578548/7578548-uhd_3840_2160_25fps.mp4",  # modern interior
        "https://videos.pexels.com/video-files/8419143/8419143-uhd_3840_2160_25fps.mp4",  # contemporary home
    ],
    "restaurant": [
        "https://videos.pexels.com/video-files/3196284/3196284-uhd_3840_2160_25fps.mp4",
    ],
    "dental": [
        "https://videos.pexels.com/video-files/6529115/6529115-uhd_2732_1440_25fps.mp4",
    ],
    "fnb": [
        "https://videos.pexels.com/video-files/2887463/2887463-hd_1920_1080_24fps.mp4",
    ],
}

# Vibe presets — each lead deterministically gets one for design diversity.
_VIBES = [
    {
        "name": "editorial-soft",
        "radius_sm": "8px", "radius_md": "16px", "radius_lg": "28px", "radius_pill": "999px",
        "accent": "#C9A24B",  # champagne gold
        "card_skew": "0deg",
    },
    {
        "name": "architectural-sharp",
        "radius_sm": "2px", "radius_md": "4px", "radius_lg": "6px", "radius_pill": "4px",
        "accent": "#B7791F",  # deep brass
        "card_skew": "0deg",
    },
    {
        "name": "modern-pill",
        "radius_sm": "12px", "radius_md": "24px", "radius_lg": "32px", "radius_pill": "999px",
        "accent": "#0EA5A4",  # teal
        "card_skew": "0deg",
    },
    {
        "name": "asymmetric-cut",
        "radius_sm": "0px", "radius_md": "24px 4px 24px 4px", "radius_lg": "48px 8px 48px 8px", "radius_pill": "999px",
        "accent": "#A855F7",  # plum
        "card_skew": "-0.5deg",
    },
]


def _hash_index(seed: str, modulo: int) -> int:
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % modulo


def _pick_video(vertical: str, lead_id: str) -> str | None:
    pool = _VIDEO_POOL.get(vertical)
    if not pool:
        return None
    return pool[sum(ord(c) for c in lead_id) % len(pool)]


def _pick_vibe(lead_id: str) -> dict[str, str]:
    # Sum-of-ords gives more even distribution across small N than md5%len.
    return _VIBES[sum(ord(c) for c in lead_id) % len(_VIBES)]


def _find_hero_section(soup: BeautifulSoup) -> Tag | None:
    """Find the first section that looks like a hero (h-screen / min-h-screen)."""
    for sec in soup.find_all("section"):
        cls = " ".join(sec.get("class") or [])
        if "h-screen" in cls or "min-h-screen" in cls or "hero" in cls.lower():
            return sec
    # Fallback: first section in body
    body = soup.find("body")
    if body:
        return body.find("section")
    return None


_BG_URL_RE = __import__("re").compile(r"url\(['\"]?(.*?)['\"]?\)")


def _make_video_tag(soup: BeautifulSoup, video_url: str, poster: str, alt: str, extra_classes: list[str]) -> Tag:
    classes = ["hero-bg-video"] + extra_classes
    video = soup.new_tag(
        "video",
        attrs={
            "autoplay": "",
            "muted": "",
            "loop": "",
            "playsinline": "",
            "preload": "metadata",
            "poster": poster,
            "class": " ".join(classes),
            "data-hero-video": "1",
        },
    )
    source = soup.new_tag("source", attrs={"src": video_url, "type": "video/mp4"})
    video.append(source)
    fallback = soup.new_tag("img", attrs={"src": poster, "alt": alt})
    video.append(fallback)
    return video


def _swap_img_for_video(soup: BeautifulSoup, hero: Tag, video_url: str) -> bool:
    """Replace hero background (either <img> or div with CSS background-image) with <video>."""
    # Case A: <img class='parallax-bg'> or any <img>
    img = hero.find("img", class_="parallax-bg") or hero.find("img")
    if img is not None:
        cls = img.get("class") or []
        if isinstance(cls, str):
            cls = cls.split()
        poster = img.get("src") or ""
        video = _make_video_tag(soup, video_url, poster, img.get("alt", ""), cls)
        img.replace_with(video)
        return True

    # Case B: <div style="background-image: url(...)"> with parallax-bg or in hero
    bg_div = hero.find(
        lambda t: t.name == "div"
        and t.get("style") is not None
        and "background-image" in t.get("style", "")
    )
    if bg_div is None:
        return False
    style = bg_div.get("style", "") or ""
    m = _BG_URL_RE.search(style)
    poster = m.group(1) if m else ""
    # Strip the background-image declaration; keep other style props.
    cleaned_style = __import__("re").sub(r"background-image\s*:\s*url\([^)]*\)\s*;?", "", style).strip()
    if cleaned_style:
        bg_div["style"] = cleaned_style
    else:
        del bg_div["style"]
    cls = bg_div.get("class") or []
    if isinstance(cls, str):
        cls = cls.split()
    video = _make_video_tag(soup, video_url, poster, "", cls)
    bg_div.insert(0, video)
    return True


def _inject_vibe_css(soup: BeautifulSoup, vibe: dict[str, str]) -> None:
    head = ensure_head(soup)
    if soup.find(attrs={"data-vibe-css": "1"}):
        return
    css = f"""
/* polisher vibe: {vibe['name']} */
:root {{
  --vibe-radius-sm: {vibe['radius_sm']};
  --vibe-radius-md: {vibe['radius_md']};
  --vibe-radius-lg: {vibe['radius_lg']};
  --vibe-radius-pill: {vibe['radius_pill']};
  --vibe-accent: {vibe['accent']};
}}
.rounded, .rounded-md, .rounded-lg, [class*='rounded-'] {{ border-radius: var(--vibe-radius-md); }}
.rounded-full {{ border-radius: var(--vibe-radius-pill); }}
.rounded-sm {{ border-radius: var(--vibe-radius-sm); }}
.rounded-xl, .rounded-2xl, .rounded-3xl {{ border-radius: var(--vibe-radius-lg); }}
.card, [class*='card'] {{ transform: skewY({vibe['card_skew']}); }}

/* hero video */
.hero-bg-video {{
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; z-index: 0;
}}
.hero-bg-video + img {{ display: none; }}

/* accent override */
.text-tertiary-fixed-dim, .text-primary {{ color: var(--vibe-accent) !important; }}
.bg-tertiary-fixed-dim {{ background-color: var(--vibe-accent) !important; }}
.border-tertiary, .border-primary {{ border-color: var(--vibe-accent) !important; }}
"""
    style = soup.new_tag("style")
    style["data-vibe-css"] = "1"
    style.string = css
    head.append(style)


def _inject_scroll_link_js(soup: BeautifulSoup) -> None:
    """Map scroll progress inside hero → video.currentTime for scroll-linked playback.

    Falls back to native autoplay if reduced-motion or no JS.
    """
    body = ensure_body(soup)
    if soup.find(attrs={"data-hero-scroll-link": "1"}):
        return
    js = r"""
(function () {
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var video = document.querySelector('video[data-hero-video]');
  if (!video) return;
  var hero = video.closest('section') || video.parentElement;
  if (!hero) return;
  // Keep native autoplay loop; on scroll, also nudge currentTime for a subtle scrub feel.
  var ticking = false;
  function onScroll() {
    if (ticking) return; ticking = true;
    requestAnimationFrame(function () {
      var rect = hero.getBoundingClientRect();
      var vh = window.innerHeight || 1;
      var progress = Math.max(0, Math.min(1, (vh - rect.top) / (vh + rect.height)));
      if (video.duration && isFinite(video.duration)) {
        // Subtle scrub: shift currentTime by a small offset proportional to scroll.
        var target = progress * Math.min(video.duration, 6);
        // Only sync if drift > 0.4s (cheap pause-free scrubbing).
        if (Math.abs(video.currentTime - target) > 0.4) {
          try { video.currentTime = target; } catch (_) {}
        }
      }
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();
"""
    script = soup.new_tag("script")
    script["data-hero-scroll-link"] = "1"
    script.string = js
    body.append(script)


def apply_hero_video(soup: BeautifulSoup, lead_id: str, vertical: str) -> dict[str, str | bool | None]:
    """Public entry: swap hero img→video, inject vibe CSS, inject scroll-link JS.

    Returns metadata about what was applied. If vertical has no video pool, only
    the vibe CSS is applied (no video swap).
    """
    vibe = _pick_vibe(lead_id)
    video_url = _pick_video(vertical, lead_id)
    swapped = False
    if video_url:
        hero = _find_hero_section(soup)
        if hero is not None:
            swapped = _swap_img_for_video(soup, hero, video_url)
    _inject_vibe_css(soup, vibe)
    if swapped:
        _inject_scroll_link_js(soup)
    return {"vibe": vibe["name"], "video": video_url, "swapped": swapped}
