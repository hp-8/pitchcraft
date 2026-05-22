# Contributing

Thanks for considering a contribution. This project is meant to be useful to anyone who runs a small agency or a solo freelance operation, so improvements that lower the barrier to use are especially welcome.

## Where to start

- Skim [`README.md`](./README.md) and [`PLAN.md`](./PLAN.md) for the big picture.
- Browse open issues labeled `good first issue` and `help wanted`.
- For larger changes, open an issue first to align on scope.

## Setup

```bash
uv sync --all-extras
uv run playwright install
cp .env.example .env             # add any keys you have
```

You do not need every API key to develop. The LLM fallback chain lets you use any one provider, or run with `ALLOW_MANUAL_LLM=1` and paste responses from a free chat UI.

## Running the test suite

```bash
uv run pytest
```

If you add a phase or a new LLM provider, add a unit test alongside it.

## Code style

- Python: ruff for lint and format.
  ```bash
  uv run ruff check .
  uv run ruff format .
  ```
- Keep modules small. The orchestrator pattern is `phase_<name>` for async coroutines and `_<name>_sync` for the blocking core.
- Type hints required for new public functions.
- No new top level directories without a clear owner.

## Pull requests

1. Branch from `main`: `git checkout -b feat/your-change`.
2. Make your change. Add or update tests.
3. Run `uv run ruff check . && uv run pytest`.
4. Open a PR with:
   - A one line summary.
   - A description of the use case.
   - A before/after artifact when possible (CSV row in, generated HTML or PDF out).

We squash merge. Keep commits clean but the PR title is what ends up in history.

## Adding a new LLM provider

1. Add `_call_<provider>(prompt, *, json_mode)` to `tools/llm/client.py`.
2. Register it in `_PROVIDERS`.
3. Add the env keys to `.env.example` and the table in `README.md`.
4. Add a happy path test in `tests/llm/`.

## Adding a new vertical

1. Add seed keywords in `tools/keywords/bucket.py` (`_FALLBACK_BUCKETS`).
2. Add a vertical baseline range in `tools/pdf/audit.py` (`vertical_baselines`).
3. Add a competitor query template in `tools/pdf/_competitors.py` (`_VERTICAL_QUERIES`).
4. Add a hero video pool entry in `tools/polisher/_hero_video.py` (`_VIDEO_POOL`).
5. Add a test CSV row in `tests/fixtures/`.

## Filing bugs

Include:
- The CSV row that triggered it (with PII removed).
- The phase that failed.
- The relevant log excerpt.
- Your `LLM_PROVIDERS` value if the issue is LLM related.

## Security

If your contribution touches credential handling, scraping, or anything that could leak client data, please flag it explicitly in the PR description. Lead data and outputs must never be checked in.
