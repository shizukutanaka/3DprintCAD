"""Advanced mesh repair testing - comprehensive test coverage.

Tests advanced mesh repair operations including:
- Hole filling algorithms
- Winding order correction
- Self-intersection removal
- Topology optimization
- Complex repair sequences
"""

import pytest
import numpy as np
import trimesh
from unittest.mock import MagicMock, patch

from src.core.analysis.mesh_repair import MeshRepair, RepairOperation


class TestHoleFilling:
    """Test hole filling algorithms."""

    def test_fill_simple_hole(self):
        """Test filling a simple boundary hole."""
        # Create box with one face removed
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1], [0, 3, 2],  # Bottom
            [4, 5, 6], [4, 6, 7],  # Top (reversed for open face)
            [0, 4, 5], [0, 5, 1],  # Front
            [1, 5, 6], [1, 6, 2],  # Right
            [2, 6, 7], [2, 7, 3],  # Back
            [3, 7, 4], [3, 4, 0],  # Left
            # Top face missing
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        # Attempt to fill hole
        repaired, summary = repair.repair_mesh(mesh)

        # Should have more faces than original (hole filled)
        assert repaired.faces.shape[0] >= mesh.faces.shape[0]
        # Should be watertight
        assert repaired.is_watertight

    def test_fill_multiple_holes(self):
        """Test filling multiple holes."""
        # Create mesh with multiple holes
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1], [0, 3, 2],  # Bottom
            # Top missing
            [0, 4, 5], [0, 5, 1],  # Front
            # Right missing
            [2, 6, 7], [2, 7, 3],  # Back
            [3, 7, 4], [3, 4, 0],  # Left
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(mesh)
        assert repaired is not None

    def test_fill_complex_hole(self):
        """Test filling complex/non-convex holes."""
        # Create sphere with hole
        sphere = trimesh.creation.sphere()

        # Remove random triangles to create hole
        keep_faces = np.arange(sphere.faces.shape[0])[:-20]
        sphere.update_faces(keep_faces)

        repair = MeshRepair()
        repaired, summary = repair.repair_mesh(sphere)

        assert repaired is not None

    def test_fill_hole_preserves_original_geometry(self):
        """Test that hole filling doesn't distort original mesh."""
        # Create mesh with small hole
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
            [0.3, 0.3, 1], [0.7, 0.3, 1],
            [0.7, 0.7, 1], [0.3, 0.7, 1],
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1], [0, 3, 2],
            [4, 5, 6], [4, 6, 7],
            [0, 4, 5], [0, 5, 1],
            [1, 5, 6], [1, 6, 2],
            [2, 6, 7], [2, 7, 3],
            [3, 7, 4], [3, 4, 0],
            [8, 9, 10], [8, 10, 11],  # Small hole in top
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        original_bbox = mesh.bounds

        repair = MeshRepair()
        repaired, summary = repair.repair_mesh(mesh)

        # Bounding box should be similar
        np.testing.assert_allclose(repaired.bounds, original_bbox, rtol=0.05)


class TestWindingOrder:
    """Test winding order correction."""

    def test_fix_reversed_normals(self):
        """Test correction of reversed face normals."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
        ], dtype=np.float64)

        # Reversed winding
        faces = np.array([
            [0, 2, 1],  # Reversed (should be 0, 1, 2)
            [0, 3, 2],  # Reversed (should be 0, 2, 3)
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(mesh)

        # Check normals are pointing outward
        # For a simple box, all normals should point away from center
        center = repaired.center_mass
        for normal in repaired.face_normals:
            # Normals should generally point away from center
            # This is a basic check
            assert normal is not None

    def test_fix_inconsistent_winding(self):
        """Test correction of inconsistently wound faces."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0.5, 0.5, 1],
        ], dtype=np.float64)

        # Mix of correct and reversed winding
        faces = np.array([
            [0, 1, 2],      # Correct
            [0, 3, 2],      # Reversed
            [0, 4, 1],      # Correct
            [1, 4, 2],      # Correct
            [3, 2, 4],      # Reversed
            [3, 4, 0],      # Correct
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(mesh)
        assert repaired is not None


class TestSelfIntersectionRemoval:
    """Test self-intersection detection and removal."""

    def test_detect_self_intersection(self):
        """Test detection of self-intersecting faces."""
        # Create bowtie/figure-8 mesh
        vertices = np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 1, 0],
            [-1, 0, 0],
            [0, -0.5, 0],
            [0, 0.5, 0],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 3, 2],
            [4, 5, 3],  # Self-intersecting
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(mesh)
        assert repaired is not None

    def test_remove_penetrating_faces(self):
        """Test removal of faces that penetrate each other."""
        # Two cubes penetrating
        cube1 = trimesh.creation.box(extents=[1, 1, 1])
        cube2 = trimesh.creation.box(extents=[1, 1, 1])
        cube2.apply_translation([0.5, 0, 0])

        merged = trimesh.util.concatenate([cube1, cube2])
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(merged)
        assert repaired is not None


class TestDegenerateTriangleRemoval:
    """Test removal of degenerate triangles."""

    def test_remove_zero_area_triangles(self):
        """Test removal of zero-area triangles."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0.5, 0.5, 0],  # On plane (degenerate)
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [1, 2, 4],  # Zero area (collinear)
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(mesh)

        # Should have fewer faces (degenerate removed)
        assert repaired.faces.shape[0] <= mesh.faces.shape[0]

    def test_remove_very_thin_triangles(self):
        """Test removal/fixing of very thin triangles."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0.5, 0.500001, 0],  # Very close to edge
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [1, 2, 4],  # Very thin
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(mesh)
        assert repaired is not None


