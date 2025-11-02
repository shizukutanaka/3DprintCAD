"""Watertightness validation for 3D meshes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging

import numpy as np
import trimesh
from scipy.spatial import cKDTree

from .mesh_validator import ValidationIssue


class WatertightnessIssueType(Enum):
    """Types of watertightness issues."""
    OPEN_BOUNDARY = "open_boundary"
    HOLE_IN_MESH = "hole_in_mesh"
    GAP_IN_MESH = "gap_in_mesh"
    NON_MANIFOLD = "non_manifold"
    SELF_INTERSECTION = "self_intersection"
    INCONSISTENT_NORMALS = "inconsistent_normals"
    NEGATIVE_VOLUME = "negative_volume"
    DISCONNECTED_COMPONENTS = "disconnected_components"
    THIN_SHELL = "thin_shell"


@dataclass
class WatertightnessResult:
    """Result of watertightness validation."""
    is_watertight: bool
    is_solid: bool
    volume: float
    issues: List[ValidationIssue]
    boundary_info: Dict[str, Any]
    component_info: Dict[str, Any]
    hole_info: Dict[str, Any]
    gap_analysis: Dict[str, Any]
    shell_thickness_info: Dict[str, Any]


class WatertightnessValidator:
    """Advanced watertightness validation engine."""

    def __init__(self, tolerance: float = 1e-8, gap_threshold: float = 0.1):
        """
        Initialize watertightness validator.

        Args:
            tolerance: Numerical tolerance for comparisons
            gap_threshold: Maximum distance to consider as a gap (mm)
        """
        self.tolerance = tolerance
        self.gap_threshold = gap_threshold
        self.logger = logging.getLogger(__name__)

    def validate_watertightness(self, mesh: trimesh.Trimesh) -> WatertightnessResult:
        """
        Perform comprehensive watertightness validation.

        Args:
            mesh: The trimesh object to validate

        Returns:
            WatertightnessResult with detailed analysis
        """
        issues = []

        # Basic watertightness check
        is_watertight = self._check_basic_watertightness(mesh, issues)

        # Analyze boundaries and holes
        boundary_info = self._analyze_boundaries(mesh, issues)
        hole_info = self._detect_holes(mesh, issues)

        # Component analysis
        component_info = self._analyze_components(mesh, issues)

        # Gap detection
        gap_analysis = self._detect_gaps(mesh, issues)

        # Shell thickness analysis
        shell_thickness_info = self._analyze_shell_thickness(mesh, issues)

        # Volume calculation and validation
        volume = self._calculate_volume(mesh, issues)
        is_solid = is_watertight and volume > 0

        # Normal consistency check
        self._check_normal_consistency(mesh, issues)

        return WatertightnessResult(
            is_watertight=is_watertight,
            is_solid=is_solid,
            volume=volume,
            issues=issues,
            boundary_info=boundary_info,
            component_info=component_info,
            hole_info=hole_info,
            gap_analysis=gap_analysis,
            shell_thickness_info=shell_thickness_info
        )

    def _check_basic_watertightness(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> bool:
        """Check basic watertightness properties."""
        try:
            # Use trimesh's built-in watertight check
            is_watertight = mesh.is_watertight

            if not is_watertight:
                issues.append(ValidationIssue(
                    code="WATERTIGHT_NOT_CLOSED",
                    message="Mesh is not watertight (contains open boundaries)",
                    severity="error"
                ))

            # Check if mesh is manifold (requirement for watertightness)
            if not mesh.is_winding_consistent:
                issues.append(ValidationIssue(
                    code="WATERTIGHT_INCONSISTENT_WINDING",
                    message="Face winding order is inconsistent",
                    severity="error"
                ))
                is_watertight = False

            # Check for valid volume
            if not mesh.is_volume:
                issues.append(ValidationIssue(
                    code="WATERTIGHT_NOT_VOLUME",
                    message="Mesh does not enclose a valid volume",
                    severity="error"
                ))
                is_watertight = False

            return is_watertight

        except Exception as e:
            self.logger.warning(f"Basic watertightness check failed: {e}")
            issues.append(ValidationIssue(
                code="WATERTIGHT_CHECK_FAILED",
                message=f"Watertightness check failed: {str(e)}",
                severity="warning"
            ))
            return False

    def _analyze_boundaries(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Analyze mesh boundaries and edges."""
        boundary_info = {
            'has_boundaries': False,
            'boundary_edges': 0,
            'boundary_loops': 0,
            'boundary_vertices': 0,
            'largest_hole_perimeter': 0.0
        }

        try:
            # Get edges that appear only once (boundary edges)
            edges = mesh.edges
            edge_count = {}

            for edge in edges:
                edge_key = tuple(sorted(edge))
                edge_count[edge_key] = edge_count.get(edge_key, 0) + 1

            boundary_edges = [edge for edge, count in edge_count.items() if count == 1]
            boundary_info['boundary_edges'] = len(boundary_edges)
            boundary_info['has_boundaries'] = len(boundary_edges) > 0

            if boundary_edges:
                # Find connected boundary loops
                boundary_loops = self._find_boundary_loops(boundary_edges, mesh.vertices)
                boundary_info['boundary_loops'] = len(boundary_loops)

                # Find unique boundary vertices
                boundary_vertices = set()
                for edge in boundary_edges:
                    boundary_vertices.update(edge)
                boundary_info['boundary_vertices'] = len(boundary_vertices)

                # Calculate perimeter of largest hole
                if boundary_loops:
                    max_perimeter = 0.0
                    for loop in boundary_loops:
                        perimeter = 0.0
                        for i in range(len(loop)):
                            v1 = mesh.vertices[loop[i]]
                            v2 = mesh.vertices[loop[(i + 1) % len(loop)]]
                            perimeter += np.linalg.norm(v2 - v1)
                        max_perimeter = max(max_perimeter, perimeter)
                    boundary_info['largest_hole_perimeter'] = float(max_perimeter)

                issues.append(ValidationIssue(
                    code="WATERTIGHT_OPEN_BOUNDARIES",
                    message=f"Found {len(boundary_edges)} boundary edges forming {len(boundary_loops)} holes",
                    severity="error"
                ))

                if boundary_info['largest_hole_perimeter'] > 10.0:  # Large hole (> 10mm perimeter)
                    issues.append(ValidationIssue(
                        code="WATERTIGHT_LARGE_HOLE",
                        message=f"Large hole detected with perimeter {boundary_info['largest_hole_perimeter']:.2f}mm",
                        severity="error"
                    ))

        except Exception as e:
            self.logger.warning(f"Boundary analysis failed: {e}")
            issues.append(ValidationIssue(
                code="WATERTIGHT_BOUNDARY_ANALYSIS_FAILED",
                message=f"Boundary analysis failed: {str(e)}",
                severity="warning"
            ))

        return boundary_info

    def _find_boundary_loops(self, boundary_edges: List[Tuple[int, int]], vertices: np.ndarray) -> List[List[int]]:
        """Find connected loops from boundary edges."""
        loops = []
        edges_to_process = list(boundary_edges)

        while edges_to_process:
            # Start a new loop
            current_loop = []
            edge = edges_to_process.pop(0)
            current_loop.extend(edge)

            # Try to extend the loop
            changed = True
            while changed:
                changed = False
                for i, next_edge in enumerate(edges_to_process):
                    if current_loop[-1] in next_edge:
                        # Found connecting edge
                        if next_edge[0] == current_loop[-1]:
                            current_loop.append(next_edge[1])
                        else:
                            current_loop.append(next_edge[0])
                        edges_to_process.pop(i)
                        changed = True

                        # Check if loop is closed
                        if current_loop[0] == current_loop[-1]:
                            loops.append(current_loop[:-1])  # Remove duplicate vertex
                            break
                    elif current_loop[0] in next_edge:
                        # Found edge connecting to start
                        if next_edge[0] == current_loop[0]:
                            current_loop.insert(0, next_edge[1])
                        else:
                            current_loop.insert(0, next_edge[0])
                        edges_to_process.pop(i)
                        changed = True

                        # Check if loop is closed
                        if current_loop[0] == current_loop[-1]:
                            loops.append(current_loop[:-1])  # Remove duplicate vertex
                            break

                if not changed and len(current_loop) > 2:
                    # Can't extend further, save as open chain
                    loops.append(current_loop)

        return loops

    def _detect_holes(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Detect and analyze holes in the mesh."""
        hole_info = {
            'hole_count': 0,
            'total_hole_area': 0.0,
            'hole_sizes': [],
            'hole_locations': []
        }

        try:
            # Use trimesh's hole detection if available
            if hasattr(mesh, 'holes'):
                holes = mesh.holes
                hole_info['hole_count'] = len(holes)

                for hole in holes:
                    # Calculate hole area (simplified)
                    area = hole.area if hasattr(hole, 'area') else 0.0
                    hole_info['total_hole_area'] += area
                    hole_info['hole_sizes'].append(area)

                    if hasattr(hole, 'centroid'):
                        hole_info['hole_locations'].append(hole.centroid.tolist())

            # Alternative: Detect holes through boundary analysis
            else:
                # Get boundary loops from boundary edges
                edges = mesh.edges_unique
                edge_count = np.bincount(mesh.edges_unique_inverse)
                boundary_mask = edge_count == 1

                if np.any(boundary_mask):
                    boundary_edges = edges[boundary_mask]
                    hole_info['hole_count'] = len(boundary_edges) // 3  # Rough estimate

                    issues.append(ValidationIssue(
                        code="WATERTIGHT_HOLES_DETECTED",
                        message=f"Detected approximately {hole_info['hole_count']} holes in mesh",
                        severity="error"
                    ))

        except Exception as e:
            self.logger.warning(f"Hole detection failed: {e}")
            issues.append(ValidationIssue(
                code="WATERTIGHT_HOLE_DETECTION_FAILED",
                message=f"Hole detection failed: {str(e)}",
                severity="warning"
            ))

        return hole_info

    def _analyze_components(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Analyze mesh components and connectivity."""
        component_info = {
            'component_count': 1,
            'is_connected': True,
            'component_volumes': [],
            'component_sizes': [],
            'largest_component_ratio': 1.0
        }

        try:
            # Split mesh into connected components
            components = mesh.split(only_watertight=False)
            component_info['component_count'] = len(components)
            component_info['is_connected'] = len(components) == 1

            if len(components) > 1:
                # Analyze each component
                total_volume = 0.0
                max_volume = 0.0

                for comp in components:
                    volume = comp.volume if comp.is_volume else 0.0
                    size = len(comp.vertices)

                    component_info['component_volumes'].append(float(volume))
                    component_info['component_sizes'].append(size)

                    total_volume += abs(volume)
                    max_volume = max(max_volume, abs(volume))

                if total_volume > 0:
                    component_info['largest_component_ratio'] = max_volume / total_volume

                issues.append(ValidationIssue(
                    code="WATERTIGHT_MULTIPLE_COMPONENTS",
                    message=f"Mesh has {len(components)} disconnected components",
                    severity="warning" if component_info['largest_component_ratio'] > 0.95 else "error"
                ))

                # Check for tiny floating components
                small_components = sum(1 for v in component_info['component_volumes'] if v < 0.01)
                if small_components > 0:
                    issues.append(ValidationIssue(
                        code="WATERTIGHT_FLOATING_DEBRIS",
                        message=f"Found {small_components} tiny floating components (< 0.01mm³)",
                        severity="warning"
                    ))

        except Exception as e:
            self.logger.warning(f"Component analysis failed: {e}")
            issues.append(ValidationIssue(
                code="WATERTIGHT_COMPONENT_ANALYSIS_FAILED",
                message=f"Component analysis failed: {str(e)}",
                severity="warning"
            ))

        return component_info

    def _detect_gaps(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Detect small gaps between mesh components."""
        gap_analysis = {
            'gaps_detected': False,
            'gap_count': 0,
            'max_gap_distance': 0.0,
            'gap_locations': []
        }

        try:
            # Build KD-tree for efficient nearest neighbor search
            kdtree = cKDTree(mesh.vertices)

            # For each vertex, find nearest vertices
            distances, indices = kdtree.query(mesh.vertices, k=10)

            # Look for vertices that are close but not connected
            gap_candidates = []

            for i, (dist_array, idx_array) in enumerate(zip(distances, indices)):
                for j, (dist, idx) in enumerate(zip(dist_array[1:], idx_array[1:])):  # Skip self
                    if dist < self.gap_threshold and dist > self.tolerance:
                        # Check if vertices are connected by an edge
                        edge_exists = False
                        for face in mesh.faces:
                            if i in face and idx in face:
                                edge_exists = True
                                break

                        if not edge_exists:
                            gap_candidates.append((i, idx, dist))

            if gap_candidates:
                gap_analysis['gaps_detected'] = True
                gap_analysis['gap_count'] = len(gap_candidates)
                gap_analysis['max_gap_distance'] = max(g[2] for g in gap_candidates)

                # Sample gap locations
                for i, j, dist in gap_candidates[:10]:  # Limit to 10 for performance
                    midpoint = (mesh.vertices[i] + mesh.vertices[j]) / 2
                    gap_analysis['gap_locations'].append({
                        'position': midpoint.tolist(),
                        'distance': float(dist)
                    })

                issues.append(ValidationIssue(
                    code="WATERTIGHT_GAPS_DETECTED",
                    message=f"Found {len(gap_candidates)} potential gaps (max: {gap_analysis['max_gap_distance']:.3f}mm)",
                    severity="warning"
                ))

        except Exception as e:
            self.logger.warning(f"Gap detection failed: {e}")
            issues.append(ValidationIssue(
                code="WATERTIGHT_GAP_DETECTION_FAILED",
                message=f"Gap detection failed: {str(e)}",
                severity="warning"
            ))

        return gap_analysis

    def _analyze_shell_thickness(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Analyze shell thickness to detect thin shells that might not be truly solid."""
        shell_info = {
            'is_thin_shell': False,
            'min_thickness': None,
            'avg_thickness': None,
            'thin_regions': []
        }

        try:
            # Use ray casting to estimate shell thickness
            # Sample points on the surface
            sample_count = min(100, len(mesh.vertices))
            sample_indices = np.random.choice(len(mesh.vertices), sample_count, replace=False)

            thicknesses = []
            thin_threshold = 0.5  # mm

            for idx in sample_indices:
                vertex = mesh.vertices[idx]

                # Cast ray inward (opposite to normal)
                if hasattr(mesh, 'vertex_normals') and len(mesh.vertex_normals) > idx:
                    normal = mesh.vertex_normals[idx]

                    # Ray cast inward
                    ray_origins = np.array([vertex - normal * 0.001])  # Start slightly inside
                    ray_directions = np.array([-normal])

                    try:
                        locations, index_ray, index_tri = mesh.ray.intersects_location(
                            ray_origins=ray_origins,
                            ray_directions=ray_directions
                        )

                        if len(locations) > 0:
                            # Find the closest intersection
                            distances = np.linalg.norm(locations - vertex, axis=1)
                            min_distance = np.min(distances)
                            thicknesses.append(min_distance)

                            if min_distance < thin_threshold:
                                shell_info['thin_regions'].append({
                                    'location': vertex.tolist(),
                                    'thickness': float(min_distance)
                                })
                    except:
                        pass

            if thicknesses:
                shell_info['min_thickness'] = float(np.min(thicknesses))
                shell_info['avg_thickness'] = float(np.mean(thicknesses))
                shell_info['is_thin_shell'] = shell_info['min_thickness'] < thin_threshold

                if shell_info['is_thin_shell']:
                    issues.append(ValidationIssue(
                        code="WATERTIGHT_THIN_SHELL",
                        message=f"Detected thin shell regions (min thickness: {shell_info['min_thickness']:.3f}mm)",
                        severity="warning"
                    ))

        except Exception as e:
            self.logger.warning(f"Shell thickness analysis failed: {e}")

        return shell_info

    def _calculate_volume(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> float:
        """Calculate mesh volume and validate it."""
        try:
            if mesh.is_volume:
                volume = mesh.volume

                if volume < 0:
                    issues.append(ValidationIssue(
                        code="WATERTIGHT_NEGATIVE_VOLUME",
                        message=f"Mesh has negative volume ({volume:.3f}mm³), indicating inverted normals",
                        severity="error"
                    ))
                    return abs(volume)

                if volume < 0.001:  # Less than 0.001 mm³
                    issues.append(ValidationIssue(
                        code="WATERTIGHT_NEAR_ZERO_VOLUME",
                        message=f"Mesh has near-zero volume ({volume:.6f}mm³)",
                        severity="warning"
                    ))

                return volume
            else:
                issues.append(ValidationIssue(
                    code="WATERTIGHT_VOLUME_CALCULATION_FAILED",
                    message="Cannot calculate volume for non-watertight mesh",
                    severity="error"
                ))
                return 0.0

        except Exception as e:
            self.logger.warning(f"Volume calculation failed: {e}")
            issues.append(ValidationIssue(
                code="WATERTIGHT_VOLUME_ERROR",
                message=f"Volume calculation failed: {str(e)}",
                severity="warning"
            ))
            return 0.0

    def _check_normal_consistency(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]):
        """Check normal vector consistency."""
        try:
            if hasattr(mesh, 'face_normals') and mesh.face_normals.size > 0:
                # Check for zero-length normals
                normal_lengths = np.linalg.norm(mesh.face_normals, axis=1)
                zero_normals = np.sum(normal_lengths < self.tolerance)

                if zero_normals > 0:
                    issues.append(ValidationIssue(
                        code="WATERTIGHT_ZERO_NORMALS",
                        message=f"Found {zero_normals} faces with zero-length normals",
                        severity="warning"
                    ))

                # Check winding consistency
                if not mesh.is_winding_consistent:
                    issues.append(ValidationIssue(
                        code="WATERTIGHT_INCONSISTENT_NORMALS",
                        message="Face normal orientations are inconsistent",
                        severity="error"
                    ))

        except Exception as e:
            self.logger.warning(f"Normal consistency check failed: {e}")


def validate_watertightness(mesh: trimesh.Trimesh, tolerance: float = 1e-8,
                           gap_threshold: float = 0.1) -> WatertightnessResult:
    """
    Convenience function for watertightness validation.

    Args:
        mesh: The trimesh object to validate
        tolerance: Numerical tolerance for comparisons
        gap_threshold: Maximum distance to consider as a gap (mm)

    Returns:
        WatertightnessResult with detailed analysis
    """
    validator = WatertightnessValidator(tolerance=tolerance, gap_threshold=gap_threshold)
    return validator.validate_watertightness(mesh)