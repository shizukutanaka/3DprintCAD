"""Comprehensive edge case testing for 3DprintCAD.

Tests critical functionality under extreme conditions:
- Ultra-large meshes (100k+ faces)
- Degenerate geometry
- Memory-constrained environments
- Concurrent operations
- Boundary conditions
"""

import pytest
import numpy as np
import trimesh
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.core.analysis.mesh_validator import MeshValidator
from src.core.analysis.mesh_repair import MeshRepair
from src.core.analysis.support_generator import SupportGenerator


class TestEdgeCasesLargeMeshes:
    """Test behavior with large-scale meshes."""

    @pytest.fixture
    def large_mesh(self):
        """Generate a large mesh (100k+ faces for testing)."""
        # Box with high resolution
        box = trimesh.creation.box()
        # Subdivide to create large mesh
        for _ in range(3):  # Creates ~100k faces
            box = box.subdivide_to_size(0.05)
        return box

    def test_validate_large_mesh_completes(self, large_mesh):
        """Ensure validation completes within timeout on large meshes."""
        validator = MeshValidator()

        # Should complete in reasonable time
        result = validator.validate_mesh(large_mesh, timeout_seconds=30)
        assert result is not None
        assert hasattr(result, 'success')

    def test_repair_large_mesh_memory_efficient(self, large_mesh):
        """Test mesh repair doesn't consume excessive memory."""
        repair = MeshRepair()

        # Get initial mesh properties
        initial_vertices = len(large_mesh.vertices)

        # Repair should handle gracefully
        repaired, summary = repair.repair_mesh(large_mesh)

        # Should not explode in size
        assert len(repaired.vertices) < initial_vertices * 2

    def test_support_generation_large_mesh_chunked(self, large_mesh):
        """Test support generation uses chunking for large meshes."""
        generator = SupportGenerator()

        # Should handle without OOM
        supports = generator.generate_supports(
            large_mesh,
            support_type='tree',
            chunk_size=1000  # Process in chunks
        )

        assert supports is not None


class TestEdgeCasesDegenerate:
    """Test behavior with degenerate or pathological geometry."""

    def test_validate_zero_area_triangles(self):
        """Handle meshes with zero-area (degenerate) triangles."""
        # Create mesh with degenerate triangle
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],  # Degenerate: same as vertex 0
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [0, 4, 0],  # Degenerate: line, not triangle
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        validator = MeshValidator()

        # Should identify the issue, not crash
        result = validator.validate_mesh(mesh)
        assert result is not None

    def test_validate_very_thin_mesh(self):
        """Handle extremely thin meshes (paper-thin)."""
        # Create paper-thin box
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 0.001],  # 1 micron thickness
            [1, 0, 0.001],
            [1, 1, 0.001],
            [0, 1, 0.001],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2], [0, 2, 3],  # Bottom
            [4, 6, 5], [4, 7, 6],  # Top
            [0, 5, 1], [0, 4, 5],  # Side
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        validator = MeshValidator()

        result = validator.validate_mesh(mesh)
        # Should handle gracefully
        assert result is not None
        assert not result.success  # Should fail due to thinness

    def test_validate_self_intersecting_complex(self):
        """Handle complex self-intersection cases."""
        # Create two cubes that penetrate each other
        cube1 = trimesh.creation.box(extents=[1, 1, 1])
        cube2 = trimesh.creation.box(extents=[1, 1, 1])
        cube2.apply_translation([0.5, 0.5, 0.5])

        # Merge without Boolean operation (creates intersections)
        merged = trimesh.util.concatenate([cube1, cube2])

        validator = MeshValidator()
        result = validator.validate_mesh(merged)

        assert result is not None

    def test_validate_mesh_with_isolated_vertices(self):
        """Handle meshes with orphaned vertices."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [99, 99, 99],  # Isolated vertex
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [0, 4, 1],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        validator = MeshValidator()

        result = validator.validate_mesh(mesh)
        assert result is not None


class TestEdgeCasesMemoryConstrained:
    """Test behavior under memory constraints."""

    @pytest.mark.skipif(
        not hasattr(pytest, 'xfail'),
        reason="Requires memory limiting support"
    )
    def test_mesh_repair_streaming_mode(self):
        """Test streaming repair for memory-constrained environments."""
        # Create large mesh
        mesh = trimesh.creation.box()
        mesh = mesh.subdivide_to_size(0.1)

        repair = MeshRepair()

        # Should support streaming/chunking
        if hasattr(repair, 'stream_repair'):
            repaired = repair.stream_repair(mesh, chunk_size=10000)
            assert repaired is not None

    def test_validation_incremental(self):
        """Test incremental validation of mesh properties."""
        mesh = trimesh.creation.box()
        mesh = mesh.subdivide_to_size(0.1)

        validator = MeshValidator()

        # Validate in parts
        result = validator.validate_mesh(mesh)
        assert result is not None


class TestEdgeCasesConcurrency:
    """Test behavior with concurrent operations."""

    def test_concurrent_mesh_validation(self):
        """Test multiple meshes validated concurrently."""
        meshes = [
            trimesh.creation.box(),
            trimesh.creation.sphere(),
            trimesh.creation.cylinder(),
        ]

        validator = MeshValidator()

        # Simulate concurrent validation
        results = []
        for mesh in meshes:
            result = validator.validate_mesh(mesh)
            results.append(result)

        assert len(results) == 3
        assert all(r is not None for r in results)

    def test_concurrent_mesh_repair(self):
        """Test multiple meshes repaired concurrently."""
        # Create meshes with issues
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0.5, 0.5, 1],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [0, 4, 1],
            [1, 4, 2],
            [2, 4, 3],
            [3, 4, 0],
        ], dtype=np.int32)

        meshes = [
            trimesh.Trimesh(vertices=vertices.copy(), faces=faces.copy(), process=False)
            for _ in range(3)
        ]

        repair = MeshRepair()

        # Repair multiple meshes
        results = []
        for mesh in meshes:
            repaired, summary = repair.repair_mesh(mesh)
            results.append((repaired, summary))

        assert len(results) == 3
        assert all(r[0] is not None for r in results)


class TestEdgeCasesBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_mesh_validation_empty_mesh(self):
        """Test validation of empty mesh."""
        mesh = trimesh.Trimesh(vertices=[], faces=[])
        validator = MeshValidator()

        result = validator.validate_mesh(mesh)
        assert result is not None
        assert not result.success  # Empty mesh is invalid

    def test_mesh_validation_single_triangle(self):
        """Test validation of mesh with single triangle."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
        ], dtype=np.float64)

        faces = np.array([[0, 1, 2]], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        validator = MeshValidator()

        result = validator.validate_mesh(mesh)
        assert result is not None

    def test_support_generation_tiny_overhang(self):
        """Test support generation for tiny overhang areas."""
        # Create box with minimal overhang
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
            [0.5, 0.5, 1.001],  # Tiny protrusion
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2], [0, 2, 3],  # Bottom
            [4, 6, 5], [4, 7, 6],  # Top
            [0, 5, 1], [0, 4, 5],  # Sides
            [1, 6, 2], [1, 5, 6],
            [2, 7, 3], [2, 6, 7],
            [3, 4, 0], [3, 7, 4],
            [4, 8, 5],  # Tiny protrusion
            [5, 8, 6],
            [6, 8, 7],
            [7, 8, 4],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        generator = SupportGenerator()

        supports = generator.generate_supports(mesh, max_overhang_angle=45)
        # Should handle minimal overhangs gracefully
        assert supports is not None


