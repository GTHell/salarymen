"""Roundtrip + mutation tests for board.py — the kanban is data, prove it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from salarymen.board import Board

SAMPLE = """# BOARD — demo project

## 📥 INBOX

- p001 [raw] "make the shop page faster"

- p002 [raw] "add discount codes"

## 📋 TODO

- feat/discount-codes (M) — codes with %/fixed, expiry
  from: p002
  accept: code applies at checkout; expired rejected

## 🔨 DOING

- perf/shop-page (S) — lazy-load product images
  branch: worker/perf-shop-page

## ✅ DONE

- feat/auth — google sign-in flow
  evidence: screenshots/auth-flow.png · probe /api/me → 200 · vision: PASS
"""


def test_roundtrip_identical(tmp_path):
    p = tmp_path / "BOARD.md"
    p.write_text(SAMPLE)
    b = Board(p).load()
    assert b.render() == SAMPLE, "roundtrip must be byte-identical"


def test_parse_cards(tmp_path):
    p = tmp_path / "BOARD.md"
    p.write_text(SAMPLE)
    b = Board(p).load()
    assert len(b.cards["INBOX"]) == 2
    assert b.cards["INBOX"][0].raw_text == "make the shop page faster"
    todo = b.cards["TODO"][0]
    assert todo.id == "feat/discount-codes" and todo.size == "M"
    assert todo.meta["from"] == "p002"
    done = b.cards["DONE"][0]
    assert done.id == "feat/auth"
    assert "auth-flow.png" in done.meta["evidence"]


def test_move_card(tmp_path):
    p = tmp_path / "BOARD.md"
    p.write_text(SAMPLE)
    b = Board(p).load()
    c = b.move("perf/shop-page", "DONE", evidence="shot.png · probe 200")
    assert c.meta["evidence"] == "shot.png · probe 200"
    ids = [x.id for x in b.cards["DONE"]]
    assert "perf/shop-page" in ids and "feat/auth" in ids


def test_evidence_gate(tmp_path):
    p = tmp_path / "BOARD.md"
    p.write_text(SAMPLE)
    b = Board(p).load()
    assert b.evidence_ok("feat/auth") is True       # has evidence
    assert b.evidence_ok("feat/discount-codes") is False  # TODO: none


def test_add_inbox_and_save(tmp_path):
    p = tmp_path / "BOARD.md"
    p.write_text(SAMPLE)
    b = Board(p).load()
    b.add_inbox("p003", "add a dark mode toggle")
    b.save()
    b2 = Board(p).load()
    assert b2.cards["INBOX"][-1].raw_text == "add a dark mode toggle"
    # and the whole thing still roundtrips after reload+render
    assert b2.render() == p.read_text()


def test_missing_card_raises(tmp_path):
    p = tmp_path / "BOARD.md"
    p.write_text(SAMPLE)
    b = Board(p).load()
    try:
        b.move("nope/nope", "DONE")
        assert False, "should raise KeyError"
    except KeyError:
        pass


if __name__ == "__main__":
    import tempfile
    fails = 0
    for fn in [test_roundtrip_identical, test_parse_cards, test_move_card,
               test_evidence_gate, test_add_inbox_and_save, test_missing_card_raises]:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            try:
                fn(td_path)
                print(f"PASS {fn.__name__}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {fn.__name__}: {e}")
            except Exception as e:
                fails += 1
                print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    raise SystemExit(1 if fails else 0)
