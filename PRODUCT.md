# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

- Frontend: Next.js (App Router) + Tailwind, deployed on Vercel at `pitchcraft.harshpatadia.com`, in `web/`.
- Backend: FastAPI wrapping the existing Python `tools/` pipeline, hosted separately (Railway/Fly/operator machine) because the pipeline is long-running (Playwright, WeasyPrint, Stitch).

## Users

Day one: a single operator (the founder) running outbound for an agency. Password-gated, no multi-tenant accounts. Target buyer later: web/marketing agencies that sell redesigns, SEO and AEO retainers to local businesses. Multi-user, workspaces and white-label are deferred.

## Product Purpose

Turn a CSV of local businesses into qualified, ready-to-send pitches: an audit of their current site, a deployed prototype redesign, audit and proposal PDFs, and a personalized email. Success = replies and booked calls, not volume sent.

## Positioning

Pitch with the finished work. Each prospect gets their own redesigned site plus an evidence-backed audit before any conversation happens.

## Operating Context

Work runs in batches of leads (tens now, hundreds to thousands later). Pipeline phases per lead: keywords → audit → scrape refs → council brief → Stitch screens → approval → polish → build/deploy → PDFs → email. Some phases can stall on rate limits or the manual Stitch step. The operator reviews outputs and approves before anything is sent.

## Capabilities and Constraints

- Existing: CLI orchestrator (`tools.orchestrator run-batch/resume`), LLM fallback chain, Flask/FastAPI approval app (`tools/approval/app.py`), PDF render and bundle, Gmail SMTP send.
- Verticals: restaurant, dental, realtor, fnb.
- Stitch generation currently requires a Claude Code session (not callable from Python).
- Planned: SEO + AEO crawler, Google Maps lead sourcing with qualification scoring, follow-up sequences, reply/open tracking.

## Evidence on Hand

No customers, testimonials, reply-rate data or case studies yet. Never fabricate them.

## Product Principles

1. Quality over volume: nothing reaches a prospect without operator approval.
2. Scale-ready: every list and view must work at 1,000+ leads.
3. Show the state honestly: stalled, failed and manual-step leads are visible, never hidden.
4. Agency-grade output: what a prospect sees reflects on the agency's brand.
