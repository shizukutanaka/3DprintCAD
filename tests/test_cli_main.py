"""Tests for the CLI entry point behavior."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import hashlib
import json

import pytest

from src import cli
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


def test_main_list_files_outputs_sorted(monkeypatch, capsys):
    """`--list-files` should print discovered meshes in sorted order."""
    monkeypatch.setattr(
        cli,
        "find_mesh_files",
        lambda args: ([Path("b_model.stl"), Path("a_model.stl")], []),
    )

    exit_code = cli.main(["dummy.stl", "--list-files"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines() == ["a_model.stl", "b_model.stl"]
    assert captured.err == ""


def test_main_list_files_reports_when_empty(monkeypatch, capsys):
    """Empty results should emit a friendly notice and exit 0."""
    monkeypatch.setattr(cli, "find_mesh_files", lambda args: ([], ["Path not found: missing.stl"]))

    exit_code = cli.main(["dummy.stl", "--list-files"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines() == [
        "No mesh files found.",
        "Hint: Path not found: missing.stl",
    ]
    assert captured.err == ""


def test_main_list_files_respects_no_progress(monkeypatch, capsys):
    """`--no-progress` suppresses the empty notice for scripting scenarios."""
    monkeypatch.setattr(cli, "find_mesh_files", lambda args: [])

    exit_code = cli.main(["dummy.stl", "--list-files", "--no-progress"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""


def test_main_list_formats_outputs_supported_extensions(capsys):
    """`--list-formats` should print supported extensions sorted ascending."""
    exit_code = cli.main(["--list-formats"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines() == sorted(cli.MESH_FILE_EXTENSIONS)
    assert captured.err == ""


def test_main_list_formats_short_circuits(monkeypatch):
    """When listing formats, no file discovery or logging should be invoked."""
    sentinel = object()

    def fail_find_mesh_files(args):  # pragma: no cover - protection only
        raise AssertionError("find_mesh_files should not be called")

    monkeypatch.setattr(cli, "find_mesh_files", fail_find_mesh_files)
    monkeypatch.setattr(cli, "configure_logging", lambda *a, **k: sentinel)

    exit_code = cli.main(["--list-formats"])

    assert exit_code == 0


def test_main_warns_on_unsupported_extension(monkeypatch, capsys):
    """Unsupported formats should emit a warning and respect progress output."""
    monkeypatch.setattr(cli, "find_mesh_files", lambda args: ([Path("model.xyz")], []))
    monkeypatch.setattr(cli, "get_logger", lambda name: _DummyLogger())

    exit_code = cli.main(["model.xyz"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Unsupported mesh extensions detected" in captured.out
    assert "対応していないメッシュ拡張子" in captured.out


def test_main_warns_quietly_with_no_progress(monkeypatch, capsys):
    """When --no-progress is used, warning should not print to stdout."""
    monkeypatch.setattr(cli, "find_mesh_files", lambda args: [Path("model.xyz")])
    monkeypatch.setattr(cli, "get_logger", lambda name: _DummyLogger())

    exit_code = cli.main(["model.xyz", "--no-progress"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""


def test_main_rejects_parallel_without_batch(capsys):
    """`--parallel` must only be used together with `--batch`."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--parallel"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--parallel requires --batch" in captured.err


def test_main_rejects_save_repaired_without_repair(capsys):
    """`--save-repaired` should enforce the presence of `--repair`."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--save-repaired", "repaired.stl"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--save-repaired requires --repair" in captured.err


def test_main_rejects_missing_output_directory(tmp_path, capsys):
    """Output paths must target existing directories."""
    missing_dir = tmp_path / "missing" / "report.json"

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--output", str(missing_dir)])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "Directory for --output does not exist" in captured.err


def test_main_enforces_safe_worker_limits(capsys):
    """Excessive worker counts should be rejected proactively."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "--batch",
            "--parallel",
            "--pattern",
            "*.stl",
            "--max-workers",
            "256",
        ])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--max-workers exceeds supported limit" in captured.err


