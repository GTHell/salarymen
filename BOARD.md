# BOARD — salaryman (dogfood: this repo builds itself)

<!-- The project dogfoods its own loop. Cards below are the v0.1 build plan. -->

## 📥 INBOX

- p001 [raw] "opinionated scaffold: minutes to live URL, swappable engine blocks"
- p002 [raw] "kanban from tasks.md, evidence on every done card, no more asking status"

## 📋 TODO

(none)

## 🔨 DOING

(none)

## ✅ DONE

- feat/board-parse (M) — board.py: parse/write the 4-section format, roundtrip safe
  from: p002
  accept: parse→mutate→write produces identical formatting; unit tests
  evidence: git 2e6e8e3 · test_board.py PASS (roundtrip)
- feat/config-layers (M) — salaryman.yml loader with defaults<file<local<cli merge
  from: p001
  accept: later layer wins per key; malformed file → clear error
  evidence: git a0428f0 · test_config.py PASS (layer merge + validation)
- feat/intake (L) — INBOX → TODO decomposition via driver LLM call, provenance `from:`
  from: p001,p002
  accept: vague 1-line prompt yields 2-5 sized cards each citing inbox id
  evidence: git 5d6afdb · test_intake.py PASS (provenance, no double-process)
- feat/builder (M) — one-card-per-tick lane with TASK_PASS gate and fail-to-TODO
  from: design
  accept: each tick takes exactly one TODO card; success stamps evidence, failure returns card
  evidence: git 0068349 · test_builder.py PASS
- feat/critic (M) — live probe + screenshot + optional vision judge → evidence
  from: design
  accept: DONE card without probe evidence is reopened; dead URL → reopen
  evidence: git c9bf5b9 · test_critic.py PASS
- feat/auditor (M) — board-vs-git reconciliation (reopen unevidenced, flag drift)
  from: design
  accept: DONE without evidence block reopens; merged work without card → ledger line
  evidence: git 096d144 · test_auditor.py PASS
- feat/deploy (S) — vercel lane via CLI (preview/prod, token from VERCEL_TOKEN)
  from: design
  accept: salaryman deploy prints live URL; prod flag deploys production
  evidence: git 0b41251 · CLI vercel lane (preview/prod)
- feat/docs (S) — auto-generate docs/features/<id>.md from board history with provenance
  from: design
  accept: every DONE card renders a feature doc; no hand-written docs
  evidence: git d3d0fba · test_features.py PASS
