"""Builder tick tests — fake driver, deterministic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from salaryman.board import Board
from salaryman.lanes import builder as builder_mod
from salaryman.drivers import DriverResult


def _seed(tmp_path: Path):
    (tmp_path / "salaryman.yml").write_text(
        "project:\n  name: demo\n")
    bp = tmp_path / "BOARD.md"
    bp.write_text("""# BOARD

## 📥 INBOX

## 📋 TODO

- feat/thing (S) — do the thing
  from: p001
  accept: thing works

## 🔨 DOING

## ✅ DONE
""")


class PassDriver:
    name = "fake-pass"
    def run(self, brief, cwd, timeout_s=1800):
        assert "feat/thing" in brief and "thing works" in brief
        return DriverResult(ok=True, duration_s=1.0, stdout="...TASK_PASS")


class FailDriver:
    name = "fake-fail"
    def run(self, brief, cwd, timeout_s=1800):
        return DriverResult(ok=False, duration_s=2.0,
                            stderr="tests failed", exit_code=1)


def test_builder_success_moves_to_done(tmp_path):
    _seed(tmp_path)
    orig = builder_mod.get_driver
    builder_mod.get_driver = lambda n: PassDriver()
    try:
        res = builder_mod.builder_tick(tmp_path)
    finally:
        builder_mod.get_driver = orig
    assert res["ok"] and res["outcome"] == "done"
    b = Board(tmp_path / "BOARD.md").load()
    sec, c = b.find("feat/thing")
    assert sec == "DONE" and "evidence" in c.meta


def test_builder_failure_returns_to_todo(tmp_path):
    _seed(tmp_path)
    orig = builder_mod.get_driver
    builder_mod.get_driver = lambda n: FailDriver()
    try:
        res = builder_mod.builder_tick(tmp_path)
    finally:
        builder_mod.get_driver = orig
    assert not res["ok"]
    b = Board(tmp_path / "BOARD.md").load()
    sec, c = b.find("feat/thing")
    assert sec == "TODO" and "last_fail" in c.meta


def test_no_second_card_while_doing(tmp_path):
    _seed(tmp_path)
    bp = tmp_path / "BOARD.md"
    t = bp.read_text().replace("## 🔨 DOING\n", "## 🔨 DOING\n\n- other/x (S) — busy\n")
    bp.write_text(t)
    res = builder_mod.builder_tick(tmp_path)
    assert not res["ok"] and "DOING" in res["reason"]


def test_empty_board_skips(tmp_path):
    (tmp_path / "salaryman.yml").write_text("project:\n  name: demo\n")
    (tmp_path / "BOARD.md").write_text("# B\n\n## 📥 INBOX\n\n## 📋 TODO\n\n## 🔨 DOING\n\n## ✅ DONE\n")
    res = builder_mod.builder_tick(tmp_path)
    assert res["ok"] and res.get("skipped") == "board empty"


if __name__ == "__main__":
    import tempfile
    fails = 0
    for fn in [test_builder_success_moves_to_done,
               test_builder_failure_returns_to_todo,
               test_no_second_card_while_doing, test_empty_board_skips]:
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
