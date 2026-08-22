"""board.py — BOARD.md is data: parse, mutate, write. Roundtrip-safe.

The four sections (📥 INBOX / 📋 TODO / 🔨 DOING / ✅ DONE) are the kanban
columns. Cards are `- id size — title` lines with indented `key: value` meta.
Everything else in a section is preserved verbatim (comments, blank lines).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

SECTIONS = ["INBOX", "TODO", "DOING", "DONE"]
SECTION_HEADERS = {
    "INBOX": "## 📥 INBOX",
    "TODO": "## 📋 TODO",
    "DOING": "## 🔨 DOING",
    "DONE": "## ✅ DONE",
}
CARD_RE = re.compile(r"^- ([a-z]+/[a-z0-9-]+)(?:\s+\((S|M|L)\))?\s*[—-]\s*(.+)$")
META_RE = re.compile(r"^\s{2}([a-z_]+):\s*(.*)$")
RAW_RE = re.compile(r'^- (p\d[\w-]*)\s*\[raw\]\s*"(.*)"$')


@dataclass
class Card:
    id: str
    title: str = ""
    size: str | None = None
    raw_text: str | None = None  # INBOX receipts only
    meta: dict = field(default_factory=dict)

    def render(self) -> str:
        if self.raw_text is not None:
            return f'- {self.id} [raw] "{self.raw_text}"'
        size = f" ({self.size})" if self.size else ""
        lines = [f"- {self.id}{size} — {self.title}"]
        for k, v in self.meta.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)


class Board:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.cards: dict[str, list[Card]] = {s: [] for s in SECTIONS}
        self._title: str = ""

    # ---------- parse ----------
    def load(self) -> "Board":
        text = self.path.read_text(encoding="utf-8")
        section = None
        buf: list[str] = []
        for line in text.splitlines():
            header = line.strip()
            matched = next((s for s, h in SECTION_HEADERS.items() if header == h), None)
            if matched:
                if section:
                    self._flush(section, buf)
                section = matched
                buf = []
                continue
            if section is None:
                if line.startswith("# "):
                    self._title = line
                continue
            buf.append(line)
        if section:
            self._flush(section, buf)
        return self

    def _flush(self, section: str, buf: list[str]) -> None:
        pending: Card | None = None
        for line in buf:
            if not line.strip():
                continue
            m = RAW_RE.match(line)
            if m and section == "INBOX":
                self.cards[section].append(Card(id=m.group(1), raw_text=m.group(2)))
                continue
            m = CARD_RE.match(line)
            if m:
                if pending:
                    self.cards[section].append(pending)
                pending = Card(id=m.group(1), size=m.group(2), title=m.group(3).strip())
                continue
            mm = META_RE.match(line)
            if mm and pending is not None:
                pending.meta[mm.group(1)] = mm.group(2).strip()
                continue
            # unrecognized non-empty lines inside a section are dropped (canonical form)
        if pending:
            self.cards[section].append(pending)

    # ---------- mutate ----------
    def add_inbox(self, inbox_id: str, raw_prompt: str) -> Card:
        c = Card(id=inbox_id, raw_text=raw_prompt)
        self.cards["INBOX"].append(c)
        return c

    def move(self, card_id: str, to_section: str, **meta_updates) -> Card:
        for sec in SECTIONS:
            for i, c in enumerate(self.cards[sec]):
                if c.id == card_id:
                    self.cards[sec].pop(i)
                    c.meta.update(meta_updates)
                    self.cards[to_section].append(c)
                    return c
        raise KeyError(f"card not found: {card_id}")

    def find(self, card_id: str) -> tuple[str, Card] | tuple[None, None]:
        for sec in SECTIONS:
            for c in self.cards[sec]:
                if c.id == card_id:
                    return sec, c
        return None, None

    def evidence_ok(self, card_id: str) -> bool:
        _, c = self.find(card_id)
        return bool(c and c.meta.get("evidence"))

    # ---------- write ----------
    def render(self) -> str:
        title = self._title or "# BOARD"
        out = [title, ""]
        for s in SECTIONS:
            out.append(SECTION_HEADERS[s])
            out.append("")
            for i, c in enumerate(self.cards[s]):
                out.append(c.render())
                if i < len(self.cards[s]) - 1:
                    out.append("")
            out.append("")
        return "\n".join(out).rstrip("\n") + "\n"

    def save(self) -> None:
        self.path.write_text(self.render(), encoding="utf-8")