def test_main_enforces_cpu_limit(monkeypatch, capsys):
    """The dynamic CPU-based limit should also guard against oversized worker pools."""
    monkeypatch.setattr("os.cpu_count", lambda: 1)

    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "--batch",
            "--parallel",
            "--pattern",
            "*.stl",
            "--max-workers",
            "8",
        ])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--max-workers exceeds supported limit" in captured.err


@pytest.mark.parametrize(
    "argument,label,bad_value",
    [
        ("--pattern", "pattern", "\u0000unsafe"),
        ("--output", "output", "dir/\u0000file.json"),
        ("--language", "language", "\ud800"),
    ],
)
def test_main_rejects_invalid_unicode_arguments(argument, label, bad_value, capsys):
    """CLI should exit with an error when arguments contain disallowed Unicode content."""

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", argument, bad_value])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert f"{label} contains disallowed Unicode characters" in captured.err


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

    monkeypatch.setattr(cli.cli_optimized, "get_config", lambda: config)
    monkeypatch.setattr(cli, "CLIProcessor", cli.cli_optimized.CLIProcessor)

    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "model.stl",
            "--batch",
            "--hash-policy",
            "warn",
        ])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "requires strict hash manifest enforcement" in captured.err


def test_main_warn_policy_allows_processing(monkeypatch, tmp_path, capsys):
    """When --hash-policy warn is used, mismatched entries should be surfaced as warnings, not hard failures."""

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"files": {"model.stl": "deadbeef"}}), encoding="utf-8")

    file_path = tmp_path / "model.stl"
    file_path.write_bytes(b"triangle")

    config = Config()

    def _get_config():
        return config

    class _Processor(cli.cli_optimized.CLIProcessor):
        def __init__(self):
            monkeypatch.setattr(cli.cli_optimized, "get_config", _get_config)
            super().__init__()

    monkeypatch.setattr(cli.cli_optimized, "CLIProcessor", _Processor)
    monkeypatch.setattr(cli, "CLIProcessor", _Processor)
    monkeypatch.setattr(cli, "find_mesh_files", lambda args: ([file_path], []))
    monkeypatch.setattr(cli.cli_optimized, "load_mesh", lambda path: SimpleNamespace(vertices=[], faces=[], bounds=None))
    monkeypatch.setattr(cli.cli_optimized, "mesh_validator", SimpleNamespace(validate_mesh=lambda *a, **k: SimpleNamespace(success=True, issues=[], as_dict=lambda: {})))
    monkeypatch.setattr(cli.cli_optimized, "repair_mesh", lambda *a, **k: (None, SimpleNamespace(operations_performed=[], issues_fixed=[], remaining_issues=[], repair_success=False)))
    monkeypatch.setattr(cli.cli_optimized, "SlicingEngine", lambda *a, **k: SimpleNamespace(slice_mesh=lambda mesh: SimpleNamespace(total_layers=0, total_print_time_seconds=0, total_material_grams=0)))
    monkeypatch.setattr(cli.cli_optimized, "GcodeGenerator", lambda *a, **k: SimpleNamespace(generate=lambda result: ""))
    monkeypatch.setattr(cli.cli_optimized, "RecommendationEngine", lambda: SimpleNamespace(generate_recommendations=lambda v: SimpleNamespace(to_dict=lambda: {})))
    monkeypatch.setattr(cli.cli_optimized, "evaluate_print_readiness", lambda *a, **k: None)

    exit_code = cli.main([
        str(file_path),
        "--hash-manifest",
        str(manifest_path),
        "--hash-policy",
        "warn",
        "--no-progress",
    ])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "HASH_MANIFEST" in captured.out


