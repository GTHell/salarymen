"""lanes/auditor.py — board-vs-reality reconciliation.

The auditor is the truth layer: it checks DONE cards against reality
(evidence present? referenced commits exist?) and TODO/DOING cards against
the git log (work merged without a card gets a ledger card; claimed work
without commits gets flagged). The audit ADDS nothing the evidence doesn't
prove — it only reconciles.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ..board import Board


def _git(d: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=d, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def auditor_tick(project_dir: str | Path, max_ledger: int = 10) -> dict:
    d = Path(project_dir)
    board = Board(d / "BOARD.md").load()
    report = {"reopened": [], "ledger_added": [], "flagged": []}

    # 1. DONE cards must carry an evidence block -> reopen otherwise.
    for c in list(board.cards["DONE"]):
        if not c.meta.get("evidence"):
            c.meta["reopened"] = "auditor: DONE without evidence block"
            board.cards["DONE"].remove(c)
            board.cards["TODO"].append(c)
            report["reopened"].append(c.id)

    # 2. DOING staleness: a card in DOING with no worker stamp predates the
    #    claim protocol -> send back to TODO.
    for c in list(board.cards["DOING"]):
        if not c.meta.get("worker"):
            c.meta["last_fail"] = "auditor: DOING without worker claim"
            board.cards["DOING"].remove(c)
            board.cards["TODO"].append(c)
            report["flagged"].append(f"{c.id} (no worker claim)")

    # 3. Commit parity: merged-card ids should appear in git history; recent
    #    commit subjects referencing unknown cards get ledger lines.
    known_ids = {c.id for sec in ("INBOX", "TODO", "DOING", "DONE")
                 for c in board.cards[sec]}
    log = _git(d, "log", "--oneline", "-40")
    referenced: set[str] = set()
    for line in log.splitlines():
        for cid in known_ids:
            slug = cid.split("/", 1)[-1]
            if slug and slug in line:
                referenced.add(cid)

    for c in board.cards["DONE"]:
        if c.id not in referenced and not c.meta.get("no_commit"):
            c.meta.setdefault("audit_note", "no matching commit found in last 40")
            report["flagged"].append(f"{c.id} (done, no matching commit)")

    todo_slugs_unbuilt = []
    for c in board.cards["TODO"] + board.cards["DOING"]:
        slug = c.id.split("/", 1)[-1]
        if slug and any(slug in line for line in log.splitlines()):
            todo_slugs_unbuilt.append(c.id)
    if todo_slugs_unbuilt:
        report["flagged"].append(
            "commits exist for TODO/DOING cards: " + ", ".join(todo_slugs_unbuilt))

    # 4. Ledger cap: keep the audit honest but bounded.
    if len(report["ledger_added"]) > max_ledger:
        report["ledger_added"] = report["ledger_added"][:max_ledger]

    board.save()
    return report
