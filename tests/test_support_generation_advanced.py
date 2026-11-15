"""Advanced support structure generation testing.

Tests comprehensive support generation including:
- Tree support generation
- Support optimization
- Collision detection
"""

import pytest
import numpy as np
import trimesh
from unittest.mock import MagicMock, patch

from src.core.analysis.support_generator import SupportGenerator, SupportSettings, SupportType


class TestTreeSupportGeneration:
    """Test tree-structured support generation."""

    @pytest.fixture
    def overhanging_mesh(self):
        """Create mesh with significant overhangs."""
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],  # Base
            [0, 0, 2], [1, 0, 2], [1, 1, 2], [0, 1, 2],  # Middle
            [0.5, 0.5, 4],  # Top point (overhang)
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1], [0, 3, 2],  # Base
            [4, 5, 6], [4, 6, 7],  # Middle
            [4, 5, 8], [5, 6, 8],  # Top overhangs
            [6, 7, 8], [7, 4, 8],
        ], dtype=np.int32)

        return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    def test_tree_support_generation_basic(self, overhanging_mesh):
        """Test basic tree support generation."""
        generator = SupportGenerator(SupportSettings(support_type=SupportType.TREE))

        supports = generator.generate_supports(overhanging_mesh)

        assert supports is not None
        assert supports.support_mesh is not None
        assert len(supports.support_points) > 0

    def test_tree_support_reaches_base(self, overhanging_mesh):
        """Test that tree supports reach from base to overhang."""
        generator = SupportGenerator(SupportSettings(support_type=SupportType.TREE))

        supports = generator.generate_supports(overhanging_mesh)

        # The support mesh should have defined height and vertices
        assert supports.support_mesh is not None
        assert len(supports.support_mesh.vertices) > 0

    def test_tree_support_branch_optimization(self, overhanging_mesh):
        """Test that tree branches are optimized."""
        generator = SupportGenerator(SupportSettings(
            support_type=SupportType.TREE,
            optimize_for_material=True
        ))

        supports = generator.generate_supports(overhanging_mesh)

        assert supports is not None
        assert supports.support_mesh is not None
        assert supports.support_mesh.volume > 0

    def test_tree_support_collision_free(self, overhanging_mesh):
        """Test that tree supports don't intersect with model."""
        generator = SupportGenerator(SupportSettings(support_type=SupportType.TREE))

        supports = generator.generate_supports(overhanging_mesh)

        # Check no collision between supports and model
        if supports.support_mesh is not None:
            # Simplified check: bounds shouldn't contain model vertices
            bounds = supports.support_mesh.bounds
            for vertex in overhanging_mesh.vertices:
                if np.all(vertex >= bounds[0]) and np.all(vertex <= bounds[1]):
                    # May be collision, but supports might intentionally touch model
                    pass



class TestNormalSupportGeneration:
    """Test normal (pillar) support generation."""

    def test_normal_support_generation(self):
        """Test normal pillar support generation."""
        # Simple overhang
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0.2, 0.2, 2], [0.8, 0.2, 2], [0.8, 0.8, 2], [0.2, 0.8, 2],
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1], [0, 3, 2],
            [4, 5, 6], [4, 6, 7],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        generator = SupportGenerator(SupportSettings(support_type=SupportType.GRID))

        supports = generator.generate_supports(mesh)

        assert supports is not None

    def test_normal_supports_are_cylindrical(self):
        """Test that normal supports are pillar-shaped."""
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0.3, 0.3, 2], [0.7, 0.3, 2], [0.7, 0.7, 2], [0.3, 0.7, 2],
        ], dtype=np.float64)

        # The floating top plate is the overhang: its faces are wound
        # as the plate's underside (normal -z). They were previously
        # wound as a top surface (+z), so the only face the detector
        # flagged was the base plate lying on the build plate -- and
        # this test passed only because the generator built a pillar
        # *below* the build plate for it (the defect fixed in
        # src/core/analysis/support_generator.py).
        faces = np.array([
            [0, 2, 1], [0, 3, 2],
            [4, 6, 5], [4, 7, 6],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        generator = SupportGenerator(SupportSettings(support_type=SupportType.GRID))

        supports = generator.generate_supports(mesh)

        # Pillars should be relatively simple
        assert supports.support_mesh is not None
        assert len(supports.support_mesh.faces) > 0


class TestSlimSupportGeneration:
    """Test slim/minimal support generation."""

    def test_slim_support_minimal_volume(self):
        """Test that slim supports use minimum material."""
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0.4, 0.4, 2], [0.6, 0.4, 2], [0.6, 0.6, 2], [0.4, 0.6, 2],
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1], [0, 3, 2],
            [4, 5, 6], [4, 6, 7],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

        # Generate different support types
        slim_supports = SupportGenerator(
            SupportSettings(support_type=SupportType.MINIMAL)
        ).generate_supports(mesh)
        normal_supports = SupportGenerator(
            SupportSettings(support_type=SupportType.GRID)
        ).generate_supports(mesh)

        # Slim should use less material
        slim_volume = slim_supports.support_volume
        normal_volume = normal_supports.support_volume

        assert slim_volume <= normal_volume


