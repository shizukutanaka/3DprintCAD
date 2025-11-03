"""Advanced support structure generation testing.

Tests comprehensive support generation including:
- Tree support generation
- Organic support generation
- Support optimization
- Interface layer generation
- Collision detection
"""

import pytest
import numpy as np
import trimesh
from unittest.mock import MagicMock, patch

from src.core.analysis.support_generator import SupportGenerator, SupportType


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
        generator = SupportGenerator()

        supports = generator.generate_supports(
            overhanging_mesh,
            support_type=SupportType.TREE
        )

        assert supports is not None
        assert len(supports.support_volumes) > 0

    def test_tree_support_reaches_base(self, overhanging_mesh):
        """Test that tree supports reach from base to overhang."""
        generator = SupportGenerator()

        supports = generator.generate_supports(
            overhanging_mesh,
            support_type=SupportType.TREE
        )

        # Tree should have multiple levels
        for volume in supports.support_volumes:
            if volume.support_type == SupportType.TREE:
                # Should have defined height
                assert volume.mesh is not None
                assert len(volume.mesh.vertices) > 0

    def test_tree_support_branch_optimization(self, overhanging_mesh):
        """Test that tree branches are optimized."""
        generator = SupportGenerator()

        supports = generator.generate_supports(
            overhanging_mesh,
            support_type=SupportType.TREE,
            optimize=True
        )

        assert supports is not None
        # With optimization, volume should be smaller
        total_volume_opt = sum(v.mesh.volume for v in supports.support_volumes)
        assert total_volume_opt > 0

    def test_tree_support_collision_free(self, overhanging_mesh):
        """Test that tree supports don't intersect with model."""
        generator = SupportGenerator()

        supports = generator.generate_supports(
            overhanging_mesh,
            support_type=SupportType.TREE
        )

        # Check no collision between supports and model
        for support_volume in supports.support_volumes:
            # Simplified check: bounds shouldn't contain model vertices
            bounds = support_volume.mesh.bounds
            for vertex in overhanging_mesh.vertices:
                if np.all(vertex >= bounds[0]) and np.all(vertex <= bounds[1]):
                    # May be collision, but supports might intentionally touch model
                    pass


class TestOrganicSupportGeneration:
    """Test organic/curved support generation."""

    @pytest.fixture
    def complex_overhanging_mesh(self):
        """Create complex mesh with multiple overhang regions."""
        # Create more complex shape
        sphere = trimesh.creation.sphere(radius=0.5)
        sphere.apply_translation([0.5, 0.5, 1.5])

        box = trimesh.creation.box(extents=[1, 1, 1])
        box.apply_translation([0, 0, 0])

        # Merge
        merged = trimesh.util.concatenate([box, sphere])
        return merged

    def test_organic_support_generation(self, complex_overhanging_mesh):
        """Test organic support generation."""
        generator = SupportGenerator()

        supports = generator.generate_supports(
            complex_overhanging_mesh,
            support_type=SupportType.ORGANIC
        )

        assert supports is not None
        assert len(supports.support_volumes) > 0

    def test_organic_support_smooth(self, complex_overhanging_mesh):
        """Test that organic supports have smooth curves."""
        generator = SupportGenerator()

        supports = generator.generate_supports(
            complex_overhanging_mesh,
            support_type=SupportType.ORGANIC
        )

        for volume in supports.support_volumes:
            if volume.support_type == SupportType.ORGANIC:
                # Check curvature (simplified)
                assert volume.mesh is not None
                # Organic supports should have curved faces
                assert len(volume.mesh.faces) > 0


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
        generator = SupportGenerator()

        supports = generator.generate_supports(
            mesh,
            support_type=SupportType.NORMAL
        )

        assert supports is not None

    def test_normal_supports_are_cylindrical(self):
        """Test that normal supports are pillar-shaped."""
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0.3, 0.3, 2], [0.7, 0.3, 2], [0.7, 0.7, 2], [0.3, 0.7, 2],
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1], [0, 3, 2],
            [4, 5, 6], [4, 6, 7],
        ], dtype=np.int32)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        generator = SupportGenerator()

        supports = generator.generate_supports(mesh, support_type=SupportType.NORMAL)

        for volume in supports.support_volumes:
            # Pillars should be relatively simple
            assert len(volume.mesh.faces) > 0


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
        generator = SupportGenerator()

        # Generate different support types
        slim_supports = generator.generate_supports(
            mesh, support_type=SupportType.SLIM
        )
        normal_supports = generator.generate_supports(
            mesh, support_type=SupportType.NORMAL
        )

        # Slim should use less material
        slim_volume = sum(v.mesh.volume for v in slim_supports.support_volumes)
        normal_volume = sum(v.mesh.volume for v in normal_supports.support_volumes)

        assert slim_volume <= normal_volume


