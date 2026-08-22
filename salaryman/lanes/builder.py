"""lanes/builder.py — TODO -> DOING -> DONE. One card per tick.

Pipeline doctrine: a builder tick picks the TOP TODO card, writes a self-
contained brief (card + acceptance criteria + project conventions), hands it
to a driver, and gates the result on tests before DONE. A failed gate moves
the card back to TODO with the failure recorded — never silent, never stuck
in DOING.
"""
from __future__ import annotations

from pathlib import Path

from ..board import Board
from ..config import load_config
from ..drivers import get_driver
from ..events import EventLog

BUILD_PROMPT = """You are a build worker on project "{name}" ({stack} stack).

Implement EXACTLY this card. Nothing else.

Card: {card_id} ({size})
Title: {title}
Acceptance criteria: {accept}

Rules:
- Work only inside this repository.
- Follow the existing code style; use the stack's conventions (no raw CSS,
  no ad-hoc frameworks).
- Run the project's own verification (tests/typecheck) yourself first.
- When everything passes, end your reply with a final line: TASK_PASS
- If you cannot finish, end with TASK_FAIL and one line why.
"""


def builder_tick(project_dir: str | Path) -> dict:
    """One phase: pick top TODO, dispatch to driver, gate, move card."""
    d = Path(project_dir)
    cfg = load_config(d)
    board = Board(d / cfg["project"]["board"]).load()

    if board.cards["DOING"]:
        return {"ok": False, "reason": "a card is already DOING — critic must clear it first"}

    todos = board.cards["TODO"]
    if not todos:
        return {"ok": True, "skipped": "board empty"}
    card = todos[0]

    # claim it
    b = Board(d / cfg["project"]["board"]).load()
    _, live = b.find(card.id)
    if live is None:
        return {"ok": False, "reason": "board changed under us"}
    b.move(card.id, "DOING", worker=cfg["workers"]["driver"])
    b.save()

    brief = BUILD_PROMPT.format(name=cfg["project"]["name"],
                                stack=cfg["stack"]["scaffold"],
                                card_id=card.id, size=card.size or "M",
                                title=card.title,
                                accept=card.meta.get("accept", "see title"))
    driver = get_driver(cfg["workers"]["driver"])
    result = driver.run(brief, cwd=str(d), timeout_s=int(cfg.get("builder_timeout_s", 1800)))

    passed = result.ok and "TASK_PASS" in (result.stdout or "")
    b = Board(d / cfg["project"]["board"]).load()
    events = EventLog(d / ".state" / "events.jsonl")
    if passed:
        evidence = f"driver={driver.name} {result.duration_s}s exit={result.exit_code}"
        b.move(card.id, "DONE", evidence=evidence)
        outcome = "done"
        events.emit("build.passed", card_id=card.id,
                    duration_s=result.duration_s)
    else:
        fail_note = (result.stderr or result.stdout or "")[:200]
        b.move(card.id, "TODO", last_fail=fail_note)
        outcome = "failed->back to TODO"
        events.emit("build.failed", card_id=card.id, note=fail_note)
    b.save()

    return {"ok": passed, "card": card.id, "outcome": outcome,
            "duration_s": result.duration_s}
