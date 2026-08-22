# salaryman v0.2 DESIGN — chatbot-first on the event spine
(Gauntlet verdict 2026-08-22, unanimous 5-0: SYNTHESIS)

## Locked decisions

1. **v0.2 surface = thin Telegram bot** (`salaryman serve-bot`) over existing lanes.
   No daemon webapp. Bot token from `TELEGRAM_BOT_TOKEN` env; owner's chat id allowlist.
2. **Event spine is THE product**: append-only `.state/events.jsonl`. Every lane action
   emits a typed event: `card.created`, `card.moved`, `build.passed`, `build.failed`,
   `evidence.attached`, `deploy.done`. Lanes emit; renderers consume.
3. **Telegram adapter = dumb renderer**: reads the event tail, pushes formatted updates +
   screenshots to the owner chat; inbound texts become INBOX receipts (same as CLI inbox).
4. **HYBRID-WEBCHAT deferred to v0.3**: local web UI consuming the same event spine as a
   rich-card renderer. Design constraint now: events must be self-contained enough to
   render without re-reading BOARD.md.
5. **CLI survives forever** as cron invocation + power-user/debug hatch.

## The one-shot test (proves the loop end-to-end)

Pick ONE real app, one-shot it through salaryman itself:
- App: **"salaryman cafe"** — a real cafe site+orders demo (menu, order form, orders list).
  Real enough to not be slop: menu items from SQLite, working order flow, admin list.
- Flow: fresh dir → `salaryman init` → `inbox "cafe site with menu + ordering"` →
  `tick intake` → builder ticks until board done → critic probes+screenshot each DONE card
  → auditor reconciles → docs generated → serve locally for human verification.
- Pass criteria (all must hold):
  - app builds and serves HTTP 200 with real content
  - every DONE card has evidence block
  - zero unevidenced claims after auditor
  - event log contains full history of the run
  - human (owner) judges "not slop" from screenshots

## Build gauntlet for v0.2 implementation

1. BUILDER pass: implement event spine + Telegram bot + one-shot driver script.
2. CRITIC pass (fresh context): probe the built system + the demo app; verify all pass criteria.
3. ORCHESTRATOR diff + fix tasks; max 3 rounds.
