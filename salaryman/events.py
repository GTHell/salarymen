"""events.py — the salaryman event spine (append-only JSONL).

Every lane action emits a typed, self-contained event. Renderers (Telegram
bot, future webchat) consume this stream without re-reading BOARD.md.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

VALID_TYPES = {
    "card.created", "card.moved", "build.passed", "build.failed",
    "evidence.attached", "deploy.done", "intake.done", "audit.done",
}


class EventLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, type_: str, **data) -> dict:
        if type_ not in VALID_TYPES:
            raise ValueError(f"unknown event type: {type_} (valid: {sorted(VALID_TYPES)})")
        evt = {"ts": time.time(), "type": type_, **data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")
        return evt

    def tail(self, n: int = 50) -> list[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines[-n:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def since(self, ts: float) -> list[dict]:
        """Events after ts — the bot's polling cursor."""
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
                if e.get("ts", 0) > ts:
                    out.append(e)
            except json.JSONDecodeError:
                continue
        return out
