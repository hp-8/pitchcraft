# Design Brief: Joe's Pizza

## Pre-flight context

- Lead ID: test-pizza
- Vertical: restaurant
- Location: Brooklyn, NY
- Services: pizza, delivery
- Phone: (unspecified)
- Booking provider: (unspecified)

## Audience

Diners within 15 minutes of the storefront looking for a memorable but unfussy meal.

## Use case

Browse the menu, check hours, reserve a table, find the address.

## Tone

**editorial** — voice attributes: warm, specific, place-rooted.

One-liner: _Joe's Pizza — a Brooklyn kitchen built on pizza._

## Genre

editorial

## Macrostructure

**Bento Grid** — page shape inherited from Hallmark catalogue. Refer to the matching `references/macrostructures/<slug>.md` for hero composition rules.

## Theme

- Name: **Specimen**
- Paper band: light
- Display style: italic-serif
- Accent hue: warm
- Rotation note: Recent macrostructures: none. Previous theme: none. Pool: ['Specimen', 'Atelier', 'Brutal', 'Salon', 'Newsprint', 'Linen', 'Studio', 'Manifesto', 'Almanac', 'Garden', 'Riso', 'Sport', 'Coral', 'Violet', 'Aurora', 'Halo', 'Editorial'].

## Nav archetype

N1 Wordmark + 2 links

## Footer archetype

Ft1 Tabular index

## Must-have sections (drawn from audit + vertical minimums)

- primary CTA above fold + repeated in footer band
- phone in header + footer
- lazy-load below-fold imagery
- reservation widget block
- hours block in contact + footer
- menu / services index callout

## Page-specific requirements

### Landing
- primary CTA mandatory above fold; repeat in footer band
- phone number visible in header and footer
- lazy-load below-fold imagery; ship one optimised hero image
- reservation widget anchored above the fold on contact, callout on landing

### Services
- primary CTA mandatory above fold; repeat in footer band
- phone number visible in header and footer

### About
- phone number visible in header and footer

### Contact
- phone number visible in header and footer
- reservation widget anchored above the fold on contact, callout on landing

## Motion plan

| Page | Primitives |
|------|------------|
| landing | smooth_scroll, kinetic_typography, scroll_reveals, marquee, intro_loader, hover_micro, modern_typography, depth |
| services | scroll_reveals, hover_micro, lazy_reveal, modern_typography |
| about | scroll_reveals, lazy_reveal, page_transition, modern_typography |
| contact | hover_micro, page_transition |

- Libraries to load: framer-motion, gsap, lenis, splitting, three
- `prefers-reduced-motion`: prefers-reduced-motion: reduce -> opacity crossfade <=150ms only

## Inspirational references (top 12)

By source: {'codrops': 1, 'awwwards': 1, 'arena': 1}

Motion-lib distribution: {'motion': 1, 'gsap': 1, 'Lenis': 1}

| # | Title | Source | URL |
|---|-------|--------|-----|
| 1 | Marquee hover card | codrops | https://tympanus.net/codrops/3 |
| 2 | Kinetic typographic landing | awwwards | https://awwwards.com/site/2 |
| 3 | Warm pasta bar | arena | https://www.are.na/block/1 |

## Phase 3 DESIGN.md handoff (palette / typography / motion)

(no Phase 3 DESIGN.md supplied — palette/typography to be inherited from theme defaults)

## Honesty constraints

- No fabricated metrics (count, percentage, dollar figure)
- "Trusted by N+ teams" / "N happy customers" banned unless supplied by lead
- Testimonials and stats placeholdered if not supplied — never invented
- No 'Jane Doe' / 'John Smith' placeholder names

## Hallmark slop-test gates to enforce post-build

- Mobile-correct at 320 / 375 / 414 / 768 px (gate: responsive)
- Locked design tokens (no inline OKLCH literals in markup)
- No re-drawn UI chrome (no fake browser bars, fake macOS windows)
- No invented metrics (gate: honesty)
- 2+1 font discipline (display + body, optional mono)
- No glassmorphism, no gradient text
- Respect prefers-reduced-motion

## Audit narrative

Top audit pressures: weak_cta, no_phone, slow_lcp. Brief enforces 6 structural requirements drawn from the audit.
