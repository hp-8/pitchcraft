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

## Screen request envelopes (Phase 4)

After a design system is registered, the screen prompt builder
(`tools/stitch/screens.py`) emits one combined envelope per lead at:

```
data/outputs/<lead_id>/stitch_screens_request.json
```

Shape (12 entries — 4 pages × 3 variants, stable order):

```json
{
  "lead_id": "lead_123",
  "business": "Joe's Pizza",
  "vertical": "restaurant",
  "design_system_id": "ds_abc",
  "created_at": "2026-05-20T12:00:00Z",
  "screens": [
    {
      "page": "landing",
      "variant_idx": 0,
      "variant_direction": "hero-video-parallax",
      "tool": "mcp__stitch__generate_screen_from_text",
      "args": {
        "prompt": "...full Stitch prompt...",
        "design_system_id": "ds_abc",
        "name": "lead_123-landing-v0"
      },
      "fulfilled": false,
      "target_path": "data/outputs/lead_123/stitch/landing-v0.json"
    }
  ]
}
```

### Per-screen `tool` field

Always the fully-qualified MCP name (`mcp__stitch__generate_screen_from_text`).
The orchestrator dispatches exactly this tool with `args` as kwargs.

### Orchestrator responsibilities (Phase 10)

For each envelope with at least one screen where `fulfilled == false`:

1. For each unfulfilled screen, call the named MCP tool with `args`.
2. Write the Stitch return payload to `target_path` (parents auto-created).
3. Flip that screen's `fulfilled` to `true` in the envelope.
4. When the whole envelope is fulfilled, update the master sheet:
   - `stitch_status = "ready"` (or `"partial"` if any errors)
   - `stitch_variants_url = <envelope path>` (already seeded by the Python
     writer when `sheets_client` was passed, but safe to re-write)
5. Persist the envelope back to disk after each screen so partial runs are
   resumable.

### Handling per-screen Stitch errors

Do NOT abort the whole batch on a single failure. Instead:

- Mark that screen `fulfilled: true` with an extra `error: "<repr>"` field.
- Skip writing `target_path` for that screen.
- Continue with the remaining screens.
- Final `stitch_status` is `"ready"` if all 12 succeeded, otherwise `"partial"`.

This keeps the approval gate (Phase 5) usable on whatever variants did render.
