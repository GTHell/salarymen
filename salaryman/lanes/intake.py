"""lanes/intake.py — INBOX receipts -> TODO cards. The backfill mechanism.

Vague user prompts land in BOARD.md INBOX verbatim (receipts, never edited).
Intake reads each unprocessed receipt, asks the driver LLM to decompose it
into 2-5 sized TODO cards with `from:` provenance and acceptance criteria,
then writes them to the board. The raw receipt stays untouched.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from ..board import Board
from ..drivers import get_driver
from ..events import EventLog

DECOMPOSE_PROMPT = """You are the intake worker of an app-building team.
The client wrote a vague request. Decompose it into 2-5 concrete build cards.

Rules:
- Each card: one deliverable feature or fix, sized S/M/L
- "accept" = acceptance criteria in plain language the critic can verify
  (prefer things checkable by a screenshot or HTTP probe)
- Reply ONLY with JSON: {{"cards": [{{"id": "feat|fix|perf|chore/<slug>",
  "size": "S|M|L", "title": "...", "accept": "..."}}, ...]}}

Client request:
\"\"\"{prompt}\"\"\"
"""


def _slug_ok(cid: str) -> bool:
    return bool(re.fullmatch(r"(feat|fix|perf|chore)/[a-z0-9-]+", cid))


def process_inbox(board_path: str | Path, project_dir: str | Path,
                  driver_name: str = "claude-code") -> list[dict]:
    """Decompose every INBOX receipt into TODO cards. Returns created cards."""
    board = Board(board_path).load()
    driver = get_driver(driver_name)
    created: list[dict] = []

    for receipt in list(board.cards["INBOX"]):
        if receipt.raw_text is None:
            continue
        existing_from = {c.meta.get("from")
                         for s in ("TODO", "DOING", "DONE")
                         for c in board.cards[s]}
        if receipt.id in existing_from:
            continue  # already decomposed

        brief = DECOMPOSE_PROMPT.format(prompt=receipt.raw_text)
        result = driver.run(brief, cwd=str(project_dir), timeout_s=300)
        cards_data = _extract_cards(result.stdout)
        if not cards_data:
            continue

        for c in cards_data[:5]:
            cid = c.get("id", "")
            if not _slug_ok(cid):
                cid = f"feat/{re.sub(r'[^a-z0-9]+', '-', str(c.get('title', 'card')).lower()).strip('-')[:40]}"
                if not _slug_ok(cid) or board.find(cid)[1] is not None:
                    cid = f"feat/{uuid.uuid4().hex[:8]}"
            if board.find(cid)[1] is not None:
                continue  # duplicate id
            card = board.add_todo(cid, size=c.get("size", "M"),
                                  title=c.get("title", ""),
                                  **{"from": receipt.id,
                                     "accept": c.get("accept", "")})
            created.append({"id": card.id, "size": card.size,
                            "title": card.title, "from": receipt.id})

    if created:
        board.save()
        EventLog(Path(board_path).parent / ".state" / "events.jsonl").emit(
            "intake.done", cards=created)
    return created


def _extract_cards(stdout: str) -> list[dict]:
    m = re.search(r"\{[\s\S]*\}", stdout)
    if not m:
        return []
    try:
        d = json.loads(m.group(0))
        return d.get("cards", []) if isinstance(d, dict) else []
    except json.JSONDecodeError:
        return []
