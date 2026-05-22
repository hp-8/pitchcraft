# Checkpoints & Testing Guide

Per-phase deliverables and how to verify them manually.

---

## Phase 0 — Scaffold ✅
**Deliverables:**
- Folder structure, `pyproject.toml`, `package.json`, `.env.example`, `.gitignore`, `README.md`, git init.

**Verify:**
```bash
ls -la
git log --oneline
python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"
node -e "JSON.parse(require('fs').readFileSync('package.json'))"
```
Expected: folders present, 2 commits, manifests valid.

---

## Phase 1 — Reference Scrapers + Animation Capture
**Sub-tasks:** 1.1 Are.na, 1.2 capture util, 1.3 Codrops, 1.4 Awwwards, 1.5 Cosmos, 1.6 Pinterest, 1.7 21st.dev, 1.8 react-bits, 1.9 GSAP showcase, 1.10 r3f, 1.11 unified CLI.

**Deliverables:** `tools/scrapers/<source>.py` per source + `tools/scrapers/_capture.py` (Playwright video + lib detection) + `tools/scrapers/cli.py` + SQLite cache at `data/cache/scrapers.db` + artifact dir `data/cache/refs/<source>/<slug>/`.

**Verify per scraper:**
```bash
uv run python -m tools.scrapers.arena --query "modern restaurant landing" --limit 20
uv run python -m tools.scrapers.codrops --tag "hero" --limit 10
uv run python -m tools.scrapers.awwwards --category restaurant --limit 5     # writes MP4 + meta.json per result
uv run python -m tools.scrapers.21st --query "hero animation" --limit 10     # writes components.tsx
# etc.
```
Expected JSON output: `{source, query, fetched_at, items: [{id, title, url, image_url, preview_mp4_path?, components_tsx_path?, tags, libs_detected: [...], has_animation: bool}]}`.

**Cache check:**
```bash
sqlite3 data/cache/scrapers.db "SELECT source, COUNT(*) FROM cache GROUP BY source;"
ls data/cache/refs/awwwards/*/preview.mp4 | head
```

**Animation detection check:** open any `meta.json` for a live-site scrape, confirm `libs_detected` lists at least one of `gsap`, `Lenis`, `THREE`, `motion`, `lottie` where applicable.

**Unified CLI:**
```bash
uv run python -m tools.scrapers.cli --vertical restaurant --style modern --limit 30 --include-motion
```
Expected: deduped JSON moodboard from all sources, sorted with motion-rich refs first when `--include-motion`.

---

## Phase 2 — Audit Engine
**Deliverables:** `tools/audit/audit.py` — runs Firecrawl scrape + PageSpeed + heuristics, outputs `audit.json` + screenshot.

**Verify:**
```bash
uv run python -m tools.audit --url https://somerealrestaurant.com --vertical restaurant
```
Expected: `data/outputs/<slug>/audit.json` with `{problems: [], dollar_impact: $X, screenshot_path, scores}`.

**Edge:** test on slow site, fast site, missing site. Confirm graceful errors.

---

## Phase 3 — Design Moodboard → DESIGN.md → Stitch
**Deliverables:** `agents/design-ref/agent.py` — input moodboard JSON, output `DESIGN.md` + invokes Stitch `create_design_system_from_design_md`.

**Verify:**
```bash
uv run python -m agents.design-ref --vertical restaurant --moodboard data/outputs/moodboard.json
```
Expected: `DESIGN.md` written, Stitch design system ID returned, logged to Sheet.

**Manual:** open Stitch dashboard, confirm design system appears.

---

## Phase 4 — Stitch Screen Generation
**Deliverables:** `tools/stitch/generate.py` — generate 4 pages × 3 variants per lead.

**Verify:**
```bash
uv run python -m tools.stitch.generate --lead-id <id> --pages landing,services,about,contact --variants 3
```
Expected: 12 screen URLs returned, stored in Sheet `stitch_variants_url`.

---

## Phase 5 — Approval Gate ✅
**Deliverables:** `tools/approval/app.py` — Flask app w/ inline templates. Lists leads with stitch envelopes, per-lead grid (4 pages × N variants) embedded via iframe srcdoc, click button per page → writes `approved.json`.

