"""Intake lane tests — with a FAKE driver (no LLM, deterministic)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from salarymen.board import Board
from salarymen.lanes import intake as intake_mod
from salarymen.drivers import DriverResult


FAKE_RESPONSE = '{"cards": [' \
    '{"id": "feat/discount-codes", "size": "M", "title": "discount codes", "accept": "applies at checkout"},' \
    '{"id": "perf/shop", "size": "S", "title": "lazy images", "accept": "LCP < 2.5s"},' \
    '{"id": "Bad Id!!", "size": "S", "title": "weird id gets slugified", "accept": "works"}' \
    ']}'


class FakeDriver:
    name = "fake"
    def run(self, brief, cwd, timeout_s=300):
        return DriverResult(ok=True, duration_s=0.1, stdout=FAKE_RESPONSE)


def _seed(board_path: Path):
    board_path.write_text("""# BOARD

## 📥 INBOX

- p001 [raw] "make my shop better and faster"

## 📋 TODO

## 🔨 DOING

## ✅ DONE
""")


def test_intake_creates_cards(tmp_path):
    bp = tmp_path / "BOARD.md"
    _seed(bp)
    orig = intake_mod.get_driver
    intake_mod.get_driver = lambda n: FakeDriver()
    try:
        created = intake_mod.process_inbox(bp, tmp_path)
    finally:
        intake_mod.get_driver = orig
    assert len(created) == 3
    b = Board(bp).load()
    ids = [c.id for c in b.cards["TODO"]]
    assert "feat/discount-codes" in ids and "perf/shop" in ids
    for c in b.cards["TODO"]:
        assert c.meta["from"] == "p001"
        assert c.meta["accept"]


def test_intake_no_double_process(tmp_path):
    bp = tmp_path / "BOARD.md"
    _seed(bp)
    orig = intake_mod.get_driver
    intake_mod.get_driver = lambda n: FakeDriver()
    try:
        intake_mod.process_inbox(bp, tmp_path)
        created2 = intake_mod.process_inbox(bp, tmp_path)
    finally:
        intake_mod.get_driver = orig
    assert created2 == [], "same receipt must not decompose twice"


if __name__ == "__main__":
    import tempfile
    fails = 0
    for fn in [test_intake_creates_cards, test_intake_no_double_process]:
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
