# Website Generator

Mass-generate high-quality 4-page websites + cold outreach for US local service businesses (restaurants, dentists, realtors, FnB).

See [`PLAN.md`](./PLAN.md) for the full implementation plan, phases, and master-sheet schema.

## Quickstart

```bash
# 1. Python env (uv-managed). Install uv: https://docs.astral.sh/uv/getting-started/install/
uv sync
uv run playwright install   # one-time, for Scrapling stealth fetchers

# 2. Node tooling (orchestrator root). Per-vertical Next.js apps under /templates/* have their own package.json.
npm install

# 3. Env
cp .env.example .env        # then fill in API keys
mkdir -p secrets            # drop service-account JSONs here (gitignored)
```

## Folder map

```
/agents       site-audit, design-ref, copy, email, proposal
/tools        scrapers (Scrapling), audit (Firecrawl+PageSpeed), stitch, sheets, gmail, pdf
/templates    per-vertical Next.js templates: restaurant, dental, realtor, fnb
/pipeline     orchestrator (CSV row -> all phases)
/data         leads/ (Apollo CSVs), cache/ (SQLite), outputs/ (moodboards, audits, prototypes)
/scripts      one-off CLI scripts
/docs         design notes, runbooks
/secrets      service-account JSONs (gitignored)
```

## Notes

- Free tools only until first revenue.
- Gmail SMTP, 35 emails/day cap.
- Root `package.json` is for orchestrator tooling; each `/templates/<vertical>` will have its own Next.js app scaffold (created in Phase 6).