**Verify:**
```bash
python -m tools.approval --port 8765 --out-dir data/outputs
# open http://127.0.0.1:8765/
```
Expected: lead list, click "Review variants →" per lead, see 4 page blocks with variant cards. Each "Approve" button writes `{"approved": {"landing": 0, ...}}` to `data/outputs/<slug>/approved.json`. "Finalize approval & continue" returns to index.

**After approval, resume polish + deploy:**
```bash
python -m tools.orchestrator resume --leads data/leads/test_batch.csv --no-sheet
```

---

## Phase 6 — Prototype Builder
**Deliverables:** `pipeline/builder.py` — approved Stitch design → Next.js project in `data/outputs/<slug>/site/` → deploy via Vercel CLI → write URL to Sheet.

**Verify:**
```bash
uv run python -m pipeline.builder --lead-id <id>
```
Expected:
- `data/outputs/<slug>/site/` contains working Next.js app
- `npm run dev` works locally
- Vercel deploy returns `joes-pizza.vercel.app`
- Sheet `prototype_url` updated
- Hit the URL → see real site

---

## Phase 7 — Email Agent + Send Queue ✅
**Deliverables:** `tools/email/{template, llm, gmail_send, agent, cli}.py`. Hybrid: deterministic template w/ audit-driven swap blocks + optional per-lead Gemini Flash polish + Gmail SMTP send.

**Verify preview (no send):**
```bash
python -m tools.email preview --lead-id trayvino --leads data/leads/test_batch.csv --lead-dir data/outputs/trayvinowines-com --preview-url https://trayvino-wines.vercel.app
python -m tools.email preview ... --no-llm   # skip LLM polish
```
Expected: `{subject, body, polished_by_llm}` printed.

**Verify send (to yourself first; needs `GMAIL_USER` + `GMAIL_APP_PASSWORD` in .env):**
```bash
python -m tools.email send-one --lead-id <id> --leads <csv> --lead-dir <dir> --preview-url <url>
```
Expected: email in inbox within 30s.

**Batch:**
```bash
python -m tools.email send-batch --leads <csv> --cap 35 --spacing 900
```
Expected: up to 35 emails sent, spaced 15min apart, can opt-out of LLM with `--no-llm`.

---

## Phase 8 — Tracking Layer (Sheets)
**Deliverables:** `tools/sheets/client.py` wrapping gspread. All agents write status updates.

**Verify:**
```bash
uv run python -m tools.sheets.client --test
```
Expected: writes test row, reads back, deletes.

**Manual:** open Google Sheet, see real-time status updates as pipeline runs.

---

## Phase 9 — Proposal + Audit PDFs ✅ / Reply Detection ⏳
**Deliverables:** `tools/pdf/{proposal, audit, _humanize, _brand, renderer, cli}.py`. Playwright Chromium renderer (weasyprint blocked by missing macOS system libs — pango/gobject).

**Verify proposal + audit PDFs:**
```bash
python -m tools.pdf both --lead-id trayvino --leads data/leads/test_batch.csv --preview-url https://trayvino-wines.vercel.app
```
Expected: `data/outputs/<slug>/proposal.pdf` (1pg, plain-English problems + $loss callout + timeline + price + Book A Call) and `audit.pdf` (multi-page, per-problem cards + calculation transparency table + methodology + competitive benchmark).

**Customize price / book-call URL:**
```bash
python -m tools.pdf both ... --price "CA$3,200" --book-call-url https://cal.com/harshpatadia/intro
```

**Batch (every lead in CSV):**
```bash
python -m tools.pdf batch --leads <csv>
```

**Reply detection ⏳ — not built.** Planned: `tools/gmail/reply_watcher.py` polls Gmail label, flips sheet status, triggers proposal send.

**Open/click tracking ⏳ — not built.** Planned: tracking pixel relay (1×1 GIF endpoint) + UTM-wrapped preview URL.

---

