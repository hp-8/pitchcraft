# Website Generator — Implementation Plan

## Goal
Mass-generate high-quality 4-page websites (Landing + Services + About + Contact) for US local service businesses (restaurants, dentists, realtors, FnB), audit their current sites, send personalized cold emails with prototypes, close deals at $800–$1,200.

## Constraints
- Free tools only until first revenue
- Gmail personal account, 35 emails/day cap
- Payments via Wise (default), PayPal +10%, or bank wire
- Solo operator (Harsh)

## Stack
- **Scraping/audit:** Scrapling (Python), Firecrawl (1000 credits), PageSpeed Insights API
- **Design refs:** Are.na API, Codrops, Awwwards, Cosmos, Pinterest (via Scrapling)
- **UI generation:** Stitch MCP
- **Prototype build:** Next.js + Tailwind + shadcn + Framer Motion
- **Copy/proposal:** Gemini Flash (free tier)
- **Hosting:** Vercel free tier (subdomains per client)
- **Email:** Gmail SMTP
- **Tracking:** Google Sheets (single source of truth)
- **Payments:** Wise / PayPal / bank wire

## Agents
1. **site-audit-agent** — scrapes client site, runs PageSpeed, applies heuristics, outputs problems + $ impact
2. **design-ref-agent** — pulls curated moodboard for vertical/style from ref sources
3. **copy-agent** — fills template text from business data + audit
4. **email-agent** — drafts personalized cold email (subject + body + audit summary + prototype link)
5. **proposal-agent** — generates 1-page proposal PDF after positive reply

## Pipeline (per lead)
1. Ingest lead row from Apollo CSV → create row in master Sheet
2. Audit current site → log problems + $ impact
3. Pull design references for vertical
4. Generate 3 UI variants × 4 pages via Stitch
5. Human approval gate (Harsh picks variant)
6. Build approved variant as Next.js prototype, fill copy, deploy to Vercel subdomain
7. Draft personalized cold email, queue for send
8. Send via Gmail SMTP (35/day cap, spaced)
9. Track opens/clicks/replies in Sheet
10. On positive reply → generate proposal PDF → send
11. On close → invoice via Wise → deliver → push to client domain

## Phases
- **Phase 0** — Environment + accounts + API keys (manual, Harsh)
- **Phase 1** — Reference scrapers (Are.na → Codrops → Awwwards → Cosmos → Pinterest)
- **Phase 2** — Audit engine (Firecrawl + PageSpeed + heuristics + $ translator)
- **Phase 3** — Design moodboard → DESIGN.md → Stitch design system
- **Phase 4** — Stitch screen generation (4 pages × 3 variants per lead)
- **Phase 5** — Approval gate (simple local web UI to view + approve)
- **Phase 6** — Prototype builder (Stitch design → Next.js page + copy fill + Vercel deploy)
- **Phase 7** — Email agent + Gmail SMTP send queue (35/day, scheduled spacing)
- **Phase 8** — Tracking layer (Sheets API, status updates per phase, open/click pixels)
- **Phase 9** — Reply handling + proposal-agent + PDF generation
- **Phase 10** — Orchestrator (CSV row → all phases automated, errors logged to Sheet)
- **Phase 11** — Manual test loop: 20 end-to-end leads, measure, iterate

## Master Sheet Columns
lead_id, name, business, vertical, email, site_url, audit_status, audit_url, audit_problems, audit_dollar_impact, ref_status, moodboard_url, stitch_status, stitch_variants_url, approved_variant, prototype_status, prototype_url, deployed_at, email_status, email_sent_at, email_subject, email_body, open_count, click_count, reply_status, reply_text, call_booked, call_date, proposal_status, proposal_url, proposal_sent_at, deal_status, amount_usd, payment_method, paid_at, notes, last_updated, error_log

## Success Criteria
- 20 leads processed end-to-end
- >5% reply rate
- 1+ deal closed before scaling
- Per-lead automated runtime <10 min compute + <2 min human approval

## Out of Scope (v1)
- Custom domains for sending email
- Multi-user dashboard
- Automated A/B copy testing
- Client revision workflow automation
- CRM integrations beyond Sheets
