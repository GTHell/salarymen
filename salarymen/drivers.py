"""drivers/base.py + claude_code.py — harness-agnostic worker invocation.

A Driver turns a task brief into completed work in a target directory and
returns a result with artifacts. Salarymen never talk to a model API directly;
it always goes through a driver (claude-code, codex, pi, opencode, dsh).
"""
from __future__ import annotations

import abc
import json
import os
import subprocess
import time
from dataclasses import dataclass, field


@dataclass
class DriverResult:
    ok: bool
    duration_s: float
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    artifacts: dict = field(default_factory=dict)


class Driver(abc.ABC):
    name: str

    @abc.abstractmethod
    def run(self, brief: str, cwd: str, timeout_s: int = 1800) -> DriverResult:
        """Execute a self-contained task brief inside cwd."""


class ClaudeCodeDriver(Driver):
    name = "claude-code"

    def run(self, brief: str, cwd: str, timeout_s: int = 1800) -> DriverResult:
        cmd = ["claude", "-p", brief, "--output-format", "json"]
        t0 = time.time()
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout_s)
        dt = time.time() - t0
        result_json = {}
        try:
            result_json = json.loads(r.stdout)
        except json.JSONDecodeError:
            pass
        return DriverResult(
            ok=r.returncode == 0,
            duration_s=round(dt, 2),
            stdout=r.stdout[-4000:],
            stderr=r.stderr[-2000:],
            exit_code=r.returncode,
            artifacts={"session_id": result_json.get("session_id"),
                       "cost": result_json.get("total_cost_usd")},
        )


class PiDriver(Driver):
    name = "pi"

    def __init__(self, provider: str | None = None, model: str | None = None):
        env = os.environ
        self.provider = provider or env.get("SALARYMEN_PI_PROVIDER")
        self.model = model or env.get("SALARYMEN_PI_MODEL")

    def run(self, brief: str, cwd: str, timeout_s: int = 1800) -> DriverResult:
        cmd = ["pi", "--print", "--no-session"]
        if self.provider:
            cmd += ["--provider", self.provider]
        if self.model:
            cmd += ["--model", self.model]
        cmd.append(brief)
        t0 = time.time()
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout_s)
        dt = time.time() - t0
        return DriverResult(ok=r.returncode == 0 and "TASK_PASS" not in "",
                            duration_s=round(dt, 2),
                            stdout=r.stdout[-4000:], stderr=r.stderr[-2000:],
                            exit_code=r.returncode)


def get_driver(name: str) -> Driver:
    if name == "claude-code":
        return ClaudeCodeDriver()
    if name == "pi":
        return PiDriver()
    raise ValueError(f"unknown driver: {name} (known: claude-code, pi)")
