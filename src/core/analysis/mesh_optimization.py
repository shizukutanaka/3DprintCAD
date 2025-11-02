"""Advanced mesh optimization for 3D printing production quality."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging
import time

import numpy as np
import trimesh
from trimesh import smoothing, decimation
from scipy.spatial import KDTree
from scipy.optimize import minimize


class OptimizationGoal(Enum):
    """Goals for mesh optimization."""
    MINIMAL_SUPPORTS = "minimal_supports"
    MAXIMUM_STRENGTH = "maximum_strength"
    FASTEST_PRINT = "fastest_print"
    BEST_QUALITY = "best_quality"
    MINIMAL_MATERIAL = "minimal_material"
    BALANCED = "balanced"


@dataclass
class OptimizationSettings:
    """Settings for mesh optimization."""
    goal: OptimizationGoal = OptimizationGoal.BALANCED
    preserve_features: bool = True
    feature_threshold_mm: float = 0.5
    max_decimation_ratio: float = 0.5
    smoothing_iterations: int = 5
    smoothing_lambda: float = 0.5
    allow_topology_changes: bool = False
    target_face_count: Optional[int] = None
    min_face_quality: float = 0.3
    max_edge_length_mm: float = 10.0
    min_edge_length_mm: float = 0.1
    preserve_boundaries: bool = True
    preserve_materials: bool = True


@dataclass
class OptimizationResult:
    """Result of mesh optimization."""
    success: bool
    optimized_mesh: Optional[trimesh.Trimesh]
    original_metrics: Dict[str, Any]
    optimized_metrics: Dict[str, Any]
    operations_performed: List[str]
    processing_time: float
    quality_score: float
    print_time_reduction: float
    material_reduction: float
    support_reduction: float


class MeshOptimizer:
    """Advanced mesh optimization engine for 3D printing."""

    def __init__(self, settings: OptimizationSettings = None):
        """
        Initialize the mesh optimizer.

        Args:
            settings: Optimization settings
        """
        self.settings = settings or OptimizationSettings()
        self.logger = logging.getLogger(__name__)

    def optimize_mesh(self, mesh: trimesh.Trimesh) -> OptimizationResult:
        """
        Optimize mesh for 3D printing based on specified goals.

        Args:
            mesh: Input mesh to optimize

        Returns:
            OptimizationResult with optimized mesh and metrics
        """
        start_time = time.time()
        operations_performed = []

        # Calculate original metrics
        original_metrics = self._calculate_metrics(mesh)

        # Create a copy for optimization
        optimized_mesh = mesh.copy()

        try:
            # Step 1: Clean and repair basic issues
            if self._should_clean_mesh():
                optimized_mesh = self._clean_mesh(optimized_mesh)
                operations_performed.append("mesh_cleaning")

            # Step 2: Optimize orientation based on goal
            if self.settings.goal in [OptimizationGoal.MINIMAL_SUPPORTS,
                                     OptimizationGoal.BALANCED,
                                     OptimizationGoal.FASTEST_PRINT]:
                optimized_mesh, orientation = self._optimize_orientation(optimized_mesh)
                operations_performed.append(f"orientation_optimization: {orientation}")

            # Step 3: Decimate if appropriate
            if self._should_decimate():
                optimized_mesh = self._decimate_mesh(optimized_mesh)
                operations_performed.append("mesh_decimation")

            # Step 4: Smooth mesh if quality is priority
            if self.settings.goal in [OptimizationGoal.BEST_QUALITY,
                                     OptimizationGoal.BALANCED]:
                optimized_mesh = self._smooth_mesh(optimized_mesh)
                operations_performed.append("mesh_smoothing")

            # Step 5: Optimize for specific goals
            if self.settings.goal == OptimizationGoal.MINIMAL_MATERIAL:
                optimized_mesh = self._optimize_for_material(optimized_mesh)
                operations_performed.append("material_optimization")
            elif self.settings.goal == OptimizationGoal.MAXIMUM_STRENGTH:
                optimized_mesh = self._optimize_for_strength(optimized_mesh)
                operations_performed.append("strength_optimization")

            # Step 6: Remesh if needed for quality
            if self._should_remesh(optimized_mesh):
                optimized_mesh = self._remesh(optimized_mesh)
                operations_performed.append("remeshing")

            # Step 7: Final validation and cleanup
            optimized_mesh = self._final_cleanup(optimized_mesh)
            operations_performed.append("final_cleanup")

            # Calculate optimized metrics
            optimized_metrics = self._calculate_metrics(optimized_mesh)

            # Calculate improvements
            quality_score = self._calculate_quality_score(optimized_mesh)
            print_time_reduction = self._calculate_print_time_reduction(
                original_metrics, optimized_metrics
            )
            material_reduction = self._calculate_material_reduction(
                original_metrics, optimized_metrics
            )
            support_reduction = self._calculate_support_reduction(
                original_metrics, optimized_metrics
            )

            processing_time = time.time() - start_time

            return OptimizationResult(
                success=True,
                optimized_mesh=optimized_mesh,
                original_metrics=original_metrics,
                optimized_metrics=optimized_metrics,
                operations_performed=operations_performed,
                processing_time=processing_time,
                quality_score=quality_score,
                print_time_reduction=print_time_reduction,
                material_reduction=material_reduction,
                support_reduction=support_reduction
            )

        except Exception as e:
            self.logger.error(f"Mesh optimization failed: {e}")
            processing_time = time.time() - start_time

            return OptimizationResult(
                success=False,
                optimized_mesh=None,
                original_metrics=original_metrics,
                optimized_metrics={},
                operations_performed=operations_performed,
                processing_time=processing_time,
                quality_score=0.0,
                print_time_reduction=0.0,
                material_reduction=0.0,
                support_reduction=0.0
            )

    def _should_clean_mesh(self) -> bool:
        """Determine if mesh cleaning is needed."""
        return True  # Always clean for production quality

    def _clean_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Clean mesh by removing duplicate vertices, degenerate faces, etc."""
        try:
            # Remove duplicate vertices
            mesh.merge_vertices()

            # Remove degenerate faces
            mesh.remove_degenerate_faces()

            # Remove duplicate faces
            mesh.remove_duplicate_faces()

            # Remove unreferenced vertices
            mesh.remove_unreferenced_vertices()

            # Fix normals
            mesh.fix_normals()

            return mesh
        except Exception as e:
            self.logger.warning(f"Mesh cleaning failed: {e}")
            return mesh

    def _optimize_orientation(self, mesh: trimesh.Trimesh) -> Tuple[trimesh.Trimesh, str]:
        """
        Optimize mesh orientation for printing.

        Returns:
            Tuple of (optimized mesh, orientation description)
        """
        best_orientation = None
        best_score = float('inf')
        best_rotation = np.eye(4)

        # Test multiple orientations
        test_orientations = [
            (0, 0, 0),      # Original
            (90, 0, 0),     # X-axis rotation
            (0, 90, 0),     # Y-axis rotation
            (0, 0, 90),     # Z-axis rotation
            (45, 0, 0),     # 45° X
            (0, 45, 0),     # 45° Y
            (45, 45, 0),    # Combined
        ]

        for rx, ry, rz in test_orientations:
            # Create rotation matrix
            rotation = trimesh.transformations.euler_matrix(
                np.radians(rx), np.radians(ry), np.radians(rz)
            )

            # Apply rotation
            test_mesh = mesh.copy()
            test_mesh.apply_transform(rotation)

            # Calculate score based on goal
            score = self._calculate_orientation_score(test_mesh)

            if score < best_score:
                best_score = score
                best_rotation = rotation
                best_orientation = f"rx={rx}, ry={ry}, rz={rz}"

        # Apply best orientation
        optimized_mesh = mesh.copy()
        optimized_mesh.apply_transform(best_rotation)

        return optimized_mesh, best_orientation

    def _calculate_orientation_score(self, mesh: trimesh.Trimesh) -> float:
        """Calculate orientation score based on optimization goal."""
        score = 0.0

        if self.settings.goal == OptimizationGoal.MINIMAL_SUPPORTS:
            # Minimize overhanging area
            overhang_area = self._calculate_overhang_area(mesh)
            score += overhang_area * 10.0

        elif self.settings.goal == OptimizationGoal.FASTEST_PRINT:
            # Minimize Z-height for faster printing
            z_height = mesh.extents[2]
            score += z_height * 5.0

        elif self.settings.goal == OptimizationGoal.MAXIMUM_STRENGTH:
            # Optimize for layer orientation strength
            # Layers perpendicular to load direction are stronger
            score += self._calculate_strength_score(mesh)

        else:  # BALANCED
            # Balance multiple factors
            overhang_area = self._calculate_overhang_area(mesh)
            z_height = mesh.extents[2]
            bed_area = self._calculate_bed_contact_area(mesh)

            score = (overhang_area * 5.0 +
                    z_height * 2.0 +
                    (1000.0 / max(bed_area, 1.0)))  # Maximize bed contact

        return score

    def _calculate_overhang_area(self, mesh: trimesh.Trimesh) -> float:
        """Calculate total area requiring supports."""
        try:
            overhang_threshold = np.radians(self.settings.feature_threshold_mm)
            overhang_area = 0.0

            for i, normal in enumerate(mesh.face_normals):
                # Check if face points downward beyond threshold
                z_component = normal[2]
                if z_component < -np.cos(overhang_threshold):
                    overhang_area += mesh.area_faces[i]

            return overhang_area
        except:
            return 0.0

    def _calculate_bed_contact_area(self, mesh: trimesh.Trimesh) -> float:
        """Calculate contact area with build plate."""
        try:
            z_min = mesh.vertices[:, 2].min()
            threshold = 0.1  # mm tolerance

            bed_faces = []
            for i, face in enumerate(mesh.faces):
                face_vertices = mesh.vertices[face]
                if np.all(np.abs(face_vertices[:, 2] - z_min) < threshold):
                    bed_faces.append(i)

            return sum(mesh.area_faces[i] for i in bed_faces)
        except:
            return 0.0

    def _calculate_strength_score(self, mesh: trimesh.Trimesh) -> float:
        """Calculate strength score based on layer orientation."""
        # Simplified: prefer orientations where critical features are not parallel to layers
        # Lower score is better
        score = 0.0

        # Analyze face orientations relative to Z-axis (layer direction)
        for normal in mesh.face_normals:
            # Faces parallel to layers (horizontal) are weaker
            horizontal_component = abs(normal[2])
            score += (1.0 - horizontal_component)  # Penalize horizontal faces

        return score / len(mesh.face_normals)

    def _should_decimate(self) -> bool:
        """Determine if decimation is appropriate."""
        return (self.settings.goal in [OptimizationGoal.FASTEST_PRINT,
                                      OptimizationGoal.MINIMAL_MATERIAL] or
                self.settings.target_face_count is not None)

    def _decimate_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Reduce mesh complexity while preserving features."""
        try:
            target_faces = self.settings.target_face_count
            if target_faces is None:
                # Calculate based on decimation ratio
                target_faces = int(len(mesh.faces) * (1.0 - self.settings.max_decimation_ratio))

            # Use quadric decimation for better feature preservation
            decimated = mesh.simplify_quadric_decimation(target_faces)

            # Verify quality
            if self._verify_mesh_quality(decimated):
                return decimated
            else:
                self.logger.warning("Decimation reduced quality too much, using original")
                return mesh

        except Exception as e:
            self.logger.warning(f"Decimation failed: {e}")
            return mesh

    def _smooth_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Apply smoothing to improve surface quality."""
        try:
            # Apply Laplacian smoothing
            smooth_mesh = mesh.copy()

            for _ in range(self.settings.smoothing_iterations):
                # Get vertex neighbors for Laplacian smoothing
                vertices = smooth_mesh.vertices.copy()

                # Simple Laplacian smoothing
                for i in range(len(vertices)):
                    # Find neighboring vertices
                    neighbors = []
                    for face in smooth_mesh.faces:
                        if i in face:
                            for v in face:
                                if v != i and v not in neighbors:
                                    neighbors.append(v)

                    if neighbors and not self._is_boundary_vertex(smooth_mesh, i):
                        # Average neighbor positions
                        neighbor_positions = smooth_mesh.vertices[neighbors]
                        new_position = (
                            (1 - self.settings.smoothing_lambda) * vertices[i] +
                            self.settings.smoothing_lambda * np.mean(neighbor_positions, axis=0)
                        )
                        smooth_mesh.vertices[i] = new_position

            return smooth_mesh

        except Exception as e:
            self.logger.warning(f"Smoothing failed: {e}")
            return mesh

    def _is_boundary_vertex(self, mesh: trimesh.Trimesh, vertex_index: int) -> bool:
        """Check if vertex is on mesh boundary."""
        if not self.settings.preserve_boundaries:
            return False

        try:
            # Check if vertex is part of any boundary edge
            edges = mesh.edges_unique
            edge_counts = np.bincount(mesh.edges_unique_inverse)
            boundary_edges = edges[edge_counts == 1]

            for edge in boundary_edges:
                if vertex_index in edge:
                    return True
            return False
        except:
            return False

    def _optimize_for_material(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Optimize mesh to minimize material usage."""
        # This would involve hollowing, lattice generation, etc.
        # For now, return decimated version
        return self._decimate_mesh(mesh)

    def _optimize_for_strength(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Optimize mesh for structural strength."""
        # This would involve thickening critical areas, adding ribs, etc.
        # For now, return original
        return mesh

    def _should_remesh(self, mesh: trimesh.Trimesh) -> bool:
        """Determine if remeshing is needed."""
        try:
            # Check face quality metrics
            edge_lengths = []
            for face in mesh.faces:
                v0, v1, v2 = mesh.vertices[face]
                edge_lengths.extend([
                    np.linalg.norm(v1 - v0),
                    np.linalg.norm(v2 - v1),
                    np.linalg.norm(v0 - v2)
                ])

            edge_lengths = np.array(edge_lengths)
            min_edge = np.min(edge_lengths)
            max_edge = np.max(edge_lengths)

            # Remesh if edge length variation is too high
            return (max_edge / min_edge > 10.0 or
                   max_edge > self.settings.max_edge_length_mm or
                   min_edge < self.settings.min_edge_length_mm)
        except:
            return False

    def _remesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Remesh to improve triangle quality."""
        try:
            # Subdivide large faces
            target_edge_length = (self.settings.max_edge_length_mm +
                                 self.settings.min_edge_length_mm) / 2.0

            # Simple subdivision approach
            # In production, use more sophisticated remeshing algorithms
            return mesh.subdivide_to_size(target_edge_length, max_iter=3)
        except:
            return mesh

    def _final_cleanup(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Final cleanup and validation."""
        try:
            # Ensure watertightness
            if not mesh.is_watertight:
                mesh.fill_holes()

            # Fix normals
            mesh.fix_normals()

            # Remove any new duplicate vertices
            mesh.merge_vertices()

            return mesh
        except:
            return mesh

    def _verify_mesh_quality(self, mesh: trimesh.Trimesh) -> bool:
        """Verify mesh meets quality standards."""
        try:
            # Check basic quality metrics
            if not mesh.is_valid:
                return False

            if len(mesh.faces) < 4:  # Minimum faces for valid 3D object
                return False

            # Check face quality
            for face in mesh.faces:
                vertices = mesh.vertices[face]
                # Calculate face area
                v0, v1, v2 = vertices
                area = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0))
                if area < 1e-6:  # Degenerate face
                    return False

            return True
        except:
            return False

    def _calculate_metrics(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Calculate comprehensive mesh metrics."""
        metrics = {}

        try:
            metrics['face_count'] = len(mesh.faces)
            metrics['vertex_count'] = len(mesh.vertices)
            metrics['edge_count'] = len(mesh.edges_unique)
            metrics['volume'] = mesh.volume if mesh.is_volume else 0.0
            metrics['surface_area'] = mesh.area
            metrics['bounding_box'] = mesh.extents.tolist()
            metrics['is_watertight'] = mesh.is_watertight
            metrics['is_manifold'] = mesh.is_winding_consistent
            metrics['components'] = len(mesh.split())

            # Calculate overhang area
            metrics['overhang_area'] = self._calculate_overhang_area(mesh)

            # Calculate bed contact area
            metrics['bed_contact_area'] = self._calculate_bed_contact_area(mesh)

            # Calculate face quality distribution
            face_qualities = []
            for face in mesh.faces:
                vertices = mesh.vertices[face]
                # Simple quality metric: aspect ratio
                edges = [
                    np.linalg.norm(vertices[1] - vertices[0]),
                    np.linalg.norm(vertices[2] - vertices[1]),
                    np.linalg.norm(vertices[0] - vertices[2])
                ]
                quality = min(edges) / max(edges) if max(edges) > 0 else 0
                face_qualities.append(quality)

            metrics['avg_face_quality'] = np.mean(face_qualities) if face_qualities else 0.0
            metrics['min_face_quality'] = np.min(face_qualities) if face_qualities else 0.0

        except Exception as e:
            self.logger.warning(f"Metric calculation failed: {e}")

        return metrics

    def _calculate_quality_score(self, mesh: trimesh.Trimesh) -> float:
        """Calculate overall quality score (0-100)."""
        score = 100.0

        try:
            # Penalize for non-watertight
            if not mesh.is_watertight:
                score -= 20.0

            # Penalize for non-manifold
            if not mesh.is_winding_consistent:
                score -= 15.0

            # Penalize for poor face quality
            metrics = self._calculate_metrics(mesh)
            avg_quality = metrics.get('avg_face_quality', 0.5)
            score -= (1.0 - avg_quality) * 20.0

            # Penalize for excessive faces
            if len(mesh.faces) > 100000:
                score -= 10.0

            # Penalize for minimal bed contact
            bed_area = metrics.get('bed_contact_area', 0.0)
            if bed_area < 100.0:  # mm²
                score -= 10.0

            return max(0.0, min(100.0, score))

        except:
            return 50.0

    def _calculate_print_time_reduction(self, original: Dict, optimized: Dict) -> float:
        """Calculate estimated print time reduction percentage."""
        try:
            # Simple estimation based on volume and height
            original_time = (original.get('volume', 1.0) * 0.01 +
                           original.get('bounding_box', [0, 0, 100])[2] * 0.5)
            optimized_time = (optimized.get('volume', 1.0) * 0.01 +
                            optimized.get('bounding_box', [0, 0, 100])[2] * 0.5)

            if original_time > 0:
                reduction = (original_time - optimized_time) / original_time * 100
                return max(0.0, reduction)
            return 0.0
        except:
            return 0.0

    def _calculate_material_reduction(self, original: Dict, optimized: Dict) -> float:
        """Calculate material usage reduction percentage."""
        try:
            original_volume = original.get('volume', 0.0)
            optimized_volume = optimized.get('volume', 0.0)

            if original_volume > 0:
                reduction = (original_volume - optimized_volume) / original_volume * 100
                return max(0.0, reduction)
            return 0.0
        except:
            return 0.0

    def _calculate_support_reduction(self, original: Dict, optimized: Dict) -> float:
        """Calculate support material reduction percentage."""
        try:
            original_overhang = original.get('overhang_area', 0.0)
            optimized_overhang = optimized.get('overhang_area', 0.0)

            if original_overhang > 0:
                reduction = (original_overhang - optimized_overhang) / original_overhang * 100
                return max(0.0, reduction)
            return 0.0
        except:
            return 0.0


def optimize_mesh(mesh: trimesh.Trimesh,
                 goal: OptimizationGoal = OptimizationGoal.BALANCED,
                 settings: OptimizationSettings = None) -> OptimizationResult:
    """
    Convenience function for mesh optimization.

    Args:
        mesh: Input mesh to optimize
        goal: Optimization goal
        settings: Optional optimization settings

    Returns:
        OptimizationResult with optimized mesh
    """
    if settings is None:
        settings = OptimizationSettings(goal=goal)
    else:
        settings.goal = goal

    optimizer = MeshOptimizer(settings)
    return optimizer.optimize_mesh(mesh)