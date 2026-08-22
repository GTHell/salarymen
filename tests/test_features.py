"""Feature-docs backfill tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from salarymen.board import Board
from salarymen.features import backfill


def test_backfill_generates_docs(tmp_path):
    bp = tmp_path / "BOARD.md"
    bp.write_text("""# B

## 📥 INBOX

- p001 [raw] "add auth"

## 📋 TODO

- feat/pending — not started
  from: p001

## 🔨 DOING

## ✅ DONE

- feat/auth — sign-in flow
  evidence: shots/auth.png · probe 200
""")
    out = tmp_path / "docs" / "features"
    written = backfill(bp, out)
    assert set(written) == {"feat/pending", "feat/auth"}
    doc = (out / "feat-auth.md").read_text()
    assert "# feat/auth" in doc and "sign-in flow" in doc
    assert "shots/auth.png" in doc          # evidence included
    assert '"add auth"' in (out / "feat-pending.md").read_text() or \
           "add auth" in (out / "feat-pending.md").read_text()


def test_backfill_idempotent(tmp_path):
    bp = tmp_path / "BOARD.md"
    bp.write_text("""# B

## 📥 INBOX

## 📋 TODO

## 🔨 DOING

## ✅ DONE

- feat/x — thing
  evidence: e1
""")
    out = tmp_path / "docs" / "features"
    assert len(backfill(bp, out)) == 1
    assert backfill(bp, out) == []  # unchanged -> no rewrite


if __name__ == "__main__":
    import tempfile
    fails = 0
    for fn in [test_backfill_generates_docs, test_backfill_idempotent]:
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
