# Pitchcraft

> Pipeline that turns a CSV of local businesses into deployed prototype websites, audit PDFs, and growth proposals, ready to send.

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+"></a>
  <a href="#"><img src="https://img.shields.io/badge/node-18%2B-green" alt="Node 18+"></a>
  <a href="https://github.com/hp-8/pitchcraft/issues"><img src="https://img.shields.io/badge/contributions-welcome-orange.svg" alt="Contributions welcome"></a>
  <a href="https://github.com/hp-8/pitchcraft/stargazers"><img src="https://img.shields.io/github/stars/hp-8/pitchcraft?style=social" alt="GitHub stars"></a>
</p>

A solo-operator infrastructure for mass producing high quality prototype websites and matching sales collateral for local service businesses. Built around free tools, falls back gracefully when any single provider rate limits, and ships everything as portable static HTML plus PDFs.

## What it does

Given a CSV of leads, the pipeline:

1. **Audits** each current website (Firecrawl + PageSpeed Insights, scored against vertical heuristics).
2. **Pulls design references** from Are.na, Codrops, Awwwards, GSAP showcase, react-bits, and other curated sources.
3. **Synthesizes a brand brief** via the LLM fallback chain (Gemini, OpenAI, Anthropic, Groq, manual).
4. **Generates UI** via Stitch MCP using a per vertical design system.
5. **Polishes** the HTML output: scroll linked hero videos, vibe presets (radius, accent), animation primitives (Lenis, GSAP, Splitting), brand wordmark intro curtain, mobile fixes, performance pass.
6. **Builds + deploys** to Vercel with one project per client.
7. **Renders PDFs**: a one page growth proposal and a multi page revenue audit with calculation transparency and real competitor lookup via Firecrawl search.
8. **Bundles deliverables**: per lead folder with `proposal.pdf`, `audit.pdf`, `index.html` (share page with CTA and contact), `README.md`.

## Quickstart

```bash
# 1. Python env (uv managed). Install uv: https://docs.astral.sh/uv/getting-started/install/
uv sync
uv run playwright install        # one time, for Scrapling stealth fetchers

# 2. Node tooling (Vercel CLI)
npm install -g vercel

# 3. Env
cp .env.example .env             # fill in keys you have
mkdir -p secrets                 # drop service account JSONs here (gitignored)

# 4. Drop a lead CSV in data/leads/yourbatch.csv with columns:
#    lead_id, business, vertical, site_url, email, location, name
#    Verticals: restaurant | dental | realtor | fnb

# 5. Run the pipeline
uv run python -m tools.orchestrator run-batch \
    --leads data/leads/yourbatch.csv \
    --design-system-id <stitch_design_system_id> \
    --no-sheet --skip-deploy

# 6. Drive Stitch fulfillment via Claude Code skill (/stitch-batch),
#    then resume polish + build + deploy:
uv run python -m tools.orchestrator resume --leads data/leads/yourbatch.csv --no-sheet

# 7. Render PDFs + bundle:
uv run python -m tools.pdf batch  --leads data/leads/yourbatch.csv
uv run python -m tools.pdf bundle --leads data/leads/yourbatch.csv
open data/deliverables/INDEX.html
```

## LLM fallback chain

The pipeline never blocks on a single provider. Order is controlled by `LLM_PROVIDERS` in `.env`:

```
LLM_PROVIDERS=gemini,openai,anthropic,groq,manual
```

- Each provider is tried in order; first valid key wins.
- On rate limit, network failure, or missing key, the chain moves to the next provider.
- If every provider fails and `ALLOW_MANUAL_LLM=1`, the pipeline prints the prompt to stderr and waits for a pasted response from your terminal (use this when you want to copy the prompt into ChatGPT manually and paste the answer back).
- If manual is disabled, the pipeline downgrades to a template based fallback so generation never stops.

## Architecture

