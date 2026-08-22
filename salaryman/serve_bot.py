"""serve_bot.py — thin Telegram renderer over the event spine.

Inbound: texts become INBOX receipts (same as CLI `salaryman inbox`).
Outbound: polls the event tail, formats lane events, pushes to the owner chat.
Screenshots referenced by evidence events are sent as photos.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from .board import Board
from .events import EventLog

API = "https://api.telegram.org/bot{token}/{method}"


def _tg(token: str, method: str, payload: dict) -> dict:
    req = urllib.request.Request(
        API.format(token=token, method=method),
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def send_message(token: str, chat_id: str | int, text: str) -> None:
    _tg(token, "sendMessage", {"chat_id": chat_id, "text": text[:4000],
                               "parse_mode": "Markdown"})


def send_photo(token: str, chat_id: str | int, png_path: Path, caption: str = "") -> None:
    boundary = "----salaryman"
    boundary_bytes = boundary.encode()
    with open(png_path, "rb") as f:
        img = f.read()
    body = b"--" + boundary_bytes + b"\r\n"
    body += b'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
    body += str(chat_id).encode() + b"\r\n"
    if caption:
        body += b"--" + boundary_bytes + b"\r\n"
        body += b'Content-Disposition: form-data; name="caption"\r\n\r\n'
        body += caption.encode() + b"\r\n"
    body += b"--" + boundary_bytes + b"\r\n"
    body += b'Content-Disposition: form-data; name="photo"; filename="shot.png"\r\n'
    body += b"Content-Type: image/png\r\n\r\n" + img + b"\r\n"
    body += b"--" + boundary_bytes + b"--\r\n"
    req = urllib.request.Request(
        API.format(token=token, method="sendPhoto"), data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    urllib.request.urlopen(req, timeout=60)


def format_event(evt: dict, project_name: str) -> str:
    t = evt["type"]
    icon = {"build.passed": "✅", "build.failed": "❌", "card.created": "📝",
            "card.moved": "🔀", "evidence.attached": "📸",
            "deploy.done": "🚀", "intake.done": "📥", "audit.done": "🔍"}.get(t, "•")
    if t == "intake.done":
        cards = evt.get("cards", [])
        lines = [f"{icon} intake: {len(cards)} new card(s)"]
        lines += [f"  • {c['id']} ({c.get('size','M')}) {c.get('title','')}" for c in cards[:5]]
        return "\n".join(lines)
    if t == "card.moved":
        return f"{icon} {evt.get('card_id')} → {evt.get('to')}"
    if t in ("build.passed", "build.failed"):
        return f"{icon} {evt.get('card_id')}: {'DONE' if t=='build.passed' else 'FAILED — back to TODO'} ({evt.get('duration_s','?')}s)"
    if t == "evidence.attached":
        return f"{icon} evidence attached to {evt.get('card_id')} (screenshot available)"
    if t == "deploy.done":
        return f"{icon} deployed: {evt.get('url', 'see logs')}"
    return f"{icon} {t}: {json.dumps({k: v for k, v in evt.items() if k not in ('ts','type')})[:200]}"


def poll_updates(token: str, offset: int) -> tuple[list[dict], int]:
    r = _tg(token, "getUpdates", {"offset": offset, "timeout": 25})
    updates = r.get("result", [])
    new_offset = offset
    for u in updates:
        new_offset = max(new_offset, u["update_id"] + 1)
    return updates, new_offset


def add_to_inbox(board_path: Path, text: str) -> str:
    board = Board(board_path).load()
    n = len(board.cards["INBOX"]) + 1
    card_id = f"p{n:03d}"
    board.add_inbox(card_id, text)
    board.save()
    events = EventLog(board_path.parent / ".state" / "events.jsonl")
    events.emit("card.created", card_id=card_id, source="telegram",
                raw=text[:200])
    return card_id


def serve(project_dir: str | Path, token: str, owner_chat_id: str | int,
          poll_interval_s: int = 5) -> None:
    d = Path(project_dir)
    cfg_board = d / "BOARD.md"
    events = EventLog(d / ".state" / "events.jsonl")
    cursor_path = d / ".state" / "bot_cursor"

    last_ts = float(cursor_path.read_text()) if cursor_path.exists() else 0.0
    offset = 0
    print(f"salaryman bot live for chat {owner_chat_id}; polling events since {last_ts}")
    while True:
        # inbound: telegram texts -> INBOX
        try:
            updates, offset = poll_updates(token, offset)
        except Exception as e:
            print("tg poll error:", e)
            updates = []
        for u in updates:
            msg = u.get("message") or {}
            chat = str(msg.get("chat", {}).get("id", ""))
            text = (msg.get("text") or "").strip()
            if chat == str(owner_chat_id) and text:
                cid = add_to_inbox(cfg_board, text)
                send_message(token, owner_chat_id,
                             f"📥 received as {cid} — intake will decompose it")

        # outbound: new events -> formatted push
        for evt in events.since(last_ts):
            last_ts = max(last_ts, evt["ts"])
            try:
                send_message(token, owner_chat_id,
                             format_event(evt, cfg_board.parent.name))
                shot = evt.get("screenshot")
                if shot and Path(shot).exists():
                    send_photo(token, owner_chat_id, Path(shot),
                               caption=f"evidence: {evt.get('card_id','')}")
            except Exception as e:
                print("push error:", e)

        cursor_path.parent.mkdir(parents=True, exist_ok=True)
        cursor_path.write_text(str(last_ts))
        time.sleep(poll_interval_s)