## Phase 10 — Orchestrator (Worker Pool) ✅
**Deliverables:** `tools/orchestrator/` package + `.claude/skills/stitch-batch/SKILL.md` + `.claude/skills/stitch-probe/SKILL.md`.
- `cli.py` typer commands: `run-batch`, `resume`, `status`, `pending-screens`, `set-stitch-cap`
- `runner.py` asyncio pipeline w/ per-phase `asyncio.Semaphore` (default: scrape/audit/design_ref/council/polish=10, build=5, stitch_fulfill=3, email=1)
- `_phases.py` async wrappers around existing CLIs (`asyncio.to_thread` for sync work)
- `_state.py` per-lead `asyncio.Lock` map + sheet status updates
- Pauses at Stitch envelope. `/stitch-batch` skill drives MCP fulfillment. `orchestrator resume` continues polish + deploy in parallel.

**Verify pre-stitch run on 1+ leads (no MCP yet):**
```bash
python -m tools.orchestrator run-batch --leads data/leads/test_batch.csv --design-system-id <ds_asset_id> --no-sheet --pause-at-stitch
```
Expected: per-lead `scrape`, `audit`, `design_ref`, `council` (scheduled), `stitch_envelope` all OK. Envelopes written under `data/outputs/<slug>/stitch_screens_request.json`.

**Drive Stitch fulfillment (inside CC session):**
```
/stitch-batch
```
Skill reads pending screens, fires parallel `mcp__stitch__generate_screen_from_text` calls (concurrency from `.orchestrator/stitch_caps.json`), polls `list_screens`, downloads HTML, calls `tools.stitch fulfill` per row.

**Resume post-stitch:**
```bash
python -m tools.orchestrator resume --leads data/leads/test_batch.csv --no-sheet
```
Expected: polish + build/deploy in parallel. Sheet status flips to `deployed` with preview URL.

**Set Stitch cap manually (or run `/stitch-probe` to derive):**
```bash
python -m tools.orchestrator set-stitch-cap --n 5
```

---

## Phase 11 — End-to-End Test
**Deliverables:** none new — operational test.

**Verify:**
- 20 leads processed start to finish
- ≥1 reply
- ≥1 demo call booked
- Sheet shows full audit trail

**Daily checks:**
- Sheet `error_log` empty
- Gmail Sent folder = today's count matches Sheet
- Vercel dashboard ≈ leads processed

---

## Phase 13 — Scraper repair (✅ partial)
**Status:** 4 working sources after repair (Are.na, Codrops, **Unsplash**, **Pexels**). Behance + Dribbble RSS now cloudflared — code present but disabled via `SOURCE_WEIGHTS = 0.0`.

**Deliverables:**
- `tools/scrapers/unsplash.py` — Unsplash search API (`UNSPLASH_ACCESS_KEY`, 50 req/hr free)
- `tools/scrapers/pexels.py` — Pexels search API (`PEXELS_API_KEY`, unlimited free)
- `tools/scrapers/behance_rss.py` — Behance RSS (currently blocked; field-id mapping built for future stealth retry)
- `tools/scrapers/dribbble_rss.py` — Dribbble RSS (currently blocked; popular + tag feed paths built)
- `tools/scrapers/cli.py`:
  - `VERTICAL_SEEDS` map (fnb → wine/winery/cellar; restaurant → menu/dining; dental → clinic/healthcare; realtor → architecture/property)
  - `SOURCE_WEIGHTS` matrix per vertical — r3f weighted to 0 for non-3D verticals
  - `build_queries()` now seed-driven, not "modern X landing page" template

**Verify per source:**
```bash
python -m tools.scrapers.unsplash -q "wine cellar" -n 5 --pretty
python -m tools.scrapers.pexels -q "vineyard" -n 5 --pretty
python -m tools.scrapers.behance_rss -q "winery hospitality" -n 5 --pretty   # may 429
python -m tools.scrapers.dribbble_rss -q "wine" -n 5 --pretty               # may 202 empty
```

**Verify unified sweep:**
```bash
python -m tools.scrapers.cli --vertical fnb --style editorial -n 30 --pretty 2>/dev/null | \
  python -c "import sys,json; d=json.load(sys.stdin); print(d['by_source']); print('items:', len(d['items']))"
```
Expected: ≥4 sources non-zero, total deduped items = 30.

## Phase 13b — Anti-bot bypass (⏳)
Behance + Dribbble + Awwwards + Cosmos + Pinterest blocked by Cloudflare on plain `requests`. Plan: Playwright stealth context w/ persistent cookies + browser fingerprint rotation. Not built yet.

