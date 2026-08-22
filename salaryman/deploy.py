"""deploy.py — send it live.

v0.1: Vercel via the vercel CLI (token from VERCEL_TOKEN env or ~/.vercel).
Design: deploy is a lane, not a build step — workers never push to prod
directly; humans (or a cron with approval) run `salaryman deploy`.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


def _vercel_cli() -> str | None:
    for name in ("vercel",):
        if shutil.which(name):
            return name
    return None


def deploy(project_dir: str | Path, prod: bool = False,
           token_env: str = "VERCEL_TOKEN") -> dict:
    """Deploy the built app. Returns {ok, url?} or {ok: False, error}."""
    d = Path(project_dir)
    cli = _vercel_cli()
    if not cli:
        return {"ok": False, "error": "vercel CLI not found — npm i -g vercel"}
    cmd = [cli, "deploy", "--yes"]
    if prod:
        cmd.append("--prod")
    import os
    token = os.environ.get(token_env)
    if token:
        cmd += ["--token", token]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=d, capture_output=True, text=True,
                           timeout=600)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "deploy timed out after 600s"}
    dt = round(time.time() - t0, 1)
    if r.returncode != 0:
        return {"ok": False, "error": (r.stderr or r.stdout)[-400:], "secs": dt}
    url = ""
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("https://"):
            url = line
    return {"ok": True, "url": url, "secs": dt}
