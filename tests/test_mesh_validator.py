"""Unit tests for `mesh_validator` module."""
from pathlib import Path

import numpy as np
import pytest
import trimesh
from trimesh.transformations import rotation_matrix

from src.core.analysis import mesh_validator


def test_validate_mesh_success_on_box():
    mesh = trimesh.creation.box(extents=[10.0, 20.0, 5.0])

    result = mesh_validator.validate_mesh(mesh, source_path=Path("box.stl"))

    assert result.success is True
    assert result.metrics is not None
    assert pytest.approx(result.metrics.surface_area_mm2, rel=1e-6) == mesh.area
    assert pytest.approx(result.metrics.volume_mm3, rel=1e-6) == mesh.volume
    assert result.metrics.component_count == 1
    assert pytest.approx(result.metrics.min_wall_thickness_mm, rel=1e-5) == 5.0
    assert pytest.approx(result.metrics.center_of_gravity_mm[0], rel=1e-6) == 0.0
    assert pytest.approx(result.metrics.bounding_box_mm[0], rel=1e-6) == 10.0
    assert result.metrics.cavities_detected == 0
    assert result.metrics.thin_tip_faces == 0
    assert result.metrics.floating_shell_count == 0
    assert result.metrics.min_hole_diameter_mm == 0.0
    assert result.metrics.high_aspect_ratio_faces == 0
    assert result.metrics.sharp_internal_corners == 0
    assert result.metrics.surface_roughness_score == 0.0
    assert result.metrics.bed_contact_area_mm2 > 0.0
    assert pytest.approx(result.metrics.volume_cm3, rel=1e-6) == mesh.volume / 1000.0
    assert result.metrics.bounding_box_diagonal_mm > 0.0
    assert result.metrics.scale_consistent is True
    assert result.metrics.auto_orientation_bed_area_mm2 >= result.metrics.bed_contact_area_mm2
    assert len(result.metrics.auto_orientation_euler_deg) == 3
    assert not result.issues


def test_validate_mesh_detects_hole():
    mesh = trimesh.creation.box(extents=[5.0, 5.0, 5.0])
    mesh.update_vertices()
    mesh.faces = mesh.faces[:-1]

    result = mesh_validator.validate_mesh(mesh)

    assert result.success is False
    codes = {issue.code for issue in result.issues}
    assert "GEOM_WATERTIGHT" in codes
    assert "GEOM_VOLUME" in codes
    assert result.metrics is None


def test_validate_mesh_handles_empty_mesh():
    empty_mesh = trimesh.Trimesh(vertices=np.empty((0, 3)), faces=np.empty((0, 3), dtype=np.int64))

    result = mesh_validator.validate_mesh(empty_mesh)

    assert result.success is False
    assert len(result.issues) == 1
    assert result.issues[0].code == "GEOM_EMPTY"
    assert result.metrics is None


def test_validate_mesh_flags_small_feature_warning():
    mesh = trimesh.creation.box(extents=[5.0, 5.0, 5.0])

    result = mesh_validator.validate_mesh(
        mesh,
        settings=mesh_validator.MeshValidationSettings(min_feature_size_mm=15.0),
    )

    codes = {issue.code for issue in result.issues}
    assert "GEOM_SMALL_FEATURE" in codes
    assert result.metrics is not None
    assert pytest.approx(result.metrics.min_edge_length_mm, rel=1e-6) == 5.0


def test_validate_mesh_detects_overhang_faces():
    mesh = trimesh.creation.box(extents=[10.0, 10.0, 2.0])
    mesh.apply_transform(rotation_matrix(np.radians(75.0), [1.0, 0.0, 0.0]))
    mesh.apply_translation([0.0, 0.0, 5.0])

    settings = mesh_validator.MeshValidationSettings(support_overhang_angle_deg=30.0)
    result = mesh_validator.validate_mesh(mesh, settings=settings)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_OVERHANG" in codes
    assert result.metrics is not None
    assert result.metrics.overhang_face_count > 0


def test_validate_mesh_flags_walls_under_threshold():
    mesh = trimesh.creation.box(extents=[6.0, 4.0, 2.0])

    settings = mesh_validator.MeshValidationSettings(min_wall_thickness_mm=3.0)
    result = mesh_validator.validate_mesh(mesh, settings=settings)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_WALL_THICKNESS" in codes
    assert result.metrics is not None
    assert pytest.approx(result.metrics.min_wall_thickness_mm, rel=1e-6) == 2.0


def test_validate_mesh_detects_self_intersection():
    mesh = trimesh.creation.box(extents=[5.0, 5.0, 5.0])
    overlap = mesh.copy()
    overlap.apply_translation([2.0, 0.0, 0.0])
    combined = trimesh.util.concatenate([mesh, overlap])

    result = mesh_validator.validate_mesh(combined)

    assert result.success is False
    codes = {issue.code for issue in result.issues}
    assert "GEOM_SELF_INTERSECTION" in codes


def test_validate_mesh_detects_thin_tip_warning():
    mesh = trimesh.creation.cone(radius=0.5, height=6.0)
    mesh.apply_translation([0.0, 0.0, 3.0])

    result = mesh_validator.validate_mesh(mesh)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_THIN_TIP" in codes
    assert result.metrics is not None
    assert result.metrics.thin_tip_faces > 0


def test_validate_mesh_detects_cavities():
    outer = trimesh.creation.box(extents=[20.0, 20.0, 20.0])
    inner = trimesh.creation.icosphere(subdivisions=1, radius=3.0)
    inner.apply_translation([0.0, 0.0, 0.0])
    combined = trimesh.util.concatenate([outer, inner])

    result = mesh_validator.validate_mesh(combined)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_CAVITIES" in codes
    assert result.metrics is not None
    assert result.metrics.cavities_detected > 0


