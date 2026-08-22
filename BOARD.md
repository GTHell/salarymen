# BOARD — salarymen (dogfood: this repo builds itself)

<!-- The project dogfoods its own loop. Cards below are the v0.1 build plan. -->

## 📥 INBOX
- p001 [raw] "opinionated scaffold: minutes to live URL, swappable engine blocks"
- p002 [raw] "kanban from tasks.md, evidence on every done card, no more asking status"

## 📋 TODO
- feat/board-parse (M) — board.py: parse/write the 4-section format, roundtrip safe
  from: p002
  accept: parse→mutate→write produces identical formatting; unit tests
- feat/config-layers (M) — salaryman.yml loader with defaults<file<local<cli merge
  from: p001
  accept: later layer wins per key; malformed file → clear error
- feat/intake (L) — INBOX → TODO decomposition via driver LLM call, provenance `from:`
  from: p001,p002
  accept: vague 1-line prompt yields 2-5 sized cards each citing inbox id
- feat/critic (L) — dev-server probe + screenshot + optional vision verdict
  from: p002
  accept: DONE requires evidence block; missing evidence → reopen
- feat/auditor (M) — board vs git/tests reconciliation pass
  from: p002
  accept: claimed-done w/o evidence reopened; merged-without-card closed
- chore/cli-init (S) — salarymen init: copy template + render yml + seed board
  from: p001
  accept: fresh dir → runnable app + board in <60s

## 🔨 DOING
(none)

## ✅ DONE
(none)
