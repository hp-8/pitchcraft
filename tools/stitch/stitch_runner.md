# Stitch MCP boundary

This project uses Stitch through its **MCP server**, not a REST API or a Python
SDK. MCP tools (`mcp__stitch__*`) are only callable from inside a running
Claude Code session. A normal Python subprocess — including every agent in
`agents/` — cannot dispatch them.

To keep that boundary clean, the design-ref agent **emits an envelope** instead
of trying to call Stitch directly.

## Envelope contract

For every design system the agent wants registered, it writes:

```
data/outputs/<slug>/stitch_request.json
```

```json
{
  "tool": "create_design_system_from_design_md",
  "args": {
    "name": "<vertical> — <style> (<slug>)",
    "design_md_path": "data/outputs/<slug>/DESIGN.md"
  },
  "queued_at": "2026-05-20T12:00:00Z",
  "fulfilled": false
}
```

## Orchestrator responsibilities (Phase 10)

The orchestrator runs **inside Claude Code**, so it can:

1. Glob for `data/outputs/*/stitch_request.json` with `fulfilled == false`.
2. For each request, invoke the named MCP tool with the supplied args
   (`mcp__stitch__create_design_system_from_design_md`, etc.).
3. Persist the result to `data/outputs/<slug>/stitch_design_system.json`:

   ```json
   {
     "id": "<stitch-returned-id>",
     "name": "...",
     "created_at": "...",
     "source_design_md_path": "data/outputs/<slug>/DESIGN.md"
   }
   ```

4. Flip the envelope's `fulfilled` flag (or delete it) so reruns are idempotent.

## Why not just shell out?

There is no public Stitch CLI today. The only first-class interface is MCP.
A Python wrapper that pretended to call Stitch would either lie or shell into
Claude Code itself — both worse than an explicit boundary.

## Stub

`stitch_runner.create_design_system` exists for typing/mocking; it raises
`NotImplementedError`. The design-ref agent calls it in a try/except so the
envelope is always written even when the stub blows up — this keeps the design
phase decoupled from MCP availability.