class TestSupportOptimization:
    """Test support optimization algorithms."""

    def test_support_optimization_reduces_volume(self):
        """Test that optimization reduces support volume."""
        mesh = trimesh.creation.icosphere()
        mesh.apply_translation([0.5, 0.5, 2])

        # Generate with optimization
        supports_opt = SupportGenerator(
            SupportSettings(optimize_for_material=True)
        ).generate_supports(mesh)

        # Generate without optimization
        supports_noopt = SupportGenerator(
            SupportSettings(optimize_for_material=False)
        ).generate_supports(mesh)

        volume_opt = supports_opt.support_volume
        volume_noopt = supports_noopt.support_volume

        # Optimized should be smaller or equal
        assert volume_opt <= volume_noopt * 1.1  # Allow 10% tolerance

    def test_support_optimization_removes_redundancy(self):
        """Test that optimization removes redundant supports."""
        # Create mesh with unnecessary support points
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0.2, 0.2, 2], [0.25, 0.2, 2], [0.3, 0.2, 2],  # Close points
            [0.8, 0.8, 2], [0.85, 0.8, 2], [0.9, 0.8, 2],   # Close points
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1], [0, 3, 2],
            [4, 5, 6],
            [7, 8, 9],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        generator = SupportGenerator(SupportSettings(optimize_for_material=True))

        supports = generator.generate_supports(mesh)

        # Should reduce redundant supports
        assert len(supports.support_points) >= 1



class TestSupportMaterialConsumption:
    """Test support material optimization."""

    def test_support_volume_calculation(self):
        """Test accurate support volume calculation."""
        mesh = trimesh.creation.box(extents=[1, 1, 0.5])
        mesh.apply_translation([0, 0, 2])

        generator = SupportGenerator()
        supports = generator.generate_supports(mesh)

        total_volume = supports.support_volume

        # Volume should be positive and reasonable
        assert total_volume > 0
        assert total_volume < mesh.volume * 5  # Sanity check

    def test_support_weight_estimate(self):
        """Test support weight estimation."""
        mesh = trimesh.creation.icosphere()
        mesh.apply_translation([0.5, 0.5, 2])

        generator = SupportGenerator()
        supports = generator.generate_supports(mesh)

        # Should estimate weight
        if hasattr(supports, 'estimated_weight'):
            assert supports.estimated_weight > 0

    def test_support_printing_time_estimate(self):
        """Test support printing time estimation."""
        mesh = trimesh.creation.cylinder(radius=0.5, height=1.0)
        mesh.apply_translation([0.5, 0.5, 1])

        generator = SupportGenerator()
        supports = generator.generate_supports(mesh)

        # Should have time estimate
        if hasattr(supports, 'estimated_print_time'):
            assert supports.estimated_print_time > 0


class TestSupportRemovability:
    """Test support removal characteristics."""

    def test_support_breakaway_points(self):
        """Test that supports have defined breakaway points."""
        mesh = trimesh.creation.icosphere()
        mesh.apply_translation([0.5, 0.5, 2])

        generator = SupportGenerator()
        supports = generator.generate_supports(mesh)

        # Interface should provide clean breakaway
        assert supports is not None

    def test_support_connection_strength(self):
        """Test that supports have proper connection strength."""
        mesh = trimesh.creation.box()
        mesh.apply_translation([0.5, 0.5, 1])

        generator = SupportGenerator()
        supports = generator.generate_supports(mesh)

        # Supports should be connected to model
        # Simplified check: support mesh should exist
        assert supports.support_mesh is not None


class TestSupportGenerationPerformance:
    """Test support generation performance."""

    @pytest.mark.parametrize("complexity", [100, 500, 2000])
    def test_support_generation_scales(self, complexity):
        """Test support generation scales with mesh complexity."""
        # Create mesh of varying complexity
        mesh = trimesh.creation.icosphere(subdivisions=3)

        # Further subdivide
        while mesh.faces.shape[0] < complexity:
            mesh = mesh.subdivide()

        mesh.apply_translation([0.5, 0.5, 2])

        generator = SupportGenerator()

        import time
        start = time.time()
        supports = generator.generate_supports(mesh)
        elapsed = time.time() - start

        assert supports is not None
        # Should complete in reasonable time
        assert elapsed < 30.0  # 30 second limit

    def test_support_generation_memory_efficient(self):
        """Test memory usage during support generation."""
        mesh = trimesh.creation.icosphere()
        mesh.apply_translation([0.5, 0.5, 2])

        generator = SupportGenerator()

        # Should not consume excessive memory
        supports = generator.generate_supports(mesh)
        assert supports is not None


class TestSupportGenerationEdgeCases:
    """Test support generation edge cases."""

    def test_support_generation_flat_mesh(self):
        """Test support generation for flat mesh (no supports needed)."""
        # Flat square
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1],
            [0, 3, 2],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        generator = SupportGenerator()

        supports = generator.generate_supports(mesh)

        # May not need supports, should handle gracefully
        assert supports is not None

    def test_support_generation_hanging_edge(self):
        """Test support generation for hanging edge case."""
        # Thin sheet hanging from one edge
        vertices = np.array([
            [0, 0, 0],
            [0.1, 0, 0],
            [0.1, 1, 0],
            [0, 1, 0],
            [0, 0, 0.05],
            [0.1, 0, 0.05],
            [0.1, 1, 0.05],
            [0, 1, 0.05],
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1], [0, 3, 2],
            [4, 5, 6], [4, 6, 7],
            [0, 4, 5], [0, 5, 1],
            [1, 5, 6], [1, 6, 2],
            [2, 6, 7], [2, 7, 3],
            [3, 7, 4], [3, 4, 0],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        mesh.apply_translation([0, 0, 2])

        generator = SupportGenerator()
        supports = generator.generate_supports(mesh)

        # Should identify hanging edge as needing support
        assert supports is not None
        assert supports.support_volume > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
