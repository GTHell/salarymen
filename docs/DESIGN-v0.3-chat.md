# DESIGN v0.3 — the Devin surface: chat IS the workspace

## The pivot (owner, 08-23)
`salaryman.fasttunnel.xyz` = a full chat UI (Devin-style). You talk; workers
build; **the built app renders live inside the chat**. cafe.fasttunnel.xyz
becomes the deployed artifact viewable in-place.

## Architecture

```
browser ── salaryman.fasttunnel.xyz (chat UI, Next.js on :3460)
             │  POST /api/chat      → user message → INBOX + trigger lanes
             │  GET  /api/events?since=ts   → event spine tail (SSE/poll)
             │  iframe /preview     → live app (cafe.fasttunnel.xyz or :3457)
             ▼
        event spine (.state/events.jsonl)   ← lanes emit (already done)
```

## Chat UX contract (Devin-like)

- User: "build me a cafe ordering site"
- Assistant bubble streams lane progress as it happens:
  - 📥 decomposed into 5 cards (list them)
  - 🔨 building feat/db-foundation… ✅ passed (1m12s)
  - 🔨 building feat/api-routes…
- When cards DONE with screenshots: evidence card inline (image + probe result)
- Right pane / tab: **live preview** of the built app (iframe to deploy target)
- Board state always visible as a compact strip (5/5 ✓)

## Implementation slices

1. **chat server** (`salaryman serve-web`, :3460): static chat page + two APIs
   (POST /api/chat → inbox receipt; GET /api/events → JSON tail). No framework —
   same stdlib pattern as ctlplane.
2. **lane trigger**: POST /api/chat runs `tick intake` synchronously-ish then
   spawns builder ticks sequentially in background (subprocess, detached).
3. **preview pane**: iframe pointing at the running app URL from config
   (`engine.preview_url`), auto-refreshes when a build.passed event arrives.
4. **expose**: caddy block `salaryman.fasttunnel.xyz` → :3460 behind authelia.

## Non-goals v0.3

- No auth beyond authelia gate. No multi-user. No websocket — 2s polling of
  /api/events is enough for v0.3.
