"""Dynamic support structure generation for 3D printing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging
import time
import numpy as np
import trimesh
from scipy.spatial import KDTree
from scipy.spatial.distance import cdist


class SupportType(Enum):
    """Types of support structures."""
    TREE = "tree"
    GRID = "grid"
    CONTOUR = "contour"
    ADAPTIVE = "adaptive"
    MINIMAL = "minimal"


class SupportPattern(Enum):
    """Support pattern styles."""
    LINES = "lines"
    HONEYCOMB = "honeycomb"
    TRIANGULAR = "triangular"
    RECTANGULAR = "rectangular"
    CIRCULAR = "circular"


@dataclass
class SupportSettings:
    """Settings for support generation."""
    support_type: SupportType = SupportType.ADAPTIVE
    pattern: SupportPattern = SupportPattern.HONEYCOMB
    support_angle: float = 45.0  # degrees
    support_density: float = 0.3  # 0.0 to 1.0
    support_spacing: float = 2.0  # mm
    support_thickness: float = 0.8  # mm
    support_overhang: float = 1.0  # mm
    contact_area: float = 0.5  # mm²
    remove_overhang: bool = True
    optimize_for_material: bool = True
    optimize_for_speed: bool = False


@dataclass
class SupportResult:
    """Result of support generation."""
    success: bool
    support_mesh: Optional[trimesh.Trimesh]
    support_points: List[np.ndarray]
    support_volume: float
    support_area: float
    overhang_area: float
    generation_time: float
    operations_performed: List[str]


class SupportGenerator:
    """Dynamic support structure generator for 3D printing."""

    def __init__(self, settings: SupportSettings = None):
        """
        Initialize the support generator.

        Args:
            settings: Support generation settings
        """
        self.settings = settings or SupportSettings()
        self.logger = logging.getLogger(__name__)

    def generate_supports(self, mesh: trimesh.Trimesh) -> SupportResult:
        """
        Generate support structures for the mesh.

        Args:
            mesh: Input mesh requiring supports

        Returns:
            SupportResult with generated support structures
        """
        start_time = time.time()
        operations_performed = []

        try:
            # Step 1: Analyze overhangs
            overhang_faces, overhang_normals = self._analyze_overhangs(mesh)
            operations_performed.append("overhang_analysis")

            if len(overhang_faces) == 0:
                # No supports needed
                return SupportResult(
                    success=True,
                    support_mesh=None,
                    support_points=[],
                    support_volume=0.0,
                    support_area=0.0,
                    overhang_area=0.0,
                    generation_time=time.time() - start_time,
                    operations_performed=operations_performed
                )

            # Step 2: Generate support points
            support_points = self._generate_support_points(mesh, overhang_faces, overhang_normals)
            operations_performed.append("support_point_generation")

            # Step 3: Create support structures
            support_mesh = self._create_support_mesh(mesh, support_points)
            operations_performed.append("support_mesh_creation")

            # Step 4: Optimize supports if requested
            if self.settings.optimize_for_material or self.settings.optimize_for_speed:
                support_mesh = self._optimize_supports(support_mesh)
                operations_performed.append("support_optimization")

            # Step 5: Calculate metrics
            support_volume = self._calculate_volume(support_mesh) if support_mesh else 0.0
            support_area = self._calculate_area(support_mesh) if support_mesh else 0.0
            overhang_area = sum(mesh.area_faces[i] for i in overhang_faces)

            generation_time = time.time() - start_time

            return SupportResult(
                success=True,
                support_mesh=support_mesh,
                support_points=support_points,
                support_volume=support_volume,
                support_area=support_area,
                overhang_area=overhang_area,
                generation_time=generation_time,
                operations_performed=operations_performed
            )

        except Exception as e:
            self.logger.error(f"Support generation failed: {e}")
            generation_time = time.time() - start_time

            return SupportResult(
                success=False,
                support_mesh=None,
                support_points=[],
                support_volume=0.0,
                support_area=0.0,
                overhang_area=0.0,
                generation_time=generation_time,
                operations_performed=operations_performed
            )

    def _analyze_overhangs(self, mesh: trimesh.Trimesh) -> Tuple[List[int], List[np.ndarray]]:
        """Analyze mesh for overhangs requiring supports."""
        overhang_faces = []
        overhang_normals = []

        # Convert support angle to radians
        support_angle_rad = np.radians(self.settings.support_angle)

        for i, normal in enumerate(mesh.face_normals):
            # Check if face normal is pointing downward beyond support angle
            z_component = normal[2]
            angle_from_vertical = np.arccos(max(-1.0, min(1.0, z_component)))

            if angle_from_vertical > support_angle_rad:
                overhang_faces.append(i)
                overhang_normals.append(normal)

        return overhang_faces, overhang_normals

    def _generate_support_points(self, mesh: trimesh.Trimesh,
                               overhang_faces: List[int],
                               overhang_normals: List[np.ndarray]) -> List[np.ndarray]:
        """Generate support contact points on overhang areas."""
        support_points = []

        for face_idx in overhang_faces:
            face = mesh.faces[face_idx]
            vertices = mesh.vertices[face]

            # Calculate face centroid as support point
            centroid = np.mean(vertices, axis=0)

            # Project point downward to find support contact
            # For now, place support at centroid height minus support thickness
            support_point = centroid.copy()
            support_point[2] = centroid[2] - self.settings.support_thickness

            # Ensure support point is below the overhang
            min_z = min(vertices[:, 2])
            if support_point[2] < min_z - self.settings.support_thickness:
                support_point[2] = min_z - self.settings.support_thickness

            support_points.append(support_point)

        # Remove duplicate points and cluster nearby points
        if support_points:
            support_points = self._cluster_support_points(support_points)

        return support_points

    def _cluster_support_points(self, points: List[np.ndarray]) -> List[np.ndarray]:
        """Cluster nearby support points to reduce redundancy."""
        if not points:
            return points

        points_array = np.array(points)
        clustered_points = []

        # Simple clustering based on distance threshold
        threshold = self.settings.support_spacing * 0.5

        remaining_indices = list(range(len(points_array)))

        while remaining_indices:
            # Start with first remaining point
            current_idx = remaining_indices[0]
            current_point = points_array[current_idx]

            # Find nearby points
            distances = cdist([current_point], points_array[remaining_indices])
            nearby_indices = [remaining_indices[i] for i in range(len(distances[0]))
                            if distances[0][i] <= threshold]

            # Average nearby points
            cluster_points = points_array[nearby_indices]
            cluster_center = np.mean(cluster_points, axis=0)

            clustered_points.append(cluster_center)

            # Remove processed points
            remaining_indices = [idx for idx in remaining_indices if idx not in nearby_indices]

        return clustered_points

    def _create_support_mesh(self, mesh: trimesh.Trimesh,
                           support_points: List[np.ndarray]) -> Optional[trimesh.Trimesh]:
        """Create mesh from support points."""
        if not support_points:
            return None

        # Create support structures based on type
        if self.settings.support_type == SupportType.TREE:
            return self._create_tree_supports(mesh, support_points)
        elif self.settings.support_type == SupportType.GRID:
            return self._create_grid_supports(mesh, support_points)
        elif self.settings.support_type == SupportType.CONTOUR:
            return self._create_contour_supports(mesh, support_points)
        elif self.settings.support_type == SupportType.ADAPTIVE:
            return self._create_adaptive_supports(mesh, support_points)
        else:  # MINIMAL
            return self._create_minimal_supports(mesh, support_points)

    def _create_tree_supports(self, mesh: trimesh.Trimesh,
                            support_points: List[np.ndarray]) -> trimesh.Trimesh:
        """Create tree-like support structures."""
        # Simplified tree support implementation
        support_vertices = []
        support_faces = []

        for i, point in enumerate(support_points):
            # Create vertical support pillar
            base_z = 0.0  # Assuming build plate at z=0
            height = point[2] - base_z

            # Create simple cylindrical support
            radius = self.settings.support_thickness / 2
            segments = 8

            # Base circle vertices
            base_vertices = []
            for j in range(segments):
                angle = 2 * np.pi * j / segments
                x = point[0] + radius * np.cos(angle)
                y = point[1] + radius * np.sin(angle)
                base_vertices.append([x, y, base_z])

            # Top circle vertices
            top_vertices = []
            for j in range(segments):
                angle = 2 * np.pi * j / segments
                x = point[0] + radius * np.cos(angle)
                y = point[1] + radius * np.sin(angle)
                top_vertices.append([x, y, point[2]])

            # Add vertices
            start_idx = len(support_vertices)
            support_vertices.extend(base_vertices)
            support_vertices.extend(top_vertices)

            # Create faces for cylindrical support
            for j in range(segments):
                next_j = (j + 1) % segments

                # Side faces
                face1 = [start_idx + j, start_idx + next_j,
                        start_idx + segments + next_j, start_idx + segments + j]
                support_faces.append(face1)

                # Bottom face
                if j == 0:
                    bottom_face = [start_idx + k for k in range(segments)]
                    support_faces.append(bottom_face)

                # Top face
                if j == 0:
                    top_face = [start_idx + segments + k for k in range(segments)]
                    support_faces.append(top_face)

        return trimesh.Trimesh(vertices=support_vertices, faces=support_faces)

    def _create_grid_supports(self, mesh: trimesh.Trimesh,
                            support_points: List[np.ndarray]) -> trimesh.Trimesh:
        """Create grid-based support structures."""
        # Simplified grid support implementation
        # For now, return tree supports as fallback
        return self._create_tree_supports(mesh, support_points)

    def _create_contour_supports(self, mesh: trimesh.Trimesh,
                               support_points: List[np.ndarray]) -> trimesh.Trimesh:
        """Create contour-based support structures."""
        # Simplified contour support implementation
        return self._create_tree_supports(mesh, support_points)

    def _create_adaptive_supports(self, mesh: trimesh.Trimesh,
                                support_points: List[np.ndarray]) -> trimesh.Trimesh:
        """Create adaptive support structures based on geometry."""
        # Adaptive supports combine multiple strategies
        return self._create_tree_supports(mesh, support_points)

    def _create_minimal_supports(self, mesh: trimesh.Trimesh,
                               support_points: List[np.ndarray]) -> trimesh.Trimesh:
        """Create minimal support structures."""
        # Create only essential supports
        return self._create_tree_supports(mesh, support_points)

    def _optimize_supports(self, support_mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Optimize support structures for material or speed."""
        # Basic optimization - decimate if too complex
        if len(support_mesh.faces) > 1000:
            try:
                # Reduce complexity while maintaining structure
                support_mesh = support_mesh.simplify_quadric_decimation(
                    int(len(support_mesh.faces) * 0.7)
                )
            except:
                pass  # Keep original if simplification fails

        return support_mesh

    def _calculate_volume(self, mesh: trimesh.Trimesh) -> float:
        """Calculate mesh volume."""
        return mesh.volume if mesh.is_volume else 0.0

    def _calculate_area(self, mesh: trimesh.Trimesh) -> float:
        """Calculate mesh surface area."""
        return mesh.area


def generate_supports(mesh: trimesh.Trimesh,
                     support_type: SupportType = SupportType.ADAPTIVE,
                     settings: SupportSettings = None) -> SupportResult:
    """
    Convenience function for support generation.

    Args:
        mesh: Input mesh requiring supports
        support_type: Type of support structures to generate
        settings: Optional support generation settings

    Returns:
        SupportResult with generated support structures
    """
    if settings is None:
        settings = SupportSettings(support_type=support_type)
    else:
        settings.support_type = support_type

    generator = SupportGenerator(settings)
    return generator.generate_supports(mesh)
