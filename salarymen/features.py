"""features.py — auto-generate docs/features/<id>.md from DONE card history.

Nobody writes feature docs by hand. When a card reaches DONE with evidence,
its history (provenance chain: inbox receipt -> cards -> evidence) IS the
documentation. The auditor/backfill renders it.
"""
from __future__ import annotations

import json
from pathlib import Path

from .board import Board


def _card_doc(card, section: str, receipts: dict | None = None) -> str:
    lines = [
        f"# {card.id}",
        "",
        f"**Title:** {card.title}",
        f"**Status:** {section.lower()}",
        f"**Size:** {card.size or '—'}",
        "",
    ]
    origin = (receipts or {}).get((card.meta or {}).get("from"))
    if origin:
        lines += ["## Original request", "", f'> "{origin}"', ""]
    if card.raw_text is not None:
        lines += ["## Original request", "", f'> "{card.raw_text}"', ""]
    for k, v in card.meta.items():
        lines.append(f"**{k}:** {v}  ")
    if section == "DONE" and card.meta.get("evidence"):
        lines += ["", "## Evidence", "", f"`{card.meta['evidence']}`"]
    return "\n".join(lines) + "\n"


def backfill(board_path: str | Path, out_dir: str | Path,
             force: bool = False) -> list[str]:
    """Write/update docs/features/<id>.md for every non-INBOX card.

    Returns ids whose docs were created or updated. Existing docs are only
    rewritten when `force=True` or the card content changed (hash check via
    the rendered doc itself).
    """
    board = Board(board_path).load()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    receipts = {c.id: c.raw_text for c in board.cards["INBOX"]}
    for section in ("TODO", "DOING", "DONE"):
        for card in board.cards[section]:
            doc_path = out / f"{card.id.replace('/', '-')}.md"
            content = _card_doc(card, section, receipts)
            if force or not doc_path.exists() or doc_path.read_text() != content:
                doc_path.write_text(content, encoding="utf-8")
                written.append(card.id)
    return written
