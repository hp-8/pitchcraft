---
name: Bug report
about: Something broke during pipeline execution
title: "[bug] "
labels: bug
assignees: ''
---

## What happened

A short description.

## Where it broke

Phase: <audit | keywords | scrape | design_ref | stitch_envelope | polish | build | pdf>

## Reproduction

CSV row (PII removed):
```csv
lead_id,business,vertical,site_url,email,location,name
```

Command:
```
uv run python -m tools.orchestrator ...
```

## Logs

```
paste relevant log lines
```

## Environment

- OS:
- Python version: `uv run python --version`
- LLM_PROVIDERS:
- Any provider you confirmed reachable:
