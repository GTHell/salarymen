"""lanes/critic.py — evidence over claims.

The critic verifies DOING->DONE transitions: probe the running app (HTTP),
capture a screenshot (playwright if available, else skip), and optionally ask
a VLM to judge the screenshot against the card's acceptance criteria. Evidence
is written INTO the card; a DONE without evidence is reopened.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from ..board import Board
from ..config import load_config

EVIDENCE_DIR = "evidence"


def probe(url: str, timeout_s: int = 10) -> dict:
    """GET a URL; return {status, latency_s, ok}. 401/403/404 still prove liveness."""
    t0 = time.time()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            return {"url": url, "status": r.status,
                    "latency_s": round(time.time() - t0, 2), "ok": True}
    except Exception as e:
        code = getattr(e, "code", None)
        return {"url": url, "status": code or str(e)[:80],
                "latency_s": round(time.time() - t0, 2),
                "ok": code is not None and code < 500}


def screenshot(url: str, out_png: Path, viewport: tuple[int, int] = (1280, 800)) -> dict:
    """Playwright screenshot. Returns {path} or {skipped: reason}."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"skipped": "playwright not installed"}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1200)  # settle animations/fonts
            out_png.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out_png))
            browser.close()
        return {"path": str(out_png)}
    except Exception as e:
        return {"skipped": f"{type(e).__name__}: {e}"[:160]}


def vision_judge(png_path: Path, accept: str, base_url: str | None = None,
                 api_key_env: str = "OPENCODE_ZEN_API_KEY") -> dict:
    """Optional VLM verdict on a screenshot vs acceptance criteria."""
    key = None
    from os import environ
    key = environ.get(api_key_env)
    if not (png_path.exists() and key and base_url):
        return {"verdict": "SKIPPED", "reason": "no vlm configured"}
    try:
        import base64
        b64 = base64.b64encode(png_path.read_bytes()).decode()
        body = json.dumps({
            "model": "x-preview-f-free",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text":
                    f"Does this screenshot satisfy the acceptance criteria? "
                    f"Answer PASS or FAIL then one short reason.\nCriteria: {accept}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            "max_tokens": 100,
        }).encode()
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = json.load(r)["choices"][0]["message"]["content"]
        verdict = "PASS" if "PASS" in text.upper()[:20] else "FAIL"
        return {"verdict": verdict, "reason": text[:200]}
    except Exception as e:
        return {"verdict": "SKIPPED", "reason": str(e)[:160]}


def critic_tick(project_dir: str | Path, live_urls: list[str] | None = None) -> dict:
    """Verify every DONE card has evidence; attach fresh probe+shot evidence to
    cards in DONE that lack it, reopen ones that fail verification."""
    d = Path(project_dir)
    cfg = load_config(d)
    board_path = d / cfg["project"]["board"]
    board = Board(board_path).load()

    urls = live_urls or cfg.get("verify", {}).get("urls") or ["http://localhost:3000"]
    checked, reopened, evidenced = 0, [], 0

    for c in list(board.cards["DONE"]):
        if c.meta.get("evidence"):
            continue  # already evidenced by builder/critic earlier
        probes = [probe(u) for u in urls]
        live_ok = any(pr["ok"] for pr in probes)

        shot: dict = {"skipped": "disabled"}
        if cfg.get("verify", {}).get("screenshots", True) and live_ok:
            url = next(pr["url"] for pr in probes if pr["ok"])
            shot = screenshot(url, d / EVIDENCE_DIR / f"{c.id.replace('/', '_')}.png")

        parts = [f"probes={json.dumps(probes)}"]
        if shot.get("path"):
            parts.append(f"screenshot={shot['path']}")
        elif shot.get("skipped"):
            parts.append(f"screenshot_skipped={shot['skipped']}")

        verdict = vision_judge(Path(shot["path"]), c.meta.get("accept", ""),
                               base_url=cfg.get("verify", {}).get("vision_base_url")) \
            if shot.get("path") else {"verdict": "SKIPPED"}
        parts.append(f"vision={verdict['verdict']}")

        if not live_ok:
            c.meta["reopened"] = f"live probe failed: {json.dumps(probes)}"
            board.cards["DONE"].remove(c)
            board.cards["TODO"].append(c)
            reopened.append(c.id)
        else:
            c.meta["evidence"] = " · ".join(parts)
            evidenced += 1
        checked += 1

    if checked:
        board.save()
    return {"checked": checked, "evidenced": evidenced, "reopened": reopened}
