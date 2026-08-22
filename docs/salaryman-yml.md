# salaryman.yml — composition layer reference

Inspired by DeepSeek Harness (dsh) / Cordis: behavior = **ordered patch layers
over an empty root**; later layers win per row. No central registry. The user's
`salaryman.yml` IS the product definition — agents edit this file, not code,
when the "engine block" changes.

## Format

```yaml
# salaryman.yml — one project, one file
project:
  name: my-shop
  board: BOARD.md            # kanban lives here

stack:                        # opinionated template id (templates/<id>/)
  scaffold: next-tailwind-sqlite   # mature production defaults, never raw html/css

engine:                       # swappable "engine blocks" — swap by editing, agents migrate
  db: sqlite                  # sqlite | postgres | mysql | turso ...
  auth: lucia                 # provider per stack template
  deploy: vercel              # vercel | cloudflare | docker | self-host

lanes:                        # worker cadence (cron)
  intake:  every 30m          # prompts -> board cards
  builder: every 10m          # card -> implementation + tests
  critic:  every 15m          # live-probe + screenshot + vision judge
  auditor: every 3h           # board-vs-reality reconciliation

workers:                      # which agent harness executes lanes
  driver: claude-code         # claude-code | codex | pi | opencode | dsh
  model: any                  # resolved by driver; salaryman is model-agnostic

verify:                       # evidence contract — every DONE card must have these
  screenshots: true           # attached to card on pass/fail
  live_probe: true            # HTTP probe of the running app
  vision_judge: optional      # screenshot reviewed by a VLM when available
```

## Rules

1. **Layers compose**: `salaryman.yml` + `salaryman.local.yml` (gitignored) +
   CLI `--patch key=value`. Later wins per key. Agents never edit source to
   change an engine block — they edit this file and run the migration lane.
2. **Board is truth**: if a card says done but has no evidence block, the
   auditor reopens it. If evidence exists but the card is open, the auditor
   closes it.
3. **One phase per tick**: a builder tick implements ONE card or fails trying.
   No multi-card ticks (foreman pipeline doctrine).
