"""Advanced manifold validation for 3D meshes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

import numpy as np
import trimesh

from .mesh_validator import ValidationIssue


class ManifoldIssueType(Enum):
    """Types of manifold validation issues."""
    NON_MANIFOLD_EDGE = "non_manifold_edge"
    BOUNDARY_EDGE = "boundary_edge"
    INVERTED_NORMALS = "inverted_normals"
    INCONSISTENT_ORIENTATION = "inconsistent_orientation"
    DUPLICATE_FACES = "duplicate_faces"
    DEGENERATE_FACES = "degenerate_faces"
    ISOLATED_VERTICES = "isolated_vertices"
    NON_UNIFORM_SCALING = "non_uniform_scaling"
    COORDINATE_SYSTEM_FLIP = "coordinate_system_flip"


@dataclass
class ManifoldValidationResult:
    """Result of manifold validation."""
    is_manifold: bool
    issues: List[ValidationIssue]
    edge_statistics: dict
    face_statistics: dict
    vertex_statistics: dict
    scaling_analysis: dict
    coordinate_system_analysis: dict


class ManifoldValidator:
    """Advanced manifold validation engine."""

    def __init__(self):
        self.tolerance = 1e-8

    def validate_manifold(self, mesh: trimesh.Trimesh) -> ManifoldValidationResult:
        """Perform comprehensive manifold validation."""
        issues = []

        # Basic manifold checks
        edge_stats = self._analyze_edges(mesh, issues)
        face_stats = self._analyze_faces(mesh, issues)
        vertex_stats = self._analyze_vertices(mesh, issues)

        # Advanced checks
        scaling_analysis = self._analyze_scaling(mesh, issues)
        coord_system_analysis = self._analyze_coordinate_system(mesh, issues)

        # Normal orientation checks
        self._validate_normal_orientation(mesh, issues)

        is_manifold = len([issue for issue in issues if issue.severity == "error"]) == 0

        return ManifoldValidationResult(
            is_manifold=is_manifold,
            issues=issues,
            edge_statistics=edge_stats,
            face_statistics=face_stats,
            vertex_statistics=vertex_stats,
            scaling_analysis=scaling_analysis,
            coordinate_system_analysis=coord_system_analysis
        )

    def _analyze_edges(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> dict:
        """Analyze edge manifoldness."""
        stats = {
            'total_edges': 0,
            'boundary_edges': 0,
            'non_manifold_edges': 0,
            'manifold_edges': 0
        }

        try:
            # Get edge adjacency information
            edges = mesh.edges
            edge_face_count = np.bincount(mesh.edges_unique_inverse, minlength=len(mesh.edges_unique))

            stats['total_edges'] = len(mesh.edges_unique)
            stats['boundary_edges'] = np.sum(edge_face_count == 1)
            stats['non_manifold_edges'] = np.sum(edge_face_count > 2)
            stats['manifold_edges'] = np.sum(edge_face_count == 2)

            if stats['non_manifold_edges'] > 0:
                issues.append(ValidationIssue(
                    code="MANIFOLD_NON_MANIFOLD_EDGES",
                    message=f"Found {stats['non_manifold_edges']} non-manifold edges (edges shared by more than 2 faces)",
                    severity="error"
                ))

            if stats['boundary_edges'] > 0:
                issues.append(ValidationIssue(
                    code="MANIFOLD_BOUNDARY_EDGES",
                    message=f"Found {stats['boundary_edges']} boundary edges (mesh is not closed)",
                    severity="warning"
                ))

        except Exception as e:
            issues.append(ValidationIssue(
                code="MANIFOLD_EDGE_ANALYSIS_FAILED",
                message=f"Edge analysis failed: {str(e)}",
                severity="warning"
            ))

        return stats

    def _analyze_faces(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> dict:
        """Analyze face validity and orientation."""
        stats = {
            'total_faces': len(mesh.faces),
            'degenerate_faces': 0,
            'duplicate_faces': 0,
            'zero_area_faces': 0,
            'inverted_faces': 0
        }

        try:
            # Check for degenerate faces (faces with duplicate vertices)
            for i, face in enumerate(mesh.faces):
                if len(set(face)) < 3:
                    stats['degenerate_faces'] += 1

            if stats['degenerate_faces'] > 0:
                issues.append(ValidationIssue(
                    code="MANIFOLD_DEGENERATE_FACES",
                    message=f"Found {stats['degenerate_faces']} degenerate faces with duplicate vertices",
                    severity="error"
                ))

            # Check for zero-area faces
            areas = mesh.area_faces
            zero_area_mask = areas < self.tolerance
            stats['zero_area_faces'] = np.sum(zero_area_mask)

            if stats['zero_area_faces'] > 0:
                issues.append(ValidationIssue(
                    code="MANIFOLD_ZERO_AREA_FACES",
                    message=f"Found {stats['zero_area_faces']} faces with zero or near-zero area",
                    severity="warning"
                ))

            # Check for duplicate faces
            unique_faces = np.unique(np.sort(mesh.faces, axis=1), axis=0)
            stats['duplicate_faces'] = len(mesh.faces) - len(unique_faces)

            if stats['duplicate_faces'] > 0:
                issues.append(ValidationIssue(
                    code="MANIFOLD_DUPLICATE_FACES",
                    message=f"Found {stats['duplicate_faces']} duplicate faces",
                    severity="warning"
                ))

        except Exception as e:
            issues.append(ValidationIssue(
                code="MANIFOLD_FACE_ANALYSIS_FAILED",
                message=f"Face analysis failed: {str(e)}",
                severity="warning"
            ))

        return stats

    def _analyze_vertices(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> dict:
        """Analyze vertex usage and isolation."""
        stats = {
            'total_vertices': len(mesh.vertices),
            'used_vertices': 0,
            'isolated_vertices': 0,
            'duplicate_vertices': 0
        }

        try:
            # Find vertices actually used in faces
            used_vertex_indices = np.unique(mesh.faces.flatten())
            stats['used_vertices'] = len(used_vertex_indices)
            stats['isolated_vertices'] = stats['total_vertices'] - stats['used_vertices']

            if stats['isolated_vertices'] > 0:
                issues.append(ValidationIssue(
                    code="MANIFOLD_ISOLATED_VERTICES",
                    message=f"Found {stats['isolated_vertices']} isolated vertices not used by any face",
                    severity="warning"
                ))

            # Check for duplicate vertices
            # This is a simplified check - trimesh has more sophisticated methods
            unique_vertices = np.unique(mesh.vertices, axis=0)
            stats['duplicate_vertices'] = len(mesh.vertices) - len(unique_vertices)

            if stats['duplicate_vertices'] > 0:
                issues.append(ValidationIssue(
                    code="MANIFOLD_DUPLICATE_VERTICES",
                    message=f"Found {stats['duplicate_vertices']} duplicate vertices",
                    severity="warning"
                ))

        except Exception as e:
            issues.append(ValidationIssue(
                code="MANIFOLD_VERTEX_ANALYSIS_FAILED",
                message=f"Vertex analysis failed: {str(e)}",
                severity="warning"
            ))

        return stats

    def _analyze_scaling(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> dict:
        """Detect non-uniform scaling issues."""
        analysis = {
            'extents': [],
            'aspect_ratios': [],
            'is_uniform_scaling': True,
            'scaling_factor_variance': 0.0
        }

        try:
            if mesh.extents is not None and len(mesh.extents) == 3:
                extents = mesh.extents
                analysis['extents'] = extents.tolist()

                # Calculate aspect ratios
                max_extent = np.max(extents)
                if max_extent > 0:
                    ratios = extents / max_extent
                    analysis['aspect_ratios'] = ratios.tolist()

                    # Check for extreme aspect ratios that might indicate scaling issues
                    min_ratio = np.min(ratios)
                    variance = np.var(ratios)
                    analysis['scaling_factor_variance'] = float(variance)

                    # Flag potential non-uniform scaling
                    if min_ratio < 0.01:  # One dimension is 1% or less of the largest
                        analysis['is_uniform_scaling'] = False
                        issues.append(ValidationIssue(
                            code="MANIFOLD_NON_UNIFORM_SCALING",
                            message=f"Detected potential non-uniform scaling: aspect ratios {ratios}",
                            severity="warning"
                        ))

                    if variance > 0.25:  # High variance in scaling factors
                        issues.append(ValidationIssue(
                            code="MANIFOLD_SCALING_VARIANCE",
                            message=f"High variance in scaling factors: {variance:.3f}",
                            severity="warning"
                        ))

        except Exception as e:
            issues.append(ValidationIssue(
                code="MANIFOLD_SCALING_ANALYSIS_FAILED",
                message=f"Scaling analysis failed: {str(e)}",
                severity="warning"
            ))

        return analysis

    def _analyze_coordinate_system(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]) -> dict:
        """Detect flipped coordinate systems."""
        analysis = {
            'is_right_handed': True,
            'determinant_sign': 1,
            'volume_sign': 1
        }

        try:
            # Check if the mesh has consistent orientation
            if mesh.is_volume and hasattr(mesh, 'volume'):
                volume = mesh.volume
                analysis['volume_sign'] = 1 if volume >= 0 else -1

                if volume < 0:
                    analysis['is_right_handed'] = False
                    issues.append(ValidationIssue(
                        code="MANIFOLD_FLIPPED_COORDINATE_SYSTEM",
                        message="Negative volume detected, indicating flipped coordinate system or inside-out mesh",
                        severity="warning"
                    ))

            # Additional checks based on face normals and winding order
            if hasattr(mesh, 'face_normals') and mesh.face_normals.size > 0:
                # Sample some faces to check normal direction consistency
                sample_size = min(100, len(mesh.faces))
                sample_indices = np.random.choice(len(mesh.faces), sample_size, replace=False)

                face_centers = mesh.triangles_center[sample_indices]
                face_normals = mesh.face_normals[sample_indices]

                # Check if normals generally point outward from center of mass
                if hasattr(mesh, 'center_mass'):
                    center_to_faces = face_centers - mesh.center_mass
                    dot_products = np.sum(center_to_faces * face_normals, axis=1)
                    outward_facing_ratio = np.sum(dot_products > 0) / len(dot_products)

                    if outward_facing_ratio < 0.5:
                        issues.append(ValidationIssue(
                            code="MANIFOLD_INWARD_NORMALS",
                            message=f"Only {outward_facing_ratio:.1%} of face normals point outward, mesh may be inside-out",
                            severity="warning"
                        ))

        except Exception as e:
            issues.append(ValidationIssue(
                code="MANIFOLD_COORDINATE_ANALYSIS_FAILED",
                message=f"Coordinate system analysis failed: {str(e)}",
                severity="warning"
            ))

        return analysis

    def _validate_normal_orientation(self, mesh: trimesh.Trimesh, issues: List[ValidationIssue]):
        """Validate face normal orientation consistency."""
        try:
            if not hasattr(mesh, 'face_normals') or mesh.face_normals.size == 0:
                return

            # Check winding consistency
            if not mesh.is_winding_consistent:
                issues.append(ValidationIssue(
                    code="MANIFOLD_INCONSISTENT_WINDING",
                    message="Face winding order is inconsistent, causing normal orientation issues",
                    severity="error"
                ))

            # Check for inverted normals by analyzing adjacent faces
            if hasattr(mesh, 'face_adjacency') and mesh.face_adjacency.size > 0:
                face_normals = mesh.face_normals
                adjacency = mesh.face_adjacency

                inconsistent_pairs = 0
                total_pairs = len(adjacency)

                for i, (face_a, face_b) in enumerate(adjacency):
                    if i % 100 == 0 and i > 0:  # Sample to avoid performance issues
                        continue

                    normal_a = face_normals[face_a]
                    normal_b = face_normals[face_b]

                    # Adjacent faces should have similar normal directions
                    # (accounting for some variation due to mesh curvature)
                    dot_product = np.dot(normal_a, normal_b)

                    # If dot product is very negative, normals point in opposite directions
                    if dot_product < -0.5:
                        inconsistent_pairs += 1

                if total_pairs > 0:
                    inconsistency_ratio = inconsistent_pairs / min(total_pairs, 1000)  # Sample size limit

                    if inconsistency_ratio > 0.1:  # More than 10% of adjacent faces have opposing normals
                        issues.append(ValidationIssue(
                            code="MANIFOLD_OPPOSING_NORMALS",
                            message=f"Found {inconsistency_ratio:.1%} of adjacent faces with opposing normals",
                            severity="warning"
                        ))

        except Exception as e:
            issues.append(ValidationIssue(
                code="MANIFOLD_NORMAL_VALIDATION_FAILED",
                message=f"Normal orientation validation failed: {str(e)}",
                severity="warning"
            ))


def validate_manifold(mesh: trimesh.Trimesh) -> ManifoldValidationResult:
    """Convenience function for manifold validation."""
    validator = ManifoldValidator()
    return validator.validate_manifold(mesh)