```
agents/         design_ref (moodboard -> DESIGN.md), council voices
tools/
  audit/        PageSpeed + Firecrawl heuristic audit
  scrapers/     Are.na, Codrops, Awwwards, GSAP, react-bits, Pexels, Unsplash
  keywords/     KeyBERT + LLM bucket / validation
  stitch/       Screen prompt builder, envelope fulfiller
  polisher/     Premium CSS, animation wire, hero video, perf, mobile fixes
  builder/      Static site assembly, Vercel deploy
  pdf/          Proposal + audit PDFs, deliverables bundler
  orchestrator/ Async per phase driver with semaphore caps
  llm/          Multi provider client with fallback chain
data/
  leads/        Input CSVs (gitignored)
  cache/        Scraper SQLite (gitignored)
  outputs/      Per lead intermediates (gitignored)
  deliverables/ Final per lead bundles (gitignored)
```

The orchestrator runs each lead through phases in parallel with per phase concurrency caps. Stitch fulfillment is the only manual handoff: it requires a Claude Code session because Stitch is only callable via MCP.

## Configuration reference

| Variable | Purpose |
|---|---|
| `LLM_PROVIDERS` | Comma separated order: `gemini,openai,anthropic,groq,manual` |
| `ALLOW_MANUAL_LLM` | `1` to allow terminal paste in when all providers fail |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Google AI Studio |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Anthropic |
| `GROQ_API_KEY` / `GROQ_MODEL` | Groq |
| `FIRECRAWL_API_KEY` | Web scraping + search (audits, competitor lookup) |
| `PAGESPEED_API_KEY` | Performance scoring |
| `VERCEL_TOKEN` | Production deploys |
| `GOOGLE_SHEETS_CREDENTIALS` | Optional, lead tracking |
| `GMAIL_*` | Optional, outreach phase |

See `.env.example` for the full list.

## Project structure

```
.
├── agents/                Domain agents (design_ref)
├── tools/                 Per phase modules + CLIs
├── tests/                 Unit + integration tests
├── data/                  Inputs, cache, outputs, deliverables (gitignored)
├── secrets/               Service account JSON (gitignored)
├── PLAN.md                Implementation plan
├── ARCHITECTURE.md        System architecture
├── CHECKPOINTS.md         Phase completion log
├── README.md              This file
├── LICENSE                MIT
├── .env.example           Env template
└── pyproject.toml         Python deps (uv)
```

## Contributing

Contributions are very welcome. This is a working solo operator pipeline; any of these are high value:

- **New verticals**: add seed keywords, design themes, and audit heuristics for new business categories (legal, accounting, fitness, contractors, etc.).
- **New LLM providers**: add a `_call_<provider>` function in `tools/llm/client.py`.
- **New design themes**: extend the vibe presets in `tools/polisher/_hero_video.py`.
- **New video / image sources**: extend `tools/scrapers/` with additional moodboard sources.
- **Audit heuristics**: add new problem detectors with revenue impact math in `tools/audit/`.
- **Deploy targets**: add a deployer alongside `tools/builder/_vercel.py` for Netlify, Cloudflare Pages, etc.

### Workflow

1. Fork and clone.
2. Create a branch: `git checkout -b feat/your-change`.
3. Install dev deps: `uv sync --all-extras`.
4. Run tests: `uv run pytest`.
5. Submit a PR with a clear description and a short demo (CSV row plus screenshot of generated output if possible).

### Code style

- Python: ruff for lint and format. Run `uv run ruff check . && uv run ruff format .` before pushing.
- Keep modules small and single purpose. The orchestrator is async; new phases follow the `phase_*` pattern.
- No new top level dirs without a clear owner.

### Filing issues

When filing a bug, include:
- The CSV row that triggered it (sanitized).
- The phase that failed (`audit`, `keywords`, `scrape`, `design_ref`, `stitch_envelope`, `polish`, `build`).
- Relevant log excerpts.

For feature requests, describe the use case before the proposed implementation.

## Security

This repository contains only infrastructure code. Lead data, generated outputs, credentials, and any client artifacts are gitignored and never reach the public repo. If you find a way to leak data through the pipeline, please open a security issue (or email `patadiaharsh.8@gmail.com`) before opening a public PR.

## License

[MIT](./LICENSE)

## Author

Built by [Harsh Patadia](https://www.harshpatadia.space/).

- GitHub: [@hp-8](https://github.com/hp-8)
- LinkedIn: [harsh-patadia](https://www.linkedin.com/in/harsh-patadia/)
- Substack: [@damnyouharsh](https://substack.com/@damnyouharsh)
