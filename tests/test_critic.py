"""Critic tests — local HTTP server, no playwright, deterministic."""
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from salarymen.board import Board
from salarymen.lanes import critic as critic_mod


def _serve():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>ok</body></html>")
        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_port}/"


def _seed(tmp_path: Path, with_evidence=False):
    (tmp_path / "salaryman.yml").write_text(
        "project:\n  name: demo\nverify:\n  screenshots: false\n")
    bp = tmp_path / "BOARD.md"
    ev = "\n  evidence: driver=fake 1s" if with_evidence else ""
    bp.write_text(f"""# BOARD

## 📥 INBOX

## 📋 TODO

## 🔨 DOING

## ✅ DONE

- feat/live-page — serve a page{ev}
""")


def _seed_no_evidence(tmp_path: Path):
    (tmp_path / "salaryman.yml").write_text(
        "project:\n  name: demo\nverify:\n  screenshots: false\n")
    bp = tmp_path / "BOARD.md"
    bp.write_text("""# BOARD

## 📥 INBOX

## 📋 TODO

## 🔨 DOING

## ✅ DONE

- feat/unevidenced — claimed but no proof
""")


def test_probe_ok():
    srv, url = _serve()
    try:
        r = critic_mod.probe(url)
        assert r["ok"] and r["status"] == 200
    finally:
        srv.shutdown()


def test_probe_down_is_not_ok_but_detected():
    # port 1 on localhost = nothing listening
    r = critic_mod.probe("http://127.0.0.1:1/", timeout_s=2)
    assert r["ok"] is False


def test_critic_attaches_probe_evidence(tmp_path):
    srv, url = _serve()
    try:
        _seed(tmp_path)  # no evidence -> critic must attach probe evidence
        res = critic_mod.critic_tick(tmp_path, live_urls=[url])
    finally:
        srv.shutdown()
    assert res["checked"] == 1 and res["evidenced"] == 1 and not res["reopened"]
    b = Board(tmp_path / "BOARD.md").load()
    _, c = b.find("feat/live-page")
    assert "probes=" in c.meta["evidence"]


def test_critic_reopens_dead_url(tmp_path):
    _seed_no_evidence(tmp_path)
    res = critic_mod.critic_tick(tmp_path, live_urls=["http://127.0.0.1:1/"])
    assert res["reopened"] == ["feat/unevidenced"]
    b = Board(tmp_path / "BOARD.md").load()
    sec, c = b.find("feat/unevidenced")
    assert sec == "TODO" and "live probe failed" in c.meta.get("reopened", "")


def test_critic_skips_already_evidenced(tmp_path):
    srv, url = _serve()
    try:
        _seed(tmp_path, with_evidence=True)  # already evidenced by builder
        before = (tmp_path / "BOARD.md").read_text()
        res = critic_mod.critic_tick(tmp_path, live_urls=[url])
        after = (tmp_path / "BOARD.md").read_text()
    finally:
        srv.shutdown()
    assert res["checked"] == 0 and before == after


if __name__ == "__main__":
    import tempfile
    import inspect
    fails = 0
    for fn in [test_probe_ok, test_probe_down_is_not_ok_but_detected,
               test_critic_attaches_probe_evidence, test_critic_reopens_dead_url,
               test_critic_skips_already_evidenced]:
        with tempfile.TemporaryDirectory() as td:
            try:
                if len(inspect.signature(fn).parameters):
                    fn(Path(td))
                else:
                    fn()
                print(f"PASS {fn.__name__}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {fn.__name__}: {e}")
            except Exception as e:
                fails += 1
                print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    raise SystemExit(1 if fails else 0)
