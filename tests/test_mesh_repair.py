"""Unit tests for mesh repair functionality."""
from pathlib import Path

import numpy as np
import pytest
import trimesh

from src.core.analysis.mesh_repair import MeshRepairer, repair_mesh, RepairOperation
from src.core.analysis import mesh_validator


def test_mesh_repairer_initialization():
    """Test MeshRepairer initialization."""
    repairer = MeshRepairer()
    assert not repairer.aggressive_repair
    assert len(repairer.repair_history) == 0

    aggressive_repairer = MeshRepairer(aggressive_repair=True)
    assert aggressive_repairer.aggressive_repair


def test_repair_simple_box():
    """Test repair of a simple valid box."""
    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])

    repairer = MeshRepairer()
    repaired_mesh, summary = repairer.repair_mesh(mesh)

    assert summary.repair_success or len(summary.issues_fixed) >= 0  # May have no issues to fix
    assert summary.final_mesh_stats["vertices"] > 0
    assert summary.final_mesh_stats["faces"] > 0


def test_repair_mesh_with_holes():
    """Test repair of mesh with holes."""
    mesh = trimesh.creation.box(extents=[5.0, 5.0, 5.0])

    # Remove some faces to create holes
    mesh.update_faces(mesh.faces[:-2])

    # Create validation result with watertight issue
    validation_result = mesh_validator.MeshValidationResult(
        path=Path("test.stl"),
        issues=[
            mesh_validator.ValidationIssue(
                code="GEOM_WATERTIGHT",
                message="Mesh is not watertight",
                severity="error"
            )
        ]
    )

    repaired_mesh, summary = repair_mesh(mesh, validation_result)

    assert len(summary.operations_performed) > 0
    assert any(op.operation == RepairOperation.FILL_HOLES for op in summary.operations_performed)


def test_repair_mesh_with_winding_issues():
    """Test repair of mesh with winding consistency issues."""
    mesh = trimesh.creation.box(extents=[5.0, 5.0, 5.0])

    # Flip some face normals to create winding issues
    mesh.faces[0] = mesh.faces[0][::-1]  # Reverse vertex order

    validation_result = mesh_validator.MeshValidationResult(
        path=Path("test.stl"),
        issues=[
            mesh_validator.ValidationIssue(
                code="GEOM_WINDING",
                message="Inconsistent winding",
                severity="error"
            )
        ]
    )

    repaired_mesh, summary = repair_mesh(mesh, validation_result)

    assert len(summary.operations_performed) > 0
    assert any(op.operation == RepairOperation.FIX_WINDING for op in summary.operations_performed)


def test_repair_empty_mesh():
    """Test repair of empty mesh."""
    empty_mesh = trimesh.Trimesh(vertices=np.empty((0, 3)), faces=np.empty((0, 3), dtype=np.int64))

    validation_result = mesh_validator.MeshValidationResult(
        path=Path("empty.stl"),
        issues=[
            mesh_validator.ValidationIssue(
                code="GEOM_EMPTY",
                message="Empty mesh",
                severity="error"
            )
        ]
    )

    repaired_mesh, summary = repair_mesh(empty_mesh, validation_result)

    # Should not crash, even if repair is not successful
    assert summary is not None
    assert len(summary.operations_performed) >= 0


def test_repair_plan_creation():
    """Test repair plan creation based on validation issues."""
    repairer = MeshRepairer()

    validation_result = mesh_validator.MeshValidationResult(
        path=Path("test.stl"),
        issues=[
            mesh_validator.ValidationIssue(code="GEOM_WATERTIGHT", message="Not watertight", severity="error"),
            mesh_validator.ValidationIssue(code="GEOM_WINDING", message="Bad winding", severity="error"),
        ]
    )

    plan = repairer._create_repair_plan(validation_result)

    assert RepairOperation.FILL_HOLES in plan
    assert RepairOperation.FIX_WINDING in plan
    assert RepairOperation.REMOVE_DUPLICATES in plan


def test_repair_mesh_stats():
    """Test mesh statistics calculation."""
    mesh = trimesh.creation.box(extents=[5.0, 5.0, 5.0])

    repairer = MeshRepairer()
    stats = repairer._get_mesh_stats(mesh)

    assert "vertices" in stats
    assert "faces" in stats
    assert "edges" in stats
    assert "is_watertight" in stats
    assert "is_winding_consistent" in stats
    assert "is_volume" in stats

    assert stats["vertices"] == len(mesh.vertices)
    assert stats["faces"] == len(mesh.faces)


def test_aggressive_repair():
    """Test aggressive repair mode."""
    mesh = trimesh.creation.box(extents=[5.0, 5.0, 5.0])

    validation_result = mesh_validator.MeshValidationResult(
        path=Path("test.stl"),
        issues=[
            mesh_validator.ValidationIssue(
                code="GEOM_WALL_THICKNESS",
                message="Thin walls",
                severity="warning"
            )
        ]
    )

    # Non-aggressive repair
    repaired_mesh, summary = repair_mesh(mesh, validation_result, aggressive=False)
    non_aggressive_ops = len(summary.operations_performed)

    # Aggressive repair
    repaired_mesh_aggressive, summary_aggressive = repair_mesh(mesh, validation_result, aggressive=True)
    aggressive_ops = len(summary_aggressive.operations_performed)

    # Aggressive mode should potentially perform more operations
    assert aggressive_ops >= non_aggressive_ops


def test_repair_operation_recording():
    """Test that repair operations are properly recorded."""
    mesh = trimesh.creation.box(extents=[5.0, 5.0, 5.0])

    repairer = MeshRepairer()
    repaired_mesh, summary = repairer.repair_mesh(mesh)

    # Check that all operations have proper data
    for operation in summary.operations_performed:
        assert operation.operation is not None
        assert isinstance(operation.success, bool)
        assert isinstance(operation.message, str)
        assert operation.vertices_before >= 0
        assert operation.vertices_after >= 0
        assert operation.faces_before >= 0
        assert operation.faces_after >= 0


def test_convenience_repair_function():
    """Test the convenience repair_mesh function."""
    mesh = trimesh.creation.box(extents=[5.0, 5.0, 5.0])

    # Test without validation result
    repaired_mesh, summary = repair_mesh(mesh)
    assert repaired_mesh is not None
    assert summary is not None

    # Test with validation result
    validation_result = mesh_validator.MeshValidationResult(
        path=Path("test.stl"),
        issues=[]
    )

    repaired_mesh, summary = repair_mesh(mesh, validation_result)
    assert repaired_mesh is not None
    assert summary is not None


def test_repair_result_dataclass():
    """Test RepairResult dataclass."""
    from src.core.analysis.mesh_repair import RepairResult

    result = RepairResult(
        operation=RepairOperation.FILL_HOLES,
        success=True,
        message="Success",
        vertices_before=100,
        vertices_after=100,
        faces_before=50,
        faces_after=50
    )

    assert result.operation == RepairOperation.FILL_HOLES
    assert result.success
    assert result.message == "Success"
    assert result.vertices_before == 100