#!/usr/bin/env python3
"""salaryman — self-hosted app-building loop.

  salaryman init <dir>     scaffold a project + seed the board
  salaryman tick <lane>    run one lane phase (intake|builder|critic|auditor)
  salaryman status         board summary
  salaryman inbox "<text>" add a raw prompt to INBOX (the backfill door)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from salaryman.board import Board          # noqa: E402
from salaryman.config import load_config   # noqa: E402

BOARD_SEED = """# BOARD — {name}

## 📥 INBOX

## 📋 TODO

## 🔨 DOING

## ✅ DONE
"""

YML_SEED = """# salaryman.yml — edit engine blocks here; workers migrate the code
project:
  name: {name}

stack:
  scaffold: next-tailwind-sqlite

engine:
  db: sqlite
  deploy: vercel

lanes:
  intake: every 30m
  builder: every 10m
  critic: every 15m
  auditor: every 3h

workers:
  driver: claude-code

verify:
  screenshots: true
  live_probe: true
  vision_judge: optional
"""


def cmd_init(args) -> int:
    target = Path(args.dir).resolve()
    if target.exists() and any(target.iterdir()):
        print(f"error: {target} exists and is not empty", file=sys.stderr)
        return 1
    target.mkdir(parents=True, exist_ok=True)
    cfg = load_config(target, cli_patches=args.patch or [])
    template = Path(__file__).resolve().parent.parent / "templates" / cfg["stack"]["scaffold"]
    if template.exists():
        shutil.copytree(template, target, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("TEMPLATE.md", "node_modules"))
        # render placeholders
        for f in target.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".tsx", ".ts", ".md", ".html"):
                txt = f.read_text(encoding="utf-8")
                if "{{PROJECT_NAME}}" in txt:
                    f.write_text(txt.replace("{{PROJECT_NAME}}", target.name), encoding="utf-8")
    else:
        print(f"warn: template '{cfg['stack']['scaffold']}' not found — config-only init", file=sys.stderr)
    if not (target / "salaryman.yml").exists():
        (target / "salaryman.yml").write_text(
            YML_SEED.format(name=target.name), encoding="utf-8")
    board = target / "BOARD.md"
    if not board.exists():
        board.write_text(BOARD_SEED.format(name=target.name), encoding="utf-8")
    cfg = load_config(target)
    print(f"✓ salaryman project '{cfg['project']['name']}' at {target}")
    print(f"  stack: {cfg['stack']['scaffold']} · db: {cfg['engine']['db']} · deploy: {cfg['engine']['deploy']}")
    print(f"  board: {board}")
    print("next: salaryman inbox \"build me ...\" then salaryman tick intake")
    return 0


def cmd_tick(args) -> int:
    d = Path.cwd()
    lane = args.lane
    if lane == "intake":
        from salaryman.lanes.intake import process_inbox
        created = process_inbox(d / "BOARD.md", d)
        for c in created:
            print(f"  + {c['id']} ({c['size']}) from:{c['from']} — {c['title']}")
        print(f"intake: {len(created)} card(s) created")
        return 0
    if lane == "builder":
        from salaryman.lanes.builder import builder_tick
        res = builder_tick(d)
        print(res)
        return 0 if res.get("ok") else 1
    if lane == "critic":
        from salaryman.lanes.critic import critic_tick
        res = critic_tick(d, live_urls=[args.url] if args.url else None)
        print(res)
        return 0
    if lane == "auditor":
        from salaryman.lanes.auditor import auditor_tick
        res = auditor_tick(d)
        print(res)
        return 0
    print(f"unknown lane: {lane}", file=sys.stderr)
    return 1


def cmd_status(_) -> int:
    cfg = load_config(Path.cwd())
    board = Board(Path.cwd() / cfg["project"]["board"]).load()
    print(f"{cfg['project']['name']} — {cfg['stack']['scaffold']} · db={cfg['engine']['db']} · deploy={cfg['engine']['deploy']}")
    for s in ("INBOX", "TODO", "DOING", "DONE"):
        cards = board.cards[s]
        ids = ", ".join(c.id for c in cards[:6]) or "—"
        print(f"  {s:6} {len(cards):3}  {ids}{' …' if len(cards) > 6 else ''}")
    return 0


def cmd_deploy(args) -> int:
    from salaryman.deploy import deploy
    res = deploy(Path.cwd(), prod=args.prod)
    if res["ok"]:
        print(f"🚀 live: {res.get('url', '(url in output above)')} ({res['secs']}s)")
        return 0
    print(f"deploy failed: {res.get('error')}", file=sys.stderr)
    return 1


def cmd_docs(args) -> int:
    from salaryman.features import backfill
    cfg = load_config(Path.cwd())
    written = backfill(Path.cwd() / cfg["project"]["board"],
                       Path.cwd() / "docs" / "features", force=args.force)
    for cid in written:
        print(f"  ~ docs/features/{cid.replace('/', '-')}.md")
    print(f"docs: {len(written)} file(s) written/updated")
    return 0


def cmd_inbox(args) -> int:
    cfg = load_config(Path.cwd())
    bp = Path.cwd() / cfg["project"]["board"]
    b = Board(bp).load()
    n = len(b.cards["INBOX"]) + 1
    card = b.add_inbox(f"p{n:03d}", args.text)
    b.save()
    print(f"✓ INBOX {card.id}: \"{args.text}\"")
    print("next: salaryman tick intake")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="salaryman")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("dir")
    p.add_argument("--patch", action="append", help="dotted.key=value config overrides"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("tick"); p.add_argument("lane", choices=["intake", "builder", "critic", "auditor"])
    p.add_argument("--url", help="live URL for critic probes"); p.set_defaults(fn=cmd_tick)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    p = sub.add_parser("inbox"); p.add_argument("text"); p.set_defaults(fn=cmd_inbox)
    p = sub.add_parser("docs"); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_docs)
    p = sub.add_parser("deploy")
    p.add_argument("--prod", action="store_true", help="production deploy (default preview)")
    p.set_defaults(fn=cmd_deploy)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except FileNotFoundError as e:
        print(f"error: {e} — run 'salaryman init' first?", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