def test_validate_mesh_detects_floating_shells():
    main_body = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    floating = trimesh.creation.box(extents=[2.0, 2.0, 2.0])
    floating.apply_translation([15.0, 0.0, 0.0])
    combined = trimesh.util.concatenate([main_body, floating])

    result = mesh_validator.validate_mesh(combined)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_FLOATING_SHELL" in codes
    assert result.metrics is not None
    assert result.metrics.floating_shell_count >= 1


def test_validate_mesh_detects_small_hole():
    if not hasattr(trimesh.creation, "tube"):
        pytest.skip("trimesh.creation.tube unavailable")

    mesh = trimesh.creation.tube(inner_radius=0.3, outer_radius=2.0, height=6.0, sections=32)

    settings = mesh_validator.MeshValidationSettings(min_hole_diameter_mm=1.0)
    result = mesh_validator.validate_mesh(mesh, settings=settings)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_SMALL_HOLE" in codes
    assert result.metrics is not None
    assert result.metrics.min_hole_diameter_mm < settings.min_hole_diameter_mm


def test_validate_mesh_detects_high_aspect_ratio_faces():
    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    mesh = mesh.subdivide()
    stretched = mesh.copy()
    stretched.vertices[:, 0] *= 10.0

    result = mesh_validator.validate_mesh(stretched)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_ASPECT_RATIO" in codes
    assert result.metrics is not None
    assert result.metrics.high_aspect_ratio_faces > 0


def test_validate_mesh_detects_sharp_internal_corners():
    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    notch = trimesh.creation.box(extents=[2.0, 2.0, 2.0])
    notch.apply_translation([4.0, 0.0, 0.0])
    combined = mesh.difference(notch)

    result = mesh_validator.validate_mesh(combined)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_SHARP_INTERNAL_CORNER" in codes
    assert result.metrics is not None
    assert result.metrics.sharp_internal_corners > 0


def test_validate_mesh_detects_surface_roughness_warning():
    mesh = trimesh.creation.icosphere(subdivisions=3, radius=5.0)

    settings = mesh_validator.MeshValidationSettings(max_surface_roughness_score=0.05)
    result = mesh_validator.validate_mesh(mesh, settings=settings)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_SURFACE_ROUGHNESS" in codes
    assert result.metrics is not None
    assert result.metrics.surface_roughness_score > settings.max_surface_roughness_score


def test_validate_mesh_detects_low_bed_contact_area():
    mesh = trimesh.creation.cone(radius=2.0, height=10.0)
    mesh.apply_translation([0.0, 0.0, 5.0])

    settings = mesh_validator.MeshValidationSettings(min_bed_contact_area_mm2=200.0)
    result = mesh_validator.validate_mesh(mesh, settings=settings)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_BED_ADHESION" in codes
    assert result.metrics is not None
    assert result.metrics.bed_contact_area_mm2 < settings.min_bed_contact_area_mm2


def test_validate_mesh_detects_scale_inconsistency():
    mesh = trimesh.creation.box(extents=[0.01, 0.01, 0.01])

    settings = mesh_validator.MeshValidationSettings(min_model_extent_mm=0.5)
    result = mesh_validator.validate_mesh(mesh, settings=settings)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_SCALE" in codes
    assert result.metrics is not None
    assert result.metrics.scale_consistent is False


def test_validate_mesh_detects_flatness_issue():
    base = trimesh.creation.box(extents=[20.0, 20.0, 5.0])
    modifier = trimesh.creation.box(extents=[20.0, 20.0, 0.2])
    modifier.apply_translation([0.0, 0.0, 2.8])
    warped = trimesh.boolean.difference(base, modifier, engine="scad")
    if warped is None:
        pytest.skip("Boolean difference unavailable")

    settings = mesh_validator.MeshValidationSettings(max_flatness_deviation_mm=0.05)
    result = mesh_validator.validate_mesh(warped, settings=settings)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_FLATNESS" in codes
    assert result.metrics is not None
    assert result.metrics.flatness_deviation_mm > settings.max_flatness_deviation_mm


def test_validate_mesh_provides_repair_guidance():
    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    mesh.update_vertices()
    mesh.faces = mesh.faces[:-2]

    result = mesh_validator.validate_mesh(mesh)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_REPAIR_GUIDANCE" in codes
    assert any(code in {"GEOM_WATERTIGHT", "GEOM_VOLUME"} for code in codes)
    assert result.metrics is not None
    assert result.metrics.repair_suggestions


def test_validate_mesh_provides_auto_orientation_suggestion():
    mesh = trimesh.creation.box(extents=[20.0, 10.0, 5.0])

    result = mesh_validator.validate_mesh(mesh)

    assert result.metrics is not None
    assert result.metrics.auto_orientation_bed_area_mm2 >= result.metrics.bed_contact_area_mm2
    assert len(result.metrics.auto_orientation_euler_deg) == 3


def test_validate_mesh_checks_obj_materials(tmp_path):
    obj_path = tmp_path / "test.obj"
    obj_path.write_text("""v 0 0 0
v 1 0 0
v 0 1 0
f 1 2 3
""")

    mesh = trimesh.load_mesh(obj_path, process=False)

    result = mesh_validator.validate_mesh(mesh, source_path=obj_path)

    codes = {issue.code for issue in result.issues}
    assert "GEOM_OBJ_MATERIAL" in codes
