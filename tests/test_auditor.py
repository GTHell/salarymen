"""Auditor tests — git repo fixtures, deterministic."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from salaryman.board import Board
from salaryman.lanes.auditor import auditor_tick

GIT_CFG = ["-c", "user.name=t", "-c", "user.email=t@t"]


def _git(d: Path, *args):
    subprocess.run(["git", *GIT_CFG, *args], cwd=d, capture_output=True, check=True)


def _init_repo(tmp_path: Path, board_text: str, commits: list[str]):
    _git(tmp_path, "init", "-q")
    bp = tmp_path / "BOARD.md"
    bp.write_text(board_text)
    (tmp_path / "f.txt").write_text("x")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "seed")
    for msg in commits:
        (tmp_path / "f.txt").write_text(msg)
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-qm", msg)


def test_reopens_done_without_evidence(tmp_path):
    board = """# B

## 📥 INBOX

## 📋 TODO

## 🔨 DOING

## ✅ DONE

- feat/no-proof — claimed without proof
"""
    _init_repo(tmp_path, board, [])
    res = auditor_tick(tmp_path)
    assert "feat/no-proof" in res["reopened"]
    b = Board(tmp_path / "BOARD.md").load()
    sec, c = b.find("feat/no-proof")
    assert sec == "TODO" and "without evidence" in c.meta.get("reopened", "")


def test_flags_doing_without_worker(tmp_path):
    board = """# B

## 📥 INBOX

## 📋 TODO

## 🔨 DOING

- feat/ghost — no worker claim

## ✅ DONE
"""
    _init_repo(tmp_path, board, [])
    res = auditor_tick(tmp_path)
    assert any("feat/ghost" in f for f in res["flagged"])
    b = Board(tmp_path / "BOARD.md").load()
    sec, _ = b.find("feat/ghost")
    assert sec == "TODO"


def test_commits_for_todo_flagged(tmp_path):
    board = """# B

## 📥 INBOX

## 📋 TODO

- feat/discount — not started (allegedly)

## 🔨 DOING

## ✅ DONE
"""
    _init_repo(tmp_path, board, ["feat/discount: implement codes"])
    res = auditor_tick(tmp_path)
    assert any("feat/discount" in f for f in res["flagged"])


def test_done_with_commit_and_evidence_clean(tmp_path):
    board = """# B

## 📥 INBOX

## 📋 TODO

## 🔨 DOING

## ✅ DONE

- feat/auth — sign-in flow
  evidence: screenshots/auth.png · probe 200
"""
    _init_repo(tmp_path, board, ["feat/auth: implement login"])
    res = auditor_tick(tmp_path)
    assert not res["reopened"]
    assert not [f for f in res["flagged"] if "feat/auth" in f]


if __name__ == "__main__":
    import tempfile
    fails = 0
    for fn in [test_reopens_done_without_evidence,
               test_flags_doing_without_worker,
               test_commits_for_todo_flagged,
               test_done_with_commit_and_evidence_clean]:
        with tempfile.TemporaryDirectory() as td:
            try:
                fn(Path(td))
                print(f"PASS {fn.__name__}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {fn.__name__}: {e}")
            except Exception as e:
                fails += 1
                print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    raise SystemExit(1 if fails else 0)
