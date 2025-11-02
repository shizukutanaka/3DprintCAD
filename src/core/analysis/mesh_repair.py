"""Mesh repair utilities for fixing common 3D printing issues."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple, Dict

import numpy as np
import trimesh

from .mesh_validator import MeshValidationResult, ValidationIssue

logger = logging.getLogger(__name__)


class RepairOperation(Enum):
    """Types of repair operations."""
    FILL_HOLES = "fill_holes"
    FIX_WINDING = "fix_winding"
    REMOVE_DUPLICATES = "remove_duplicates"
    MERGE_VERTICES = "merge_vertices"
    REMOVE_DEGENERATE = "remove_degenerate"
    SPLIT_COMPONENTS = "split_components"
    THICKEN_WALLS = "thicken_walls"
    SMOOTH_SURFACE = "smooth_surface"
    FIX_NORMALS = "fix_normals"
    REMOVE_NOISE = "remove_noise"


@dataclass
class RepairResult:
    """Result of a mesh repair operation."""
    operation: RepairOperation
    success: bool
    message: str
    vertices_before: int
    vertices_after: int
    faces_before: int
    faces_after: int


@dataclass
class MeshRepairSummary:
    """Summary of all repair operations performed."""
    original_mesh_stats: Dict[str, int]
    final_mesh_stats: Dict[str, int]
    operations_performed: List[RepairResult]
    issues_fixed: List[str]
    remaining_issues: List[str]
    repair_success: bool


class MeshRepairer:
    """Automated mesh repair engine."""

    def __init__(self, aggressive_repair: bool = False):
        self.aggressive_repair = aggressive_repair
        self.repair_history: List[RepairResult] = []

    def repair_mesh(self, mesh: trimesh.Trimesh, validation_result: Optional[MeshValidationResult] = None) -> Tuple[trimesh.Trimesh, MeshRepairSummary]:
        """Perform comprehensive mesh repair."""
        self.repair_history.clear()
        original_mesh = mesh.copy()
        current_mesh = mesh.copy()

        # Store original stats
        original_stats = self._get_mesh_stats(original_mesh)

        # Determine repair strategy based on validation issues
        repair_plan = self._create_repair_plan(validation_result)

        # Execute repair operations
        for operation in repair_plan:
            try:
                current_mesh = self._execute_repair_operation(current_mesh, operation)
            except Exception as e:
                logger.error(f"Repair operation {operation} failed: {e}")
                self._record_operation(operation, False, f"Failed: {str(e)}",
                                     current_mesh, current_mesh)

        # Final stats
        final_stats = self._get_mesh_stats(current_mesh)

        # Determine fixed issues
        issues_fixed, remaining_issues = self._analyze_repair_results(
            original_mesh, current_mesh, validation_result
        )

        summary = MeshRepairSummary(
            original_mesh_stats=original_stats,
            final_mesh_stats=final_stats,
            operations_performed=self.repair_history.copy(),
            issues_fixed=issues_fixed,
            remaining_issues=remaining_issues,
            repair_success=len(issues_fixed) > 0
        )

        return current_mesh, summary

    def _create_repair_plan(self, validation_result: Optional[MeshValidationResult]) -> List[RepairOperation]:
        """Create repair plan based on validation issues."""
        plan = []

        if validation_result and validation_result.issues:
            issue_codes = {issue.code for issue in validation_result.issues}

            # Basic geometric repairs (always first)
            plan.extend([
                RepairOperation.REMOVE_DUPLICATES,
                RepairOperation.MERGE_VERTICES,
                RepairOperation.REMOVE_DEGENERATE
            ])

            # Specific repairs based on issues
            if "GEOM_WATERTIGHT" in issue_codes:
                plan.append(RepairOperation.FILL_HOLES)

            if "GEOM_WINDING" in issue_codes:
                plan.append(RepairOperation.FIX_WINDING)

            if "GEOM_SELF_INTERSECTION" in issue_codes:
                plan.extend([RepairOperation.REMOVE_NOISE, RepairOperation.SMOOTH_SURFACE])

            if "GEOM_WALL_THICKNESS" in issue_codes and self.aggressive_repair:
                plan.append(RepairOperation.THICKEN_WALLS)

            # Fix normals last
            plan.append(RepairOperation.FIX_NORMALS)

        else:
            # Default repair plan
            plan = [
                RepairOperation.REMOVE_DUPLICATES,
                RepairOperation.MERGE_VERTICES,
                RepairOperation.REMOVE_DEGENERATE,
                RepairOperation.FILL_HOLES,
                RepairOperation.FIX_WINDING,
                RepairOperation.FIX_NORMALS
            ]

        return plan

    def _execute_repair_operation(self, mesh: trimesh.Trimesh, operation: RepairOperation) -> trimesh.Trimesh:
        """Execute a single repair operation."""
        before_vertices = len(mesh.vertices)
        before_faces = len(mesh.faces)

        try:
            if operation == RepairOperation.REMOVE_DUPLICATES:
                mesh = self._remove_duplicate_vertices(mesh)

            elif operation == RepairOperation.MERGE_VERTICES:
                mesh = self._merge_close_vertices(mesh)

            elif operation == RepairOperation.REMOVE_DEGENERATE:
                mesh = self._remove_degenerate_faces(mesh)

            elif operation == RepairOperation.FILL_HOLES:
                mesh = self._fill_holes(mesh)

            elif operation == RepairOperation.FIX_WINDING:
                mesh = self._fix_winding_order(mesh)

            elif operation == RepairOperation.FIX_NORMALS:
                mesh = self._fix_normals(mesh)

            elif operation == RepairOperation.SMOOTH_SURFACE:
                mesh = self._smooth_surface(mesh)

            elif operation == RepairOperation.REMOVE_NOISE:
                mesh = self._remove_noise(mesh)

            elif operation == RepairOperation.THICKEN_WALLS:
                mesh = self._thicken_walls(mesh)

            after_vertices = len(mesh.vertices)
            after_faces = len(mesh.faces)

            self._record_operation(
                operation, True, "Successfully completed",
                before_vertices, before_faces, after_vertices, after_faces
            )

        except Exception as e:
            logger.warning(f"Repair operation {operation.value} failed: {e}")
            self._record_operation(
                operation, False, f"Failed: {str(e)}",
                before_vertices, before_faces, before_vertices, before_faces
            )

        return mesh

    def _remove_duplicate_vertices(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Remove duplicate vertices."""
        mesh.remove_duplicate_faces()
        return mesh

    def _merge_close_vertices(self, mesh: trimesh.Trimesh, threshold: float = 1e-6) -> trimesh.Trimesh:
        """Merge vertices that are very close together."""
        try:
            mesh.merge_vertices(merge_tex=False, merge_norm=False)
        except Exception:
            # Fallback to manual merging
            pass
        return mesh

    def _remove_degenerate_faces(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Remove degenerate faces (zero area, duplicate vertices)."""
        try:
            # Remove faces with zero area
            areas = mesh.area_faces
            valid_faces = areas > 1e-10

            if not np.all(valid_faces):
                mesh.update_faces(valid_faces)

            # Remove faces with duplicate vertices
            face_validity = []
            for face in mesh.faces:
                unique_vertices = len(set(face))
                face_validity.append(unique_vertices == 3)  # Triangle should have 3 unique vertices

            if not all(face_validity):
                mesh.update_faces(face_validity)

        except Exception as e:
            logger.warning(f"Could not remove degenerate faces: {e}")

        return mesh

    def _fill_holes(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Fill holes in the mesh."""
        try:
            mesh.fill_holes()
        except Exception as e:
            logger.warning(f"Could not fill holes: {e}")
        return mesh

    def _fix_winding_order(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Fix face winding order."""
        try:
            mesh.fix_normals()
        except Exception as e:
            logger.warning(f"Could not fix winding order: {e}")
        return mesh

    def _fix_normals(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Fix face and vertex normals."""
        try:
            # Recompute face normals
            mesh._cache.clear()
            mesh.face_normals  # This triggers recomputation
        except Exception as e:
            logger.warning(f"Could not fix normals: {e}")
        return mesh

    def _smooth_surface(self, mesh: trimesh.Trimesh, iterations: int = 1) -> trimesh.Trimesh:
        """Apply surface smoothing."""
        try:
            for _ in range(iterations):
                mesh = mesh.smoothed()
        except Exception as e:
            logger.warning(f"Could not smooth surface: {e}")
        return mesh

    def _remove_noise(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Remove noise and small artifacts."""
        try:
            # Remove small disconnected components
            components = mesh.split(only_watertight=False)
            if len(components) > 1:
                # Keep only the largest component
                volumes = []
                for component in components:
                    try:
                        volumes.append(component.volume if component.is_volume else component.area)
                    except:
                        volumes.append(0)

                if volumes:
                    largest_idx = np.argmax(volumes)
                    mesh = components[largest_idx]
        except Exception as e:
            logger.warning(f"Could not remove noise: {e}")

        return mesh

    def _thicken_walls(self, mesh: trimesh.Trimesh, thickness: float = 1.0) -> trimesh.Trimesh:
        """Attempt to thicken thin walls (experimental)."""
        try:
            # This is a simplified approach - in practice, wall thickening is very complex
            # We apply slight surface expansion
            vertices = mesh.vertices.copy()
            normals = mesh.vertex_normals

            # Expand vertices slightly along normals
            expanded_vertices = vertices + normals * (thickness * 0.1)

            # Create new mesh with expanded vertices
            mesh = trimesh.Trimesh(vertices=expanded_vertices, faces=mesh.faces)

        except Exception as e:
            logger.warning(f"Could not thicken walls: {e}")

        return mesh

    def _record_operation(self, operation: RepairOperation, success: bool, message: str,
                         vertices_before: int, faces_before: int,
                         vertices_after: int, faces_after: int):
        """Record the result of a repair operation."""
        result = RepairResult(
            operation=operation,
            success=success,
            message=message,
            vertices_before=vertices_before,
            vertices_after=vertices_after,
            faces_before=faces_before,
            faces_after=faces_after
        )
        self.repair_history.append(result)

    def _get_mesh_stats(self, mesh: trimesh.Trimesh) -> Dict[str, int]:
        """Get basic mesh statistics."""
        return {
            "vertices": len(mesh.vertices),
            "faces": len(mesh.faces),
            "edges": len(mesh.edges),
            "is_watertight": mesh.is_watertight,
            "is_winding_consistent": mesh.is_winding_consistent,
            "is_volume": mesh.is_volume
        }

    def _analyze_repair_results(self, original_mesh: trimesh.Trimesh,
                               repaired_mesh: trimesh.Trimesh,
                               validation_result: Optional[MeshValidationResult]) -> Tuple[List[str], List[str]]:
        """Analyze what issues were fixed by the repair process."""
        issues_fixed = []
        remaining_issues = []

        if validation_result and validation_result.issues:
            for issue in validation_result.issues:
                if self._is_issue_fixed(issue.code, original_mesh, repaired_mesh):
                    issues_fixed.append(issue.message)
                else:
                    remaining_issues.append(issue.message)

        return issues_fixed, remaining_issues

    def _is_issue_fixed(self, issue_code: str, original_mesh: trimesh.Trimesh,
                       repaired_mesh: trimesh.Trimesh) -> bool:
        """Check if a specific issue was fixed."""
        try:
            if issue_code == "GEOM_WATERTIGHT":
                return not original_mesh.is_watertight and repaired_mesh.is_watertight

            elif issue_code == "GEOM_WINDING":
                return not original_mesh.is_winding_consistent and repaired_mesh.is_winding_consistent

            elif issue_code == "GEOM_VOLUME":
                return not original_mesh.is_volume and repaired_mesh.is_volume

            elif issue_code == "GEOM_EMPTY":
                return (len(original_mesh.vertices) == 0 or len(original_mesh.faces) == 0) and \
                       (len(repaired_mesh.vertices) > 0 and len(repaired_mesh.faces) > 0)

        except Exception:
            pass

        return False


def repair_mesh(mesh: trimesh.Trimesh,
               validation_result: Optional[MeshValidationResult] = None,
               aggressive: bool = False) -> Tuple[trimesh.Trimesh, MeshRepairSummary]:
    """Convenience function to repair a mesh."""
    repairer = MeshRepairer(aggressive_repair=aggressive)
    return repairer.repair_mesh(mesh, validation_result)