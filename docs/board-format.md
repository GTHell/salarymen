# BOARD.md — kanban format spec

The board is plain markdown. Parseable by humans, git, GitHub Projects sync,
and the salarymen workers. One file, four sections = four columns.

```markdown
# BOARD — <project name>

## 📥 INBOX
<!-- raw user prompts land here verbatim; intake decomposes them -->

- p2026-08-22-001 [raw] "make the shop page faster and add discount codes"

## 📋 TODO
- feat/discount-codes (M) — codes with %/fixed, expiry, per-product scope
  from: p2026-08-22-001
  accept: code applies at checkout; expired code rejected; screenshot of apply flow
- perf/shop-page (S) — lazy-load product images
  from: p2026-08-22-001
  accept: LCP < 2.5s on 3G profile

## 🔨 DOING
- feat/cart (M) @builder tick#142
  branch: worker/feat-cart

## ✅ DONE
- feat/auth [x] (merged #34)
  evidence: screenshots/auth-flow.png · probe /api/me → 200 · vision: PASS
```

## Card anatomy

- **id**: `feat|fix|perf|chore/<slug>` — stable, referenced by evidence + commits
- **size**: S/M/L — builder ticks estimate; L must be split before DOING
- **from**: inbox id — provenance chain from vague prompt to card (the backfill mechanism)
- **accept**: acceptance criteria in user language — critic judges against THIS
- **evidence** (DONE cards only): screenshot path + live-probe result + verdict

## Lifecycle rules (enforced by auditor)

1. INBOX lines are NEVER edited — they are receipts.
2. No card enters DONE without an evidence block.
3. A card whose evidence contradicts its claim is reopened with `reopened:N`.
4. Board diffs are the changelog: `git log BOARD.md` = project history.
