"""config.py — salaryman.yml layered composition.

Merge order (later wins per key):
    DEFAULTS  ->  salaryman.yml  ->  salaryman.local.yml  ->  CLI patches

This is the dsh/Cordis lesson: engine blocks (db, auth, deploy) are config
rows, not code. Swapping sqlite->postgres is an edit here + a migration lane,
never a refactor.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise SystemExit("salaryman requires PyYAML: pip install pyyaml") from e


DEFAULTS: dict = {
    "project": {"board": "BOARD.md"},
    "stack": {"scaffold": "next-tailwind-sqlite"},
    "engine": {"db": "sqlite", "deploy": "vercel"},
    "lanes": {
        "intake": "every 30m",
        "builder": "every 10m",
        "critic": "every 15m",
        "auditor": "every 3h",
    },
    "workers": {"driver": "claude-code"},
    "verify": {"screenshots": True, "live_probe": True, "vision_judge": "optional"},
}

_VALID_DB = {"sqlite", "postgres", "mysql", "turso"}
_VALID_DEPLOY = {"vercel", "cloudflare", "docker", "self-host"}
_VALID_DRIVERS = {"claude-code", "codex", "pi", "opencode", "dsh"}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (new dict). Lists/scalars replace."""
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


class ConfigError(ValueError):
    pass


def validate(cfg: dict) -> None:
    db = cfg.get("engine", {}).get("db")
    if db and db not in _VALID_DB:
        raise ConfigError(f"engine.db '{db}' not in {sorted(_VALID_DB)}")
    dep = cfg.get("engine", {}).get("deploy")
    if dep and dep not in _VALID_DEPLOY:
        raise ConfigError(f"engine.deploy '{dep}' not in {sorted(_VALID_DEPLOY)}")
    drv = cfg.get("workers", {}).get("driver")
    if drv and drv not in _VALID_DRIVERS:
        raise ConfigError(f"workers.driver '{drv}' not in {sorted(_VALID_DRIVERS)}")
    if not str(cfg.get("project", {}).get("name", "")).strip():
        raise ConfigError("project.name is required")


def load_config(
    project_dir: str | Path,
    cli_patches: list[str] | None = None,
) -> dict:
    """Load + merge + validate. CLI patches are 'dotted.key=value' strings."""
    d = Path(project_dir)
    cfg = copy.deepcopy(DEFAULTS)
    for name in ("salaryman.yml", "salaryman.local.yml"):
        f = d / name
        if f.exists():
            layer = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            if not isinstance(layer, dict):
                raise ConfigError(f"{name}: top level must be a mapping")
            cfg = _deep_merge(cfg, layer)
    for patch in cli_patches or []:
        cfg = _deep_merge(cfg, _parse_patch(patch))
    if not str(cfg.get("project", {}).get("name", "")).strip():
        cfg.setdefault("project", {})["name"] = d.resolve().name
    validate(cfg)
    return cfg


def _parse_patch(patch: str) -> dict:
    """'engine.db=postgres' -> {'engine': {'db': 'postgres'}}. Value typed."""
    m = re.fullmatch(r"([A-Za-z0-9_.]+)=(.*)", patch.strip())
    if not m:
        raise ConfigError(f"bad patch (want key=value): {patch!r}")
    key, raw = m.group(1), m.group(2).strip()
    # type inference: yaml-safe scalars only
    if raw.lower() in ("true", "false"):
        val: object = raw.lower() == "true"
    elif re.fullmatch(r"-?\d+", raw):
        val = int(raw)
    else:
        val = raw
    root: dict = {}
    node = root
    parts = key.split(".")
    for part in parts[:-1]:
        node[part] = {}
        node = node[part]
    node[parts[-1]] = val
    return root