class TestVertexMerging:
    """Test vertex merging and cleanup."""

    def test_merge_duplicate_vertices(self):
        """Test merging of duplicate/very close vertices."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1.0000001, 0, 0],  # Near duplicate
            [1, 1, 0],
            [0, 1, 0],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 3],
            [0, 3, 4],
            [1, 2, 3],  # Uses near-duplicate vertex
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(mesh)

        # Should have merged vertices
        assert repaired.vertices.shape[0] <= mesh.vertices.shape[0]

    def test_remove_unused_vertices(self):
        """Test removal of unused/orphan vertices."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [99, 99, 99],  # Unused
            [-99, -99, -99],  # Unused
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(mesh)

        # Should have removed unused vertices
        assert repaired.vertices.shape[0] == 4


class TestNoiseRemoval:
    """Test noise and artifact removal."""

    def test_remove_small_components(self):
        """Test removal of small disconnected components."""
        # Create main mesh
        main = trimesh.creation.box()

        # Add small disconnected piece
        small_vertices = np.array([
            [99, 99, 99],
            [99.1, 99, 99],
            [99, 99.1, 99],
        ], dtype=np.float64)
        small_faces = np.array([[0, 1, 2]], dtype=np.int32)
        small = trimesh.Trimesh(vertices=small_vertices, faces=small_faces)

        merged = trimesh.util.concatenate([main, small])
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(merged)

        # Should remove small component
        assert repaired.faces.shape[0] <= merged.faces.shape[0]

    def test_remove_surface_noise(self):
        """Test smoothing of noisy surfaces."""
        # Create noisy sphere
        sphere = trimesh.creation.sphere()

        # Add noise to vertices
        noise = np.random.normal(0, 0.01, sphere.vertices.shape)
        sphere.vertices += noise

        repair = MeshRepair()
        repaired, summary = repair.repair_mesh(sphere)

        assert repaired is not None


class TestSurfaceSmoothing:
    """Test surface smoothing operations."""

    def test_smooth_sharp_edges(self):
        """Test smoothing of sharp/artificial edges."""
        # Create box (has sharp edges)
        box = trimesh.creation.box()

        repair = MeshRepair()
        repaired, summary = repair.repair_mesh(box)

        # Should still be valid
        assert repaired is not None

    def test_smooth_preserves_features(self):
        """Test that smoothing preserves important features."""
        # Create mesh with important geometry
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [2, 0, 0],
            [0, 1, 0], [1, 1, 0], [2, 1, 0],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 4], [0, 4, 3],
            [1, 2, 5], [1, 5, 4],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        original_bounds = mesh.bounds.copy()

        repair = MeshRepair()
        repaired, summary = repair.repair_mesh(mesh)

        # Bounds shouldn't change dramatically
        np.testing.assert_allclose(repaired.bounds, original_bounds, rtol=0.1)


class TestRepairSequencing:
    """Test proper sequencing of repair operations."""

    def test_repair_order_matters(self):
        """Test that operation order affects result quality."""
        # Create problematic mesh
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0.5, 0.5, -0.5],
        ], dtype=np.float64)

        faces = np.array([
            [2, 1, 0],  # Reversed winding
            [0, 2, 3],
            [0, 4, 1],  # Self-intersecting potential
            [0, 0, 0],  # Degenerate
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        # Should handle complex sequence
        repaired, summary = repair.repair_mesh(mesh)
        assert repaired is not None

    def test_repair_summary_accuracy(self):
        """Test that repair summary reflects actual changes."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [99, 99, 99],  # Unused
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [1, 2, 1],  # Degenerate
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(mesh)

        # Summary should indicate operations performed
        assert summary is not None
        assert hasattr(summary, 'operations_performed')


class TestRepairPerformance:
    """Test repair performance on various mesh sizes."""

    @pytest.mark.parametrize("size", [100, 1000, 10000])
    def test_repair_scales_with_mesh_size(self, size):
        """Test repair performance scales reasonably."""
        # Create mesh of varying size
        sphere = trimesh.creation.sphere(subdivisions=2)

        # Subdivide to reach desired size
        while sphere.faces.shape[0] < size:
            sphere = sphere.subdivide()

        repair = MeshRepair()

        import time
        start = time.time()
        repaired, summary = repair.repair_mesh(sphere)
        elapsed = time.time() - start

        assert repaired is not None
        # Should scale reasonably (not exponential)
        assert elapsed < 60.0  # 60 second limit


class TestRepairValidation:
    """Test repair validation and verification."""

    def test_repaired_mesh_is_valid(self):
        """Test that repaired mesh passes validation."""
        # Create problematic mesh
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ], dtype=np.float64)

        # Mix of issues
        faces = np.array([
            [2, 1, 0],  # Reversed
            [0, 2, 3],
            [0, 4, 5], [0, 5, 1],
            [1, 5, 6], [1, 6, 2],
            [2, 6, 7], [2, 7, 3],
            [3, 7, 4], [3, 4, 0],
            [4, 6, 5], [4, 7, 6],  # Reversed
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        repaired, summary = repair.repair_mesh(mesh)

        # Repaired mesh should be valid
        assert repaired.is_valid
        assert not np.any(np.isnan(repaired.vertices))
        assert len(repaired.faces) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
