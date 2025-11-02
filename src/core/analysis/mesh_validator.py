"""Mesh validation utilities for printable geometry.

The module provides a focused set of structural checks to ensure imported meshes
are suitable for 3D printing workflows. The implementation leverages ``trimesh``
so that forthcoming enhancements (wall thickness analysis, segmentation, etc.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import trimesh
import logging

from .manifold_validator import ManifoldValidationResult, validate_manifold
from .watertightness import WatertightnessResult, validate_watertightness
from .ai_defect_detector import detect_defects_with_ai


_IDENTITY4 = np.eye(4)


@dataclass(frozen=True)
class ValidationIssue:
    """Represents a single validation finding."""

    code: str
    message: str
    severity: str = "error"  # ``error`` or ``warning``

    def as_dict(self) -> Dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass(frozen=True)
class MeshValidationMetrics:
    """Summary metrics calculated during validation."""

    surface_area_mm2: float
    volume_mm3: float
    volume_cm3: float
    bounding_box_mm: List[float]
    bounding_box_diagonal_mm: float
    component_count: int
    min_edge_length_mm: float
    overhang_face_count: int
    min_wall_thickness_mm: float
    center_of_gravity_mm: List[float]
    cavities_detected: int
    thin_tip_faces: int
    floating_shell_count: int
    min_hole_diameter_mm: float
    high_aspect_ratio_faces: int
    sharp_internal_corners: int
    surface_roughness_score: float
    bed_contact_area_mm2: float
    scale_consistent: bool
    auto_orientation_euler_deg: List[float]
    auto_orientation_bed_area_mm2: float
    flatness_deviation_mm: float
    repair_suggestions: List[str]
    manifold_statistics: Dict[str, Any]
    watertightness_statistics: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "surface_area_mm2": self.surface_area_mm2,
            "volume_mm3": self.volume_mm3,
            "volume_cm3": self.volume_cm3,
            "bounding_box_mm": self.bounding_box_mm,
            "bounding_box_diagonal_mm": self.bounding_box_diagonal_mm,
            "component_count": self.component_count,
            "min_edge_length_mm": self.min_edge_length_mm,
            "overhang_face_count": self.overhang_face_count,
            "min_wall_thickness_mm": self.min_wall_thickness_mm,
            "center_of_gravity_mm": self.center_of_gravity_mm,
            "cavities_detected": self.cavities_detected,
            "thin_tip_faces": self.thin_tip_faces,
            "floating_shell_count": self.floating_shell_count,
            "min_hole_diameter_mm": self.min_hole_diameter_mm,
            "high_aspect_ratio_faces": self.high_aspect_ratio_faces,
            "sharp_internal_corners": self.sharp_internal_corners,
            "surface_roughness_score": self.surface_roughness_score,
            "bed_contact_area_mm2": self.bed_contact_area_mm2,
            "scale_consistent": self.scale_consistent,
            "auto_orientation_euler_deg": self.auto_orientation_euler_deg,
            "auto_orientation_bed_area_mm2": self.auto_orientation_bed_area_mm2,
            "flatness_deviation_mm": self.flatness_deviation_mm,
            "repair_suggestions": self.repair_suggestions,
            "manifold_statistics": self.manifold_statistics,
            "watertightness_statistics": self.watertightness_statistics,
        }


@dataclass(frozen=True)
class MeshValidationSettings:
    """Configuration knobs for geometric validation."""

    min_wall_thickness_mm: float = 0.8
    min_feature_size_mm: float = 0.4
    support_overhang_angle_deg: float = 60.0
    min_hole_diameter_mm: float = 1.0
    max_surface_roughness_score: float = 1.7
    min_bed_contact_area_mm2: float = 150.0
    min_model_extent_mm: float = 0.2
    max_model_extent_mm: float = 2000.0
    max_flatness_deviation_mm: float = 0.1


@dataclass
class MeshValidationResult:
    """Aggregated outcome of a mesh validation run."""

    path: Optional[Path]
    issues: List[ValidationIssue] = field(default_factory=list)
    metrics: Optional[MeshValidationMetrics] = None
    ai_defects: List[Dict[str, Any]] = field(default_factory=list)  # AI-detected defects

    @property
    def success(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def as_dict(self) -> Dict[str, object]:
        data: Dict[str, object] = {
            "path": str(self.path) if self.path else None,
            "success": self.success,
            "issues": [issue.as_dict() for issue in self.issues],
            "ai_defects": self.ai_defects,
        }
        if self.metrics:
            data["metrics"] = self.metrics.as_dict()
        return data


def _compute_metrics(
    mesh: trimesh.Trimesh,
    *,
    components: Optional[List[trimesh.Trimesh]] = None,
    extents: Optional[np.ndarray] = None,
    surface_area: Optional[float] = None,
    raw_volume: Optional[float] = None,
    min_edge_length: float,
    overhang_face_count: int,
    min_wall_thickness: float,
    center_of_gravity: List[float],
    cavities_detected: int,
    thin_tip_faces: int,
    floating_shell_count: int,
    min_hole_diameter: float,
    high_aspect_ratio_faces: int,
    sharp_internal_corners: int,
    surface_roughness_score: float,
    bed_contact_area: float,
    scale_consistent: bool,
    auto_orientation_euler: List[float],
    auto_orientation_area: float,
    flatness_deviation: float,
    repair_suggestions: List[str],
    manifold_statistics: Dict[str, Any],
    watertightness_statistics: Dict[str, Any],
) -> MeshValidationMetrics:
    extents_array = extents if extents is not None else mesh.extents
    extents_list = (
        extents_array.tolist()
        if isinstance(extents_array, np.ndarray)
        else (extents_array if isinstance(extents_array, list) else None)
    )
    bounding_box = extents_list if extents_list is not None else [0.0, 0.0, 0.0]

    surface_area_value = (
        float(surface_area)
        if surface_area is not None
        else (float(mesh.area) if mesh.area is not None else 0.0)
    )
    volume = (
        float(raw_volume)
        if raw_volume is not None
        else (float(mesh.volume) if mesh.is_volume else 0.0)
    )
    if watertightness_statistics:
        volume_override = watertightness_statistics.get("volume")
        if isinstance(volume_override, (int, float)):
            volume = float(volume_override)
    volume_cm3 = volume / 1000.0 if volume else 0.0
    diagonal = 0.0
    if extents_array is not None:
        diagonal = float(np.linalg.norm(extents_array))
    elif mesh.extents is not None:
        diagonal = float(np.linalg.norm(mesh.extents))
    precomputed_components = components if components is not None else mesh.split(only_watertight=False)
    component_count = len(precomputed_components) if precomputed_components else 0
    if watertightness_statistics:
        component_info = watertightness_statistics.get("component_info")
        if isinstance(component_info, dict):
            component_count = int(component_info.get("component_count", component_count))

    return MeshValidationMetrics(
        surface_area_mm2=surface_area_value,
        volume_mm3=volume,
        volume_cm3=volume_cm3,
        bounding_box_mm=bounding_box,
        bounding_box_diagonal_mm=diagonal,
        component_count=component_count,
        min_edge_length_mm=min_edge_length,
        overhang_face_count=overhang_face_count,
        min_wall_thickness_mm=min_wall_thickness,
        center_of_gravity_mm=center_of_gravity,
        cavities_detected=cavities_detected,
        thin_tip_faces=thin_tip_faces,
        floating_shell_count=floating_shell_count,
        min_hole_diameter_mm=min_hole_diameter,
        high_aspect_ratio_faces=high_aspect_ratio_faces,
        sharp_internal_corners=sharp_internal_corners,
        surface_roughness_score=surface_roughness_score,
        bed_contact_area_mm2=bed_contact_area,
        scale_consistent=scale_consistent,
        auto_orientation_euler_deg=auto_orientation_euler,
        auto_orientation_bed_area_mm2=auto_orientation_area,
        flatness_deviation_mm=flatness_deviation,
        repair_suggestions=repair_suggestions,
        manifold_statistics=manifold_statistics,
        watertightness_statistics=watertightness_statistics,
    )




def validate_mesh(
    mesh: trimesh.Trimesh,
    *,
    settings: Optional[MeshValidationSettings] = None,
    source_path: Optional[Path] = None,
) -> MeshValidationResult:
    """Run a baseline validation suite against the provided mesh."""

    issues: List[ValidationIssue] = []
    manifold_statistics: Dict[str, Any] = {}
    watertightness_statistics: Dict[str, Any] = {}
    settings = settings or MeshValidationSettings()

    if mesh.vertices.size == 0 or mesh.faces.size == 0:
        issues.append(
            ValidationIssue(
                code="GEOM_EMPTY",
                message="Mesh contains no vertices or faces.",
                severity="error",
            )
        )
        return MeshValidationResult(path=source_path, issues=issues, metrics=None)

    is_watertight = bool(getattr(mesh, "is_watertight", False))
    if not is_watertight:
        issues.append(
            ValidationIssue(
                code="GEOM_WATERTIGHT",
                message="Mesh is not watertight. Repair holes or gaps before printing.",
                severity="error",
            )
        )

    is_winding_consistent = bool(getattr(mesh, "is_winding_consistent", False))
    if not is_winding_consistent:
        issues.append(
            ValidationIssue(
                code="GEOM_WINDING",
                message="Mesh has inconsistent winding leading to non-manifold edges.",
                severity="error",
            )
        )

    is_volume = bool(getattr(mesh, "is_volume", False))
    if not is_volume:
        issues.append(
            ValidationIssue(
                code="GEOM_VOLUME",
                message="Mesh does not form a closed volume. Confirm all faces are connected.",
                severity="error",
            )
        )

    try:
        manifold_result = validate_manifold(mesh)
        manifold_statistics = _summarize_manifold_result(manifold_result)
        _extend_unique_issues(issues, manifold_result.issues)
    except Exception as exc:
        issues.append(
            ValidationIssue(
                code="GEOM_MANIFOLD_VALIDATION_FAILED",
                message=f"Enhanced manifold validation failed: {str(exc)}",
                severity="warning",
            )
        )

    try:
        watertightness_result = validate_watertightness(mesh)
        watertightness_statistics = _summarize_watertightness_result(watertightness_result)
        _extend_unique_issues(issues, watertightness_result.issues)
    except Exception as exc:
        issues.append(
            ValidationIssue(
                code="GEOM_WATERTIGHTNESS_VALIDATION_FAILED",
                message=f"Advanced watertightness validation failed: {str(exc)}",
                severity="warning",
            )
        )

    critical_codes = {issue.code for issue in issues if issue.severity == "error"}
    if critical_codes:
        return MeshValidationResult(path=source_path, issues=issues, metrics=None)

    components = mesh.split(only_watertight=False)
    if components and len(components) > 1:
        issues.append(
            ValidationIssue(
                code="GEOM_MULTIPLE_COMPONENTS",
                message="Mesh contains multiple disconnected components.",
                severity="warning",
            )
        )

    floating_shell_count = _count_floating_shells(components)
    if floating_shell_count:
        issues.append(
            ValidationIssue(
                code="GEOM_FLOATING_SHELL",
                message="Detected detached shells that may not adhere to the main body during printing.",
                severity="warning",
            )
        )

    if _has_self_intersections(mesh):
        issues.append(
            ValidationIssue(
                code="GEOM_SELF_INTERSECTION",
                message="Mesh contains self-intersecting faces that must be resolved before printing.",
                severity="error",
            )
        )

    edges = mesh.edges_unique_length
    min_edge_length = float(np.min(edges)) if edges.size else 0.0
    if edges.size and min_edge_length < settings.min_feature_size_mm:
        issues.append(
            ValidationIssue(
                code="GEOM_SMALL_FEATURE",
                message=(
                    "Mesh contains edges smaller than the configured minimum feature size. "
                    "Consider thickening thin features before printing."
                ),
                severity="warning",
            )
        )

    bounds = getattr(mesh, "bounds", None)
    extents = getattr(mesh, "extents", None)
    face_normals = getattr(mesh, "face_normals", np.array([]))
    triangles_center = getattr(mesh, "triangles_center", np.array([]))
    area_faces = getattr(mesh, "area_faces", np.array([]))

    overhang_face_count = _detect_overhang_faces(
        mesh,
        settings,
        face_normals=face_normals,
        triangles_center=triangles_center,
        bounds=bounds,
    )
    if overhang_face_count:
        issues.append(
            ValidationIssue(
                code="GEOM_OVERHANG",
                message=(
                    f"Detected {overhang_face_count} downward-facing faces exceeding the allowed "
                    f"overhang angle of {settings.support_overhang_angle_deg:.1f} degrees."
                ),
                severity="warning",
            )
        )

    min_wall_thickness = _estimate_min_wall_thickness(mesh)
    if (
        min_wall_thickness is not None
        and min_wall_thickness > 0.0
        and min_wall_thickness < settings.min_wall_thickness_mm
    ):
        issues.append(
            ValidationIssue(
                code="GEOM_WALL_THICKNESS",
                message=(
                    "Measured minimum wall thickness is below the configured threshold. "
                    "Consider reinforcing thin regions before printing."
                ),
                severity="warning",
            )
        )

    center_of_gravity = _compute_center_of_gravity(mesh)

    cavities_detected, thin_tip_faces, min_hole_diameter = _analyze_sections(mesh)
    high_aspect_ratio_faces = _count_high_aspect_ratio_faces(mesh)
    sharp_internal_corners = _count_sharp_internal_corners(mesh)
    surface_roughness_score = _estimate_surface_roughness(mesh)
    bed_contact_area = _measure_bed_contact_area(
        mesh,
        face_normals=face_normals,
        triangles_center=triangles_center,
        area_faces=area_faces,
        bounds=bounds,
        extents=extents,
    )
    scale_consistent = _is_scale_consistent(mesh, settings, bounds=bounds, extents=extents)
    auto_orientation_euler, auto_orientation_area = _suggest_orientation(mesh, settings)
    flatness_deviation = _evaluate_surface_flatness(
        mesh,
        face_normals=face_normals,
        triangles_center=triangles_center,
        area_faces=area_faces,
    )
    if cavities_detected:
        issues.append(
            ValidationIssue(
                code="GEOM_CAVITIES",
                message="Detected internal cavities that may trap resin or powder.",
                severity="warning",
            )
        )
    if thin_tip_faces:
        issues.append(
            ValidationIssue(
                code="GEOM_THIN_TIP",
                message="Identified thin protrusions that may require support structures.",
                severity="warning",
            )
        )
    if high_aspect_ratio_faces:
        issues.append(
            ValidationIssue(
                code="GEOM_ASPECT_RATIO",
                message="Mesh contains long, slender triangles that may impair print quality.",
                severity="warning",
            )
        )
    if sharp_internal_corners:
        issues.append(
            ValidationIssue(
                code="GEOM_SHARP_INTERNAL_CORNER",
                message="Detected sharp internal corners that can concentrate stress during printing.",
                severity="warning",
            )
        )
    if (
        min_hole_diameter is not None
        and min_hole_diameter > 0.0
        and min_hole_diameter < settings.min_hole_diameter_mm
    ):
        issues.append(
            ValidationIssue(
                code="GEOM_SMALL_HOLE",
                message="Detected holes below the configured minimum diameter.",
                severity="warning",
            )
        )
    if surface_roughness_score > settings.max_surface_roughness_score:
        issues.append(
            ValidationIssue(
                code="GEOM_SURFACE_ROUGHNESS",
                message="Average surface roughness exceeds the configured limit.",
                severity="warning",
            )
        )
    if bed_contact_area < settings.min_bed_contact_area_mm2:
        issues.append(
            ValidationIssue(
                code="GEOM_BED_ADHESION",
                message="Bed contact area is below the configured minimum for adhesion.",
                severity="warning",
            )
        )
    if not scale_consistent:
        issues.append(
            ValidationIssue(
                code="GEOM_SCALE",
                message="Model extents fall outside the configured scale bounds.",
                severity="warning",
            )
        )

    if (
        flatness_deviation is not None
        and flatness_deviation > settings.max_flatness_deviation_mm
    ):
        issues.append(
            ValidationIssue(
                code="GEOM_FLATNESS",
                message=(
                    "Critical mating surfaces deviate from planarity beyond the configured limit."
                ),
                severity="warning",
            )
        )

    repair_suggestions = _generate_repair_suggestions(issues)
    if repair_suggestions:
        issues.append(
            ValidationIssue(
                code="GEOM_REPAIR_GUIDANCE",
                message="; ".join(repair_suggestions[:4]),
                severity="warning",
            )
        )

    if not _check_obj_material_groups(mesh, source_path):
        issues.append(
            ValidationIssue(
                code="GEOM_OBJ_MATERIAL",
                message="OBJ file is missing material assignments or definitions.",
                severity="warning",
            )
        )

    surface_area = float(mesh.area) if getattr(mesh, "area", None) is not None else 0.0
    raw_volume = float(mesh.volume) if is_volume and getattr(mesh, "volume", None) is not None else 0.0

    metrics = _compute_metrics(
        mesh,
        components=components,
        extents=extents,
        surface_area=surface_area,
        raw_volume=raw_volume,
        min_edge_length=min_edge_length,
        overhang_face_count=overhang_face_count,
        min_wall_thickness=min_wall_thickness or 0.0,
        center_of_gravity=center_of_gravity or [0.0, 0.0, 0.0],
        cavities_detected=cavities_detected,
        thin_tip_faces=thin_tip_faces,
        floating_shell_count=floating_shell_count,
        min_hole_diameter=min_hole_diameter or 0.0,
        high_aspect_ratio_faces=high_aspect_ratio_faces,
        sharp_internal_corners=sharp_internal_corners,
        surface_roughness_score=surface_roughness_score,
        bed_contact_area=bed_contact_area,
        scale_consistent=scale_consistent,
        auto_orientation_euler=auto_orientation_euler,
        auto_orientation_area=auto_orientation_area,
        flatness_deviation=flatness_deviation or 0.0,
        repair_suggestions=repair_suggestions,
        manifold_statistics=manifold_statistics,
        watertightness_statistics=watertightness_statistics,
    )

    # AI-powered defect detection
    ai_defects = []
    try:
        ai_detected_defects = detect_defects_with_ai(mesh)
        ai_defects = [defect.as_dict() for defect in ai_detected_defects]
    except Exception as exc:
        logging.warning(f"AI defect detection failed: {exc}")
        # Add a warning issue for AI failure
        issues.append(
            ValidationIssue(
                code="AI_DEFECT_DETECTION_FAILED",
                message=f"AI-powered defect detection failed: {str(exc)}",
                severity="warning",
            )
        )

    return MeshValidationResult(
        path=source_path,
        issues=issues,
        metrics=metrics,
        ai_defects=ai_defects
    )



def validate_file(path: Path, *, settings: Optional[MeshValidationSettings] = None) -> MeshValidationResult:
    """Load a mesh from *path* and validate it."""

    mesh = trimesh.load_mesh(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    return validate_mesh(mesh, settings=settings, source_path=Path(path))


def _detect_overhang_faces(
    mesh: trimesh.Trimesh,
    settings: MeshValidationSettings,
    *,
    face_normals: Optional[np.ndarray] = None,
    triangles_center: Optional[np.ndarray] = None,
    bounds: Optional[np.ndarray] = None,
) -> int:
    normals = face_normals if face_normals is not None else mesh.face_normals
    if normals.size == 0:
        return 0

    centers = triangles_center if triangles_center is not None else mesh.triangles_center
    if centers.size == 0:
        return 0

    mesh_bounds = bounds if bounds is not None else mesh.bounds
    min_z = float(mesh_bounds[0, 2]) if mesh_bounds is not None else 0.0

    # Vectorized computation without intermediate arrays
    z_normals = normals[:, 2]
    downward = z_normals < 0.0
    if not np.any(downward):
        return 0

    # Direct computation on filtered data
    cos_angles = np.abs(z_normals[downward])  # abs because z_normals are negative
    angles = np.degrees(np.arccos(np.clip(cos_angles, 0.0, 1.0)))

    # Combined condition check
    z_centers = centers[downward, 2]
    unsupported = (angles > settings.support_overhang_angle_deg) & (z_centers > min_z + 1e-3)

    return int(np.count_nonzero(unsupported))


def _estimate_min_wall_thickness(
    mesh: trimesh.Trimesh,
    *,
    max_samples: int = 400,
    epsilon_scale: float = 1e-4,
) -> Optional[float]:
    if mesh.is_volume is False or mesh.face_normals.size == 0:
        return None

    centers = mesh.triangles_center
    normals = mesh.face_normals
    face_count = len(centers)
    if face_count == 0:
        return None

    # Adaptive sampling based on model complexity
    sample_count = min(max_samples, face_count)
    if sample_count < face_count:
        # Use stratified sampling for better coverage
        indices = np.random.choice(face_count, sample_count, replace=False)
    else:
        indices = np.arange(face_count)

    extent_norm = float(np.linalg.norm(mesh.extents)) if mesh.extents is not None else 0.0
    epsilon = max(extent_norm * epsilon_scale, 1e-3)

    # Batch process ray intersections for better performance
    sampled_centers = centers[indices]
    sampled_normals = normals[indices]

    # Filter out invalid normals early
    valid_mask = np.linalg.norm(sampled_normals, axis=1) > 1e-10
    if not np.any(valid_mask):
        return None

    valid_centers = sampled_centers[valid_mask]
    valid_normals = sampled_normals[valid_mask]

    # Normalize directions
    directions = -valid_normals / np.linalg.norm(valid_normals, axis=1, keepdims=True)
    origins = valid_centers - directions * epsilon

    min_thickness = np.inf
    ray = mesh.ray

    # Process in batches for better cache utilization
    batch_size = 50
    for i in range(0, len(origins), batch_size):
        batch_end = min(i + batch_size, len(origins))
        batch_origins = origins[i:batch_end]
        batch_directions = directions[i:batch_end]

        locations, ray_indices, _ = ray.intersects_location(
            origins=batch_origins,
            directions=batch_directions,
        )

        if locations.size == 0:
            continue

        # Group by ray index for efficient processing
        for j in range(batch_end - i):
            ray_mask = ray_indices == j
            if not np.any(ray_mask):
                continue

            ray_locations = locations[ray_mask]
            distances = np.linalg.norm(ray_locations - batch_origins[j], axis=1)
            positive = distances > epsilon

            if np.any(positive):
                thickness = float(np.min(distances[positive]))
                min_thickness = min(min_thickness, thickness)

    if not np.isfinite(min_thickness):
        return None

    return min_thickness


def _has_self_intersections(mesh: trimesh.Trimesh) -> bool:
    try:
        return bool(mesh.is_self_intersecting)
    except BaseException:
        return False


def _compute_center_of_gravity(mesh: trimesh.Trimesh) -> Optional[List[float]]:
    if mesh.vertices.size == 0:
        return None

    try:
        center = mesh.center_mass
        if np.allclose(center, 0.0):
            return center.tolist()
        return center.tolist()
    except BaseException:
        pass

    try:
        return mesh.centroid.tolist()
    except BaseException:
        return None


def _analyze_sections(mesh: trimesh.Trimesh) -> Tuple[int, int, Optional[float]]:
    if mesh.vertices.size == 0:
        return (0, 0, None)

    axis_aligned = mesh.section_multiplane(
        plane_origin=mesh.centroid,
        plane_normal=[0, 0, 1],
        heights=np.linspace(mesh.bounds[0, 2], mesh.bounds[1, 2], num=6),
        cached=False,
    )

    cavities = 0
    thin_tip_faces = 0
    min_hole_diameter = np.inf

    for section in axis_aligned:
        if section is None or section.vertices.shape[0] == 0:
            continue
        try:
            polygons = section.polygons_full
        except BaseException:
            polygons = []
        for polygon in polygons:
            area = polygon.area
            if area < 1e-2:
                cavities += 1
            for interior in getattr(polygon, "interiors", []):
                coords = np.asarray(interior.coords)
                if coords.size == 0:
                    continue
                bounds = interior.bounds if hasattr(interior, "bounds") else None
                if bounds:
                    min_dim = min(bounds[2] - bounds[0], bounds[3] - bounds[1])
                else:
                    min_dim = float(np.linalg.norm(coords.max(axis=0) - coords.min(axis=0)))
                if min_dim > 0 and min_dim < min_hole_diameter:
                    min_hole_diameter = float(min_dim)

    normals = mesh.face_normals
    areas = mesh.area_faces
    magnitudes = np.linalg.norm(normals[:, :2], axis=1)
    thin_tip_faces = int(np.count_nonzero((areas < 1.0) & (magnitudes > 0.9)))

    if not np.isfinite(min_hole_diameter):
        min_hole_diameter = None

    return cavities, thin_tip_faces, min_hole_diameter


def _count_floating_shells(components: List[trimesh.Trimesh]) -> int:
    if not components or len(components) <= 1:
        return 0

    volumes = [float(comp.volume) if comp.is_volume else comp.area for comp in components]
    if not volumes:
        return 0

    primary_index = int(np.argmax(volumes))
    primary_bounds = components[primary_index].bounds

    floating = 0
    for index, component in enumerate(components):
        if index == primary_index:
            continue
        bounds = component.bounds
        if bounds is None or primary_bounds is None:
            floating += 1
            continue

        overlap = _bounds_overlap(primary_bounds, bounds)
        if not overlap:
            floating += 1

    return floating


def _bounds_overlap(a: np.ndarray, b: np.ndarray, *, tolerance: float = 1e-3) -> bool:
    if a is None or b is None:
        return False

    return not (
        (a[1, 0] + tolerance < b[0, 0])
        or (b[1, 0] + tolerance < a[0, 0])
        or (a[1, 1] + tolerance < b[0, 1])
        or (b[1, 1] + tolerance < a[0, 1])
        or (a[1, 2] + tolerance < b[0, 2])
        or (b[1, 2] + tolerance < a[0, 2])
    )


def _count_high_aspect_ratio_faces(mesh: trimesh.Trimesh, threshold: float = 10.0) -> int:
    if mesh.faces.size == 0:
        return 0

    edges = mesh.edges_face
    edge_lengths = mesh.edges_unique_length
    if edges.size == 0 or edge_lengths.size == 0:
        return 0

    # Vectorized computation using advanced indexing
    lengths = edge_lengths[mesh.edges_unique_inverse[edges]]

    # Use numpy's ptp (peak to peak) for efficiency
    with np.errstate(divide='ignore', invalid='ignore'):
        long_edges = np.max(lengths, axis=1)
        short_edges = np.min(lengths, axis=1)
        ratios = np.where(short_edges > 0, long_edges / short_edges, 0)

    return int(np.count_nonzero(ratios > threshold))


def _count_sharp_internal_corners(mesh: trimesh.Trimesh, angle_threshold_deg: float = 60.0) -> int:
    if mesh.face_adjacency_angles.size == 0:
        return 0

    angles = np.degrees(mesh.face_adjacency_angles)
    adjacency = mesh.face_adjacency
    if adjacency.size == 0:
        return 0

    normals = mesh.face_normals
    internal_mask = []
    for face_pair in adjacency:
        normal_a = normals[face_pair[0]]
        normal_b = normals[face_pair[1]]
        cross = np.cross(normal_a, normal_b)
        internal_mask.append(cross[2] <= 0)

    internal_mask = np.array(internal_mask)
    sharp = (angles < angle_threshold_deg) & internal_mask

    return int(np.count_nonzero(sharp))


def _estimate_surface_roughness(mesh: trimesh.Trimesh) -> float:
    angles = getattr(mesh, "face_adjacency_angles", None)
    if angles is None or angles.size == 0:
        return 0.0

    return float(np.mean(np.abs(angles)))


def _measure_bed_contact_area(
    mesh: trimesh.Trimesh,
    *,
    face_normals: Optional[np.ndarray] = None,
    triangles_center: Optional[np.ndarray] = None,
    area_faces: Optional[np.ndarray] = None,
    bounds: Optional[np.ndarray] = None,
    extents: Optional[np.ndarray] = None,
    normal_threshold: float = -0.5,
    distance_epsilon: float = 1e-3,
) -> float:
    normals = face_normals if face_normals is not None else mesh.face_normals
    areas = area_faces if area_faces is not None else mesh.area_faces
    centers = triangles_center if triangles_center is not None else mesh.triangles_center

    if normals.size == 0 or areas.size == 0:
        return 0.0

    mesh_bounds = bounds if bounds is not None else mesh.bounds
    if mesh_bounds is None:
        return 0.0

    min_z = float(mesh_bounds[0, 2])
    mesh_extents = extents if extents is not None else mesh.extents
    extent_norm = float(np.linalg.norm(mesh_extents)) if mesh_extents is not None else 0.0
    tolerance = distance_epsilon + 1e-3 * extent_norm

    downward = normals[:, 2] <= normal_threshold
    near_bed = np.abs(centers[:, 2] - min_z) <= tolerance

    mask = downward & near_bed
    if not np.any(mask):
        return 0.0

    return float(np.sum(areas[mask]))

def _is_scale_consistent(
    mesh: trimesh.Trimesh,
    settings: MeshValidationSettings,
    *,
    bounds: Optional[np.ndarray] = None,
    extents: Optional[np.ndarray] = None,
) -> bool:
    mesh_bounds = bounds if bounds is not None else mesh.bounds
    if mesh_bounds is None:
        return True

    mesh_extents = extents if extents is not None else mesh.extents
    mesh_extents = mesh_extents if mesh_extents is not None else np.zeros(3)
    max_extent = float(np.max(mesh_extents)) if mesh_extents.size else 0.0
    positive_extents = mesh_extents[mesh_extents > 0]
    min_extent = float(np.min(positive_extents)) if positive_extents.size else 0.0

    if max_extent == 0.0:
        return True

    if max_extent > settings.max_model_extent_mm:
        return False
    if min_extent and min_extent < settings.min_model_extent_mm:
        return False

    return True


def _suggest_orientation(
    mesh: trimesh.Trimesh, settings: MeshValidationSettings
) -> Tuple[List[float], float]:
    try:
        inertia = mesh.principal_inertia_vectors
    except BaseException:
        inertia = None

    base_transform = _IDENTITY4
    if inertia is not None:
        try:
            align = trimesh.geometry.align_vectors(inertia[2], np.array([0.0, 0.0, 1.0]))
            if align is not None:
                base_transform = align
        except BaseException:
            base_transform = _IDENTITY4

    candidate_angles = [0.0, 90.0, 180.0, 270.0]
    best_area = -1.0
    best_overhang = float("inf")
    best_euler: List[float] = [0.0, 0.0, 0.0]

    for angle in candidate_angles:
        rotation = trimesh.transformations.rotation_matrix(
            np.radians(angle), [0.0, 0.0, 1.0]
        )
        transform = base_transform @ rotation
        oriented = mesh.copy()
        oriented.apply_transform(transform)

        area = _measure_bed_contact_area(oriented)
        overhang = _detect_overhang_faces(oriented, settings)

        if (area > best_area) or (np.isclose(area, best_area) and overhang < best_overhang):
            best_area = area
            best_overhang = overhang
            try:
                euler = trimesh.transformations.euler_from_matrix(transform, "sxyz")
                best_euler = [float(np.degrees(value)) for value in euler[:3]]
            except BaseException:
                best_euler = [0.0, 0.0, angle]

    if best_area < 0.0:
        best_area = 0.0

    return best_euler, float(best_area)


def _check_obj_material_groups(
    mesh: trimesh.Trimesh, source_path: Optional[Path]
) -> bool:
    if source_path is None or source_path.suffix.lower() != ".obj":
        return True

    visual = getattr(mesh, "visual", None)
    if visual is None:
        return False

    material = getattr(visual, "material", None)
    face_materials = getattr(visual, "face_materials", None)
    uv = getattr(visual, "uv", None)

    has_material = material is not None
    has_face_materials = False
    if face_materials is not None:
        try:
            has_face_materials = bool(len(face_materials) and not np.all(face_materials == -1))
        except BaseException:
            has_face_materials = True

    has_uv = uv is not None and len(uv) > 0

    return bool(has_material or has_face_materials or has_uv)


def _evaluate_surface_flatness(
    mesh: trimesh.Trimesh,
    *,
    face_normals: Optional[np.ndarray] = None,
    triangles_center: Optional[np.ndarray] = None,
    area_faces: Optional[np.ndarray] = None,
    alignment_threshold: float = 0.95,
) -> float:
    normals = face_normals if face_normals is not None else mesh.face_normals
    if normals.size == 0:
        return 0.0

    centers = triangles_center if triangles_center is not None else mesh.triangles_center
    areas_array = area_faces if area_faces is not None else mesh.area_faces
    areas = areas_array if areas_array.size else None

    max_deviation = 0.0
    axes = np.eye(3)

    for axis in axes:
        alignment = np.abs(normals @ axis)
        mask = alignment >= alignment_threshold
        if not np.any(mask):
            continue

        candidate_centers = centers[mask]
        if candidate_centers.size == 0:
            continue

        axis_coordinates = candidate_centers @ axis
        if axis_coordinates.size == 0:
            continue

        if areas is not None and areas.size == normals.shape[0]:
            weights = areas[mask]
            weight_sum = float(np.sum(weights))
            if weight_sum > 0.0:
                reference = float(np.average(axis_coordinates, weights=weights))
            else:
                reference = float(np.mean(axis_coordinates))
        else:
            reference = float(np.mean(axis_coordinates))

        deviation = float(np.max(np.abs(axis_coordinates - reference)))
        if deviation > max_deviation:
            max_deviation = deviation

    return max_deviation


def _generate_repair_suggestions(issues: Iterable[ValidationIssue]) -> List[str]:
    mapping = {
        "GEOM_EMPTY": "Confirm the mesh export step produced triangles before importing again.",
        "GEOM_WATERTIGHT": "Fill open boundaries or close gaps to obtain a watertight shell.",
        "GEOM_WINDING": "Recalculate face winding to maintain consistent outward normals.",
        "GEOM_VOLUME": "Merge disconnected faces so the mesh encloses a valid volume.",
        "GEOM_MANIFOLD_VALIDATION_FAILED": "Resolve manifold defects and retry the advanced validator.",
        "GEOM_WATERTIGHTNESS_VALIDATION_FAILED": "Inspect mesh topology and rerun watertightness analysis.",
        "GEOM_MULTIPLE_COMPONENTS": "Join disconnected bodies or export individual parts separately.",
        "GEOM_FLOATING_SHELL": "Eliminate detached shells or connect them with robust struts.",
        "GEOM_SELF_INTERSECTION": "Remove self-intersecting triangles using boolean cleanup operations.",
        "GEOM_SMALL_FEATURE": "Thicken fine details beyond the minimum printable feature size.",
        "GEOM_OVERHANG": "Adjust orientation or add supports for faces exceeding the overhang limit.",
        "GEOM_WALL_THICKNESS": "Reinforce thin walls to meet the configured wall thickness target.",
        "GEOM_CAVITIES": "Provide drain holes or hollowing vents to avoid trapped material.",
        "GEOM_THIN_TIP": "Support delicate protrusions or increase their cross-section.",
        "GEOM_ASPECT_RATIO": "Retopologize long skinny triangles into well-shaped facets.",
        "GEOM_SHARP_INTERNAL_CORNER": "Round internal corners to reduce stress concentration during printing.",
        "GEOM_SMALL_HOLE": "Scale or drill holes so their diameter exceeds the minimum threshold.",
        "GEOM_SURFACE_ROUGHNESS": "Smooth the surface or adjust resolution to reduce roughness.",
        "GEOM_BED_ADHESION": "Increase the first-layer contact patch or add a brim for adhesion.",
        "GEOM_SCALE": "Rescale the model into the allowable build volume before slicing.",
        "GEOM_FLATNESS": "Planarize critical mating faces to stay within the flatness tolerance.",
        "GEOM_OBJ_MATERIAL": "Assign materials and UV sets before exporting the OBJ file.",
    }

    suggestions: List[str] = []
    seen: set[str] = set()
    for issue in issues:
        suggestion = mapping.get(issue.code)
        if suggestion and suggestion not in seen:
            suggestions.append(suggestion)
            seen.add(suggestion)

    return suggestions


def _extend_unique_issues(target: List[ValidationIssue], new_issues: Iterable[ValidationIssue]) -> None:
    existing_codes = {issue.code for issue in target}
    for issue in new_issues:
        if issue.code not in existing_codes:
            target.append(issue)
            existing_codes.add(issue.code)


def _summarize_manifold_result(result: ManifoldValidationResult) -> Dict[str, Any]:
    return {
        "is_manifold": result.is_manifold,
        "edge_statistics": result.edge_statistics,
        "face_statistics": result.face_statistics,
        "vertex_statistics": result.vertex_statistics,
        "scaling_analysis": result.scaling_analysis,
        "coordinate_system_analysis": result.coordinate_system_analysis,
    }


def _summarize_watertightness_result(result: WatertightnessResult) -> Dict[str, Any]:
    return {
        "is_watertight": result.is_watertight,
        "is_solid": result.is_solid,
        "volume": result.volume,
        "boundary_info": result.boundary_info,
        "component_info": result.component_info,
        "hole_info": result.hole_info,
        "gap_analysis": result.gap_analysis,
        "shell_thickness_info": result.shell_thickness_info,
    }
