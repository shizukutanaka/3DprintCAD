"""Tests for the CLI entry point behavior."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import hashlib
import json

import pytest

from src import cli_main as cli
from src.core.config import ApplicationConfig, Config, ValidationConfig


class _DummyLogger:
    def set_context(self, context):
        self._context = context

    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def critical(self, *args, **kwargs):
        pass


@pytest.fixture(autouse=True)
def stub_logging(monkeypatch):
    """Ensure logging setup does not touch the real environment."""
    monkeypatch.setattr(cli, "configure_logging", lambda *a, **k: None)
    monkeypatch.setattr(cli, "get_logger", lambda *a, **k: _DummyLogger())











def test_main_rejects_missing_output_directory(tmp_path, capsys):
    """Output paths must target existing directories."""
    missing_dir = tmp_path / "missing" / "report.json"

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--output", str(missing_dir)])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "Directory for --output does not exist" in captured.err




def test_main_rejects_non_nfc_string(capsys):
    """Arguments must be NFC-normalized to prevent mixed-encoding payloads."""

    # "Å" decomposed as "A" + combining ring
    decomposed = "A\u030A-model.stl"

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--pattern", decomposed])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "NFC-normalized" in captured.err


def test_main_requires_hash_manifest_in_warn_mode_when_config_enforces(monkeypatch, capsys):
    """Configuration enforcement must override CLI hash policy selections."""

    config = Config(
        application=ApplicationConfig(enforce_hash_manifest=True),
        validation=ValidationConfig(),
    )

    monkeypatch.setattr("src.core.config.get_config", lambda: config)

    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "model.stl",
            "--hash-policy",
            "warn",
        ])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "requires strict hash manifest enforcement" in captured.err





def test_main_rejects_parent_traversal(tmp_path, capsys):
    """CLI should refuse parent-directory traversal attempts."""
    unsafe_path = tmp_path / ".." / "escape.stl"

    with pytest.raises(SystemExit) as excinfo:
        cli.main([str(unsafe_path)])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "Parent directory traversal" in captured.err


def test_main_rejects_symlink_inputs(tmp_path, capsys):
    """Symbolic link inputs are blocked to prevent path spoofing."""
    target = tmp_path / "real.stl"
    target.write_text("stub", encoding="utf-8")
    symlink_path = tmp_path / "link.stl"
    symlink_path.symlink_to(target)

    with pytest.raises(SystemExit) as excinfo:
        cli.main([str(symlink_path)])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "Symbolic links are not permitted" in captured.err



def test_main_pattern_rejects_traversal(capsys):
    """Traversal tokens in --pattern should be rejected."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--pattern", "../*.stl", "--input-dir", "models"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "Parent directory traversal detected in pattern" in captured.err



def test_main_min_wall_bounds_enforced(capsys):
    """Invalid wall thickness thresholds should be rejected."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--min-wall", "0.0001"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--min-wall must be between" in captured.err


def test_main_overhang_angle_bounds_enforced(capsys):
    """Overhang angle outside bounds should cause a parse error."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--overhang-angle", "90"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--overhang-angle must be" in captured.err



def test_main_output_must_be_json(tmp_path, capsys):
    """Non-JSON output formats should be rejected for consistency."""
    bad_output = tmp_path / "report.txt"

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--output", str(bad_output)])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--output must point to a .json file" in captured.err




