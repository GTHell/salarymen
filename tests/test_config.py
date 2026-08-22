"""Tests for config.py layered composition."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from salarymen.config import load_config, validate, ConfigError, DEFAULTS


def test_defaults_only(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg["engine"]["db"] == "sqlite"
    assert cfg["workers"]["driver"] == "claude-code"


def test_project_layer_overrides(tmp_path):
    (tmp_path / "salaryman.yml").write_text(
        "project:\n  name: my-shop\nengine:\n  db: postgres\n")
    cfg = load_config(tmp_path)
    assert cfg["project"]["name"] == "my-shop"
    assert cfg["engine"]["db"] == "postgres"
    assert cfg["engine"]["deploy"] == "vercel"  # untouched default survives


def test_local_layer_wins(tmp_path):
    (tmp_path / "salaryman.yml").write_text("engine:\n  db: postgres\n")
    (tmp_path / "salaryman.local.yml").write_text("engine:\n  db: turso\n")
    cfg = load_config(tmp_path)
    assert cfg["engine"]["db"] == "turso"


def test_cli_patch_beats_all(tmp_path):
    (tmp_path / "salaryman.local.yml").write_text("engine:\n  db: turso\n")
    cfg = load_config(tmp_path, cli_patches=["engine.db=postgres"])
    assert cfg["engine"]["db"] == "postgres"


def test_patch_type_inference(tmp_path):
    cfg = load_config(tmp_path, cli_patches=["verify.screenshots=false", "lanes.builder=every 5m"])
    assert cfg["verify"]["screenshots"] is False
    assert cfg["lanes"]["builder"] == "every 5m"


def test_invalid_db_rejected(tmp_path):
    try:
        load_config(tmp_path, cli_patches=["engine.db=oracle"])
        assert False, "should raise"
    except ConfigError as e:
        assert "oracle" in str(e)


def test_missing_name_rejected(tmp_path):
    try:
        validate({**DEFAULTS, "project": {}})
        assert False, "should raise"
    except ConfigError as e:
        assert "name" in str(e)


if __name__ == "__main__":
    import tempfile
    fails = 0
    for fn in [test_defaults_only, test_project_layer_overrides, test_local_layer_wins,
               test_cli_patch_beats_all, test_patch_type_inference,
               test_invalid_db_rejected, test_missing_name_rejected]:
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
