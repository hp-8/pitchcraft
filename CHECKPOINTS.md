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

## Phase 5 — Approval Gate
**Deliverables:** Local web UI (`scripts/approval-server.py` or simple Next.js route) showing variants side-by-side, click to approve.

**Verify:**
```bash
uv run python scripts/approval-server.py
# open localhost:8000/leads/<id>
```
Expected: see 12 thumbnails grouped by page, click variant → marks approved in Sheet.

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

## Phase 7 — Email Agent + Send Queue
**Deliverables:** `agents/email/agent.py` + `tools/gmail/sender.py` + queue runner.

**Verify draft:**
```bash
uv run python -m agents.email --lead-id <id> --dry-run
```
Expected: subject + body printed, no send.

**Verify send (to yourself first):**
```bash
uv run python -m tools.gmail.sender --to hpatadi07@gmail.com --subject test --body "test"
```
Expected: email in inbox within 30s.

**Queue runner:**
```bash
uv run python -m pipeline.send-queue --max 5 --start-hour 9 --end-hour 17
```
Expected: 5 emails sent, spaced ~15min, Sheet `email_sent_at` updated.

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

## Phase 9 — Reply Handling + Proposal Agent
**Deliverables:** `agents/proposal/agent.py` → PDF via weasyprint. Reply detection (Gmail polling or IMAP).

**Verify proposal:**
```bash
uv run python -m agents.proposal --lead-id <id>
```
Expected: `data/outputs/<slug>/proposal.pdf` generated, looks pro on open.

**Reply detection:**
```bash
uv run python -m pipeline.reply-watcher --once
```
Expected: scans Gmail, marks Sheet rows where reply received.

---

## Phase 10 — Orchestrator
**Deliverables:** `pipeline/orchestrator.py` — single command runs all phases for N leads.

**Verify:**
```bash
uv run python -m pipeline.orchestrator --limit 3 --skip-send
```
Expected: 3 leads audit → ref → design → variants → (manual approval) → build → email drafts → all logged to Sheet. No actual send (`--skip-send`).

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