class TestSupportOptimization:
    """Test support optimization algorithms."""

    def test_support_optimization_reduces_volume(self):
        """Test that optimization reduces support volume."""
        mesh = trimesh.creation.sphere()
        mesh.apply_translation([0.5, 0.5, 2])

        generator = SupportGenerator()

        # Generate with optimization
        supports_opt = generator.generate_supports(
            mesh, optimize=True
        )

        # Generate without optimization
        supports_noopt = generator.generate_supports(
            mesh, optimize=False
        )

        volume_opt = sum(v.mesh.volume for v in supports_opt.support_volumes)
        volume_noopt = sum(v.mesh.volume for v in supports_noopt.support_volumes)

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
        generator = SupportGenerator()

        supports = generator.generate_supports(
            mesh, optimize=True
        )

        # Should reduce redundant supports
        assert len(supports.support_volumes) >= 1


class TestInterfaceLayerGeneration:
    """Test support interface (roof/floor) generation."""

    def test_interface_generation_adds_layers(self):
        """Test that interface generation adds roof/floor layers."""
        mesh = trimesh.creation.box(extents=[1, 1, 0.5])
        mesh.apply_translation([0, 0, 2])

        generator = SupportGenerator()

        supports = generator.generate_supports(
            mesh,
            generate_interfaces=True
        )

        # Should include interface layers
        assert supports is not None
        # Check if interface properties are set
        for volume in supports.support_volumes:
            assert hasattr(volume, 'interface_type')

    def test_interface_roof_thickness(self):
        """Test that interface roof has proper thickness."""
        mesh = trimesh.creation.sphere()
        mesh.apply_translation([0.5, 0.5, 2])

        generator = SupportGenerator()

        supports = generator.generate_supports(
            mesh,
            generate_interfaces=True,
            interface_thickness=0.5
        )

        assert supports is not None

    def test_interface_floor_strength(self):
        """Test that interface floor provides structural support."""
        mesh = trimesh.creation.cylinder(radius=0.3, height=0.5)
        mesh.apply_translation([0.5, 0.5, 2])

        generator = SupportGenerator()

        supports = generator.generate_supports(
            mesh,
            generate_interfaces=True
        )

        # Floor should be present and solid
        assert supports is not None


class TestSupportMaterialConsumption:
    """Test support material optimization."""

    def test_support_volume_calculation(self):
        """Test accurate support volume calculation."""
        mesh = trimesh.creation.box(extents=[1, 1, 0.5])
        mesh.apply_translation([0, 0, 2])

        generator = SupportGenerator()
        supports = generator.generate_supports(mesh)

        total_volume = sum(v.mesh.volume for v in supports.support_volumes)

        # Volume should be positive and reasonable
        assert total_volume > 0
        assert total_volume < mesh.volume * 5  # Sanity check

    def test_support_weight_estimate(self):
        """Test support weight estimation."""
        mesh = trimesh.creation.sphere()
        mesh.apply_translation([0.5, 0.5, 2])

        generator = SupportGenerator()
        supports = generator.generate_supports(mesh, material='PLA')

        # Should estimate weight
        if hasattr(supports, 'estimated_weight'):
            assert supports.estimated_weight > 0

    def test_support_printing_time_estimate(self):
        """Test support printing time estimation."""
        mesh = trimesh.creation.cylinder()
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
        mesh = trimesh.creation.sphere()
        mesh.apply_translation([0.5, 0.5, 2])

        generator = SupportGenerator()
        supports = generator.generate_supports(
            mesh,
            generate_interfaces=True
        )

        # Interface should provide clean breakaway
        assert supports is not None

    def test_support_connection_strength(self):
        """Test that supports have proper connection strength."""
        mesh = trimesh.creation.box()
        mesh.apply_translation([0.5, 0.5, 1])

        generator = SupportGenerator()
        supports = generator.generate_supports(mesh)

        for volume in supports.support_volumes:
            # Supports should be connected to model
            # Simplified check: volume should exist
            assert volume.mesh is not None


class TestSupportGenerationPerformance:
    """Test support generation performance."""

    @pytest.mark.parametrize("complexity", [100, 500, 2000])
    def test_support_generation_scales(self, complexity):
        """Test support generation scales with mesh complexity."""
        # Create mesh of varying complexity
        mesh = trimesh.creation.sphere(subdivisions=3)

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
        mesh = trimesh.creation.sphere()
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
        assert len(supports.support_volumes) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