---
**Problem:** only 3/9 sources (Are.na, Codrops, r3f-examples) return data on a fresh sweep. Awwwards / Cosmos / Pinterest / 21st.dev / react-bits / GSAP showcase all silently return 0 items due to Cloudflare or anti-bot. r3f returns 100+ but for non-3D verticals (wine, dental, realtor) the cosmic palette derails downstream design.

**Fix list:**
1. Add Unsplash API (`UNSPLASH_ACCESS_KEY`, 50/hr free) — vertical keyword search returns curated photos.
2. Add Pexels API (free, unlimited) — same purpose as Unsplash fallback.
3. Add Behance RSS feed (`https://www.behance.net/feeds/projects?field=<field_id>`) — no auth, by creative field.
4. Add Dribbble popular RSS (`https://dribbble.com/shots/popular.rss`).
5. Rewrite `tools/scrapers/cli.build_queries()` to vertical→seed-terms map. Example:
   - `fnb`: ["wine", "winery", "vineyard", "cellar", "bottle photography"]
   - `restaurant`: ["restaurant menu", "hospitality", "fine dining"]
   - `dental`: ["dental clinic", "healthcare brand", "medical UI"]
   - `realtor`: ["luxury real estate", "architecture", "property brochure"]
6. Per-vertical source weights — demote r3f to 0 for non-3D verticals; boost Unsplash/Pexels for hospitality.
7. Persistent Playwright contexts (cookies + stealth) for Awwwards / Cosmos / Pinterest.

**Verify after fix:**
```bash
python -m tools.scrapers.cli --vertical fnb --style editorial -n 30 --pretty | python -c "import sys,json; d=json.load(sys.stdin); print(d['by_source'])"
```
Expected: ≥5 sources non-zero, total items ≥30, color palette diverse (not r3f-dominated).

---

## Phase 15 — NLP keyword extraction ✅
**Deliverables:** `tools/keywords/{crawl,bucket,extract,validate,pipeline,cli}.py`. 2 LLM calls + spaCy + KeyBERT.

**Verify:**
```bash
python -m tools.keywords one \
  --lead-id trayvino --business "Trayvino Wines" --vertical fnb \
  --site-url https://trayvinowines.com \
  --tagline "Ontario wine agency & importer" \
  --service "Wine agency representation" --service "Hospitality accounts" \
  --max-pages 3
```
Expected: `data/outputs/<slug>/keywords.json` written. Output:
- `bucket_tokens`: 3-5 sub-vertical anchors from LLM #1 (e.g. `["ontario wine agency", "wine importer", "wholesale wine distributor"]`)
- `keywords`: 8-15 NLP-extracted terms filtered by LLM #2 (e.g. `["wine", "ontario", "chardonnay", "carmenere", "cranswick", ...]`)
- `candidates`: top 50 raw spaCy+KeyBERT extractions w/ scores + source tags

**Skip both LLM calls (offline / quota-saving):**
```bash
python -m tools.keywords one ... --skip-llm
```
Falls back to `VERTICAL_SEEDS` bucket + top-N by KeyBERT score.

**Batch:**
```bash
python -m tools.keywords batch --leads data/leads/test_batch.csv --max-pages 3
```

**Hooked into orchestrator** — runs as `phase_keywords` between audit and scrape. Scraper auto-detects `keywords.json` and uses NLP terms instead of static `VERTICAL_SEEDS`.

---

## Phase 14 — Reply detection + tracking (⏳)
**Deliverables (planned):**
- `tools/gmail/reply_watcher.py` — Gmail API polling (label `lead-reply`), flips sheet `reply_status`, marks lead → proposal flow.
- `tools/tracking/pixel.py` — Cloudflare Worker or Vercel function serving 1×1 GIF, writes hit to sheet via webhook.
- UTM wrapper for preview URLs in email body.

---

## Cross-cutting tests

**Lint:**
```bash
uv run ruff check .
npm run lint
```

**Type check (if added later):**
```bash
uv run mypy tools agents pipeline
```

**Smoke test of full pipeline (after Phase 10):**
```bash
uv run python -m pipeline.orchestrator --lead-id <test-id> --dry-run
```