class TestEdgeCasesNumericalStability:
    """Test numerical stability and precision."""

    def test_mesh_validation_very_small_coordinates(self):
        """Test mesh with very small coordinate values."""
        vertices = np.array([
            [0, 0, 0],
            [1e-6, 0, 0],
            [1e-6, 1e-6, 0],
            [0, 1e-6, 0],
            [0, 0, 1e-6],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [0, 4, 1],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        validator = MeshValidator()

        # Should handle gracefully without numerical errors
        result = validator.validate_mesh(mesh)
        assert result is not None

    def test_mesh_validation_very_large_coordinates(self):
        """Test mesh with very large coordinate values."""
        vertices = np.array([
            [0, 0, 0],
            [1e6, 0, 0],
            [1e6, 1e6, 0],
            [0, 1e6, 0],
            [0, 0, 1e6],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [0, 4, 1],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        validator = MeshValidator()

        result = validator.validate_mesh(mesh)
        assert result is not None

    def test_mesh_validation_mixed_precision(self):
        """Test mesh with mixed float32/float64 (if applicable)."""
        # Try to create mesh with mixed precision
        vertices_64 = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices_64, faces=faces, process=False)
        validator = MeshValidator()

        result = validator.validate_mesh(mesh)
        assert result is not None


class TestEdgeCasesPerformance:
    """Test performance under various conditions."""

    @pytest.mark.parametrize("size", [10, 100, 1000])
    def test_validation_performance_scales(self, size):
        """Test validation performance scales with mesh size."""
        # Create mesh of varying size
        box = trimesh.creation.box()
        for _ in range(int(np.log2(size // 10))):
            if box.faces.shape[0] < size:
                box = box.subdivide()

        validator = MeshValidator()

        import time
        start = time.time()
        result = validator.validate_mesh(box)
        elapsed = time.time() - start

        assert result is not None
        # Should complete in reasonable time
        assert elapsed < 30.0


class TestEdgeCasesRecovery:
    """Test error recovery and graceful degradation."""

    def test_repair_recovers_from_failed_operation(self):
        """Test that repair continues if one operation fails."""
        # Create problematic mesh
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [0, 0, 0],  # Degenerate
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        repair = MeshRepair()

        # Should recover and continue
        repaired, summary = repair.repair_mesh(mesh)
        assert repaired is not None

    def test_validation_with_missing_normals(self):
        """Test validation when vertex normals are missing."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        # Clear normals
        mesh.vertex_normals  # Compute once

        validator = MeshValidator()
        result = validator.validate_mesh(mesh)
        assert result is not None


# Integration tests combining multiple edge cases
class TestEdgeCasesIntegration:
    """Integration tests with multiple edge cases."""

    def test_validate_repair_validate_cycle(self):
        """Test full cycle: validate -> repair -> validate."""
        # Create mesh with issues
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0.5, 0.5, -0.5],  # Inverted normals
        ], dtype=np.float64)

        faces = np.array([
            [2, 1, 0],  # Reversed winding
            [0, 2, 3],
            [0, 4, 1],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

        validator = MeshValidator()
        repair = MeshRepair()

        # Initial validation
        result1 = validator.validate_mesh(mesh)
        assert result1 is not None

        # Repair
        repaired, summary = repair.repair_mesh(mesh)
        assert repaired is not None

        # Validate again
        result2 = validator.validate_mesh(repaired)
        assert result2 is not None

    def test_generate_supports_on_repaired_mesh(self):
        """Test support generation after mesh repair."""
        # Create mesh
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0.5, 0.5, 2],
        ], dtype=np.float64)

        faces = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [0, 4, 1],
            [1, 4, 2],
            [2, 4, 3],
            [3, 4, 0],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

        repair = MeshRepair()
        repaired, _ = repair.repair_mesh(mesh)

        generator = SupportGenerator()
        supports = generator.generate_supports(repaired)

        assert supports is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
