"""Tests for batch CLI helpers."""
from __future__ import annotations

from types import SimpleNamespace

from src.cli_batch import find_mesh_files


def _make_args(**overrides):
    defaults = {
        "mesh": None,
        "pattern": None,
        "input_dir": None,
        "progress": True,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_find_mesh_files_collects_and_sorts(tmp_path):
    """find_mesh_files should return a sorted, de-duplicated list of paths."""
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()

    file_a = tmp_path / "b_model.stl"
    file_b = nested_dir / "a_model.obj"
    file_c = nested_dir / "c_model.PLY"
    file_a.write_text("", encoding="utf-8")
    file_b.write_text("", encoding="utf-8")
    file_c.write_text("", encoding="utf-8")

    args = _make_args(mesh=[str(tmp_path)], pattern=None, input_dir=None)

    files, hints = find_mesh_files(args)

    assert [p.name for p in files] == [
        "a_model.obj",
        "b_model.stl",
        "c_model.PLY",
    ]
    assert hints == []


def test_find_mesh_files_handles_mixed_sources(tmp_path):
    """Direct paths, directories, and patterns should combine without duplicates."""
    direct_file = tmp_path / "direct.stl"
    direct_file.write_text("", encoding="utf-8")

    dir_one = tmp_path / "dir_one"
    dir_one.mkdir()
    (dir_one / "pattern1.obj").write_text("", encoding="utf-8")

    dir_two = tmp_path / "dir_two"
    dir_two.mkdir()
    (dir_two / "pattern2.stl").write_text("", encoding="utf-8")

    pattern = "dir_two/*.stl"

    args = _make_args(
        mesh=[str(direct_file), str(dir_one)],
        pattern=pattern,
        input_dir=tmp_path,
    )

    files, hints = find_mesh_files(args)

    assert [p.name for p in files] == [
        "direct.stl",
        "pattern1.obj",
        "pattern2.stl",
    ]
    assert hints == []


def test_find_mesh_files_deduplicates(tmp_path):
    """Duplicate references to the same file should be collapsed."""
    shared = tmp_path / "shared.obj"
    shared.write_text("", encoding="utf-8")

    args = _make_args(
        mesh=[str(shared)],
        pattern=str(tmp_path / "*.obj"),
        input_dir=None,
    )

    files, hints = find_mesh_files(args)

    assert [p.name for p in files] == ["shared.obj"]
    assert hints == []


def test_find_mesh_files_returns_empty_for_missing(tmp_path):
    """No matches should produce an empty list."""
    args = _make_args(
        mesh=[str(tmp_path / "*.stl")],
        pattern=None,
        input_dir=None,
    )

    files, hints = find_mesh_files(args)

    assert files == []
    assert hints != []
    assert any("No meshes" in hint for hint in hints)


def test_find_mesh_files_supports_modern_formats(tmp_path):
    """3MF and AMF files should be detected alongside legacy formats."""
    model_3mf = tmp_path / "sample.3mf"
    model_amf = tmp_path / "sample.amf"
    model_3mf.write_text("", encoding="utf-8")
    model_amf.write_text("", encoding="utf-8")

    args = _make_args(mesh=[str(tmp_path)])

    files, hints = find_mesh_files(args)

    assert [p.name for p in files] == ["sample.3mf", "sample.amf"]
    assert hints == []


def test_find_mesh_files_skips_symlinks(tmp_path):
    """Symbolic links should not be returned during discovery."""
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    real_file = real_dir / "asset.stl"
    real_file.write_text("", encoding="utf-8")

    symlink = tmp_path / "alias"
    symlink.symlink_to(real_dir)

    args = _make_args(mesh=[str(symlink)])

    files, hints = find_mesh_files(args)

    assert [p.name for p in files] == []
    assert hints != []
    assert any("Skipped symbolic link" in hint for hint in hints)


def test_find_mesh_files_blocks_traversal(tmp_path):
    outside_file = tmp_path.parent / "escape.obj"
    outside_file.write_text("", encoding="utf-8")

    args = _make_args(pattern="../escape.obj", input_dir=tmp_path)

    files, hints = find_mesh_files(args)

    assert files == []
    assert hints != []
    assert any("Traversal" in hint for hint in hints)


def test_find_mesh_files_reports_missing_path_hint(tmp_path):
    """Missing mesh arguments should yield a descriptive hint."""
    missing = tmp_path / "missing.stl"

    args = _make_args(mesh=[str(missing)])

    files, hints = find_mesh_files(args)

    assert files == []
    assert any("Path not found" in hint for hint in hints)


def test_find_mesh_files_reports_empty_pattern_hint(tmp_path):
    """Patterns without matches are surfaced as hints."""
    args = _make_args(pattern="*.stl", input_dir=tmp_path)

    files, hints = find_mesh_files(args)

    assert files == []
    assert any("Pattern produced no meshes" in hint for hint in hints)