def test_main_batch_requires_sources(capsys):
    """`--batch` must be paired with multiple inputs, patterns, or directories."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--batch"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--batch requires multiple mesh paths" in captured.err


def test_main_rejects_oversized_mesh(tmp_path, capsys, monkeypatch):
    """Files exceeding the configured threshold should be rejected before processing."""
    big_file = tmp_path / "big_model.stl"
    big_file.write_bytes(b"0" * (5 * 1024 * 1024))

    test_config = Config(
        application=ApplicationConfig(max_file_size_mb=1),
        validation=ValidationConfig(),
        printer_profiles={},
        active_printer=None,
    )
    monkeypatch.setattr(cli.cli_processor, "get_config", lambda: test_config)

    with pytest.raises(SystemExit) as excinfo:
        cli.main([str(big_file)])

    captured = capsys.readouterr()

    assert excinfo.value.code == 1
    assert "Mesh file exceeds maximum configured size" in captured.out or captured.err


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


def test_main_pattern_requires_batch(capsys):
    """`--pattern` should be tied to batch usage."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--pattern", "*.stl"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--pattern requires --batch" in captured.err


def test_main_pattern_rejects_traversal(capsys):
    """Traversal tokens in --pattern should be rejected."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--batch", "--pattern", "../*.stl", "--input-dir", "models"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "Parent directory traversal detected in pattern" in captured.err


def test_main_aggressive_repair_requires_repair(capsys):
    """Aggressive repair flag should mandate --repair."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--aggressive-repair"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--aggressive-repair requires --repair" in captured.err


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


def test_main_max_workers_requires_parallel(capsys):
    """Specifying worker counts without parallel should be rejected."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--max-workers", "4"])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--max-workers requires --parallel" in captured.err


def test_main_output_must_be_json(tmp_path, capsys):
    """Non-JSON output formats should be rejected for consistency."""
    bad_output = tmp_path / "report.txt"

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--output", str(bad_output)])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--output must point to a .json file" in captured.err


def test_main_save_repaired_requires_supported_extension(tmp_path, capsys):
    """Repaired mesh targets must use supported mesh extensions."""
    destination = tmp_path / "repaired.txt"

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["model.stl", "--repair", "--save-repaired", str(destination)])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--save-repaired must use a supported mesh extension" in captured.err


def test_main_read_only_conflicts_with_output(tmp_path, capsys):
    """Read-only mode should forbid specifying --output."""
    output_path = tmp_path / "report.json"

    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "model.stl",
            "--read-only-output",
            "--output",
            str(output_path),
        ])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--read-only-output cannot be combined with --output" in captured.err


def test_main_read_only_conflicts_with_save_repaired(tmp_path, capsys):
    """Read-only mode should forbid repaired mesh persistence."""
    save_path = tmp_path / "fixed.stl"

    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "model.stl",
            "--repair",
            "--read-only-output",
            "--save-repaired",
            str(save_path),
        ])

    captured = capsys.readouterr()

    assert excinfo.value.code == 2
    assert "--read-only-output cannot be combined with --save-repaired" in captured.err


def test_main_hash_manifest_success(tmp_path, capsys, monkeypatch):
    """`--hash-manifest` should enforce manifest digests in hash-only mode."""
    mesh_path = tmp_path / "model.stl"
    mesh_path.write_bytes(b"triangle data")

    hasher = hashlib.sha256()
    hasher.update(b"triangle data")
    expected_digest = hasher.hexdigest()

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"files": {"model.stl": expected_digest}}), encoding="utf-8")

    monkeypatch.setattr(cli, "find_mesh_files", lambda args: ([mesh_path], []))

    exit_code = cli.main([
        str(mesh_path),
        "--hash-only",
        "--hash-manifest",
        str(manifest_path),
    ])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert expected_digest in captured.out


def test_main_hash_manifest_mismatch(tmp_path, capsys, monkeypatch):
    """Hash manifest mismatches should surface as failures with exit code 1."""
    mesh_path = tmp_path / "model.stl"
    mesh_path.write_bytes(b"triangle data")

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"files": {"model.stl": "0" * 64}}), encoding="utf-8")

    monkeypatch.setattr(cli, "find_mesh_files", lambda args: ([mesh_path], []))

    exit_code = cli.main([
        str(mesh_path),
        "--hash-only",
        "--hash-manifest",
        str(manifest_path),
    ])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "observed_sha256" in captured.out
