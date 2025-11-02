"""Advanced support generation with AI optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
import trimesh
from enum import Enum
import logging
import time
from scipy.spatial import cKDTree


class SupportType(Enum):
    """Types of support structures."""
    TREE = "tree"                  # Tree-like supports
    LINEAR = "linear"              # Linear supports
    GRID = "grid"                 # Grid pattern supports
    HYBRID = "hybrid"             # Mixed approach
    CUSTOM = "custom"             # User-defined


class SupportMaterial(Enum):
    """Support material types."""
    SAME_AS_MODEL = "same_as_model"
    SOLUBLE = "soluble"
    BREAKAWAY = "breakaway"
    DISSOLVABLE = "dissolvable"


@dataclass
class SupportStructure:
    """A support structure."""
    geometry: trimesh.Trimesh
    contact_points: np.ndarray
    support_type: SupportType
    material: SupportMaterial
    estimated_volume: float
    estimated_print_time: float
    removable: bool = True


@dataclass
class OverhangRegion:
    """A region requiring support."""
    faces: np.ndarray  # Face indices
    centroid: np.ndarray
    area: float
    max_angle: float  # Maximum overhang angle
    priority: float  # Support priority (0-1)


@dataclass
class SupportGenerationSettings:
    """Settings for support generation."""
    support_type: SupportType = SupportType.TREE
    material: SupportMaterial = SupportMaterial.BREAKAWAY
    overhang_angle_threshold: float = 45.0  # Degrees
    min_support_area: float = 1.0  # mm²
    max_support_spacing: float = 10.0  # mm
    support_density: float = 15  # %
    contact_point_density: float = 0.5  # points per mm²
    base_thickness: float = 0.3  # mm
    pillar_diameter: float = 1.0  # mm
    optimize_for_removal: bool = True
    minimize_volume: bool = True


@dataclass
class SupportGenerationResult:
    """Result of support generation."""
    model_mesh: trimesh.Trimesh
    support_structures: List[SupportStructure] = field(default_factory=list)
    overhang_regions: List[OverhangRegion] = field(default_factory=list)
    total_support_volume: float = 0.0
    total_support_time: float = 0.0
    support_ratio: float = 0.0  # Support volume / model volume
    optimization_score: float = 0.0
    generation_time: float = 0.0


class AdvancedSupportGenerator:
    """Advanced support generation with AI optimization."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_supports(self, mesh: trimesh.Trimesh,
                         settings: SupportGenerationSettings) -> SupportGenerationResult:
        """Generate optimized support structures for 3D printing."""

        start_time = time.time()
        result = SupportGenerationResult(model_mesh=mesh)

        try:
            # Identify overhang regions
            overhang_regions = self._identify_overhangs(mesh, settings)
            result.overhang_regions = overhang_regions

            if not overhang_regions:
                self.logger.info("No overhang regions requiring support found")
                result.generation_time = time.time() - start_time
                return result

            # Generate support structures based on type
            if settings.support_type == SupportType.TREE:
                supports = self._generate_tree_supports(mesh, overhang_regions, settings)
            elif settings.support_type == SupportType.LINEAR:
                supports = self._generate_linear_supports(mesh, overhang_regions, settings)
            elif settings.support_type == SupportType.GRID:
                supports = self._generate_grid_supports(mesh, overhang_regions, settings)
            elif settings.support_type == SupportType.HYBRID:
                supports = self._generate_hybrid_supports(mesh, overhang_regions, settings)
            else:
                supports = self._generate_linear_supports(mesh, overhang_regions, settings)

            result.support_structures = supports

            # Calculate totals
            total_volume = sum(s.estimated_volume for s in supports)
            total_time = sum(s.estimated_print_time for s in supports)

            result.total_support_volume = total_volume
            result.total_support_time = total_time

            # Calculate ratios
            model_volume = mesh.volume if mesh.is_watertight else mesh.area * 1.0  # Rough estimate
            if model_volume > 0:
                result.support_ratio = total_volume / model_volume

            # Calculate optimization score
            result.optimization_score = self._calculate_optimization_score(result, settings)

            result.generation_time = time.time() - start_time

        except Exception as e:
            self.logger.error(f"Support generation failed: {e}")
            result.generation_time = time.time() - start_time

        return result

    def _identify_overhangs(self, mesh: trimesh.Trimesh,
                          settings: SupportGenerationSettings) -> List[OverhangRegion]:
        """Identify regions requiring support."""

        overhang_regions = []

        try:
            # Get face normals and centers
            face_normals = mesh.face_normals
            face_centers = mesh.triangles_center
            face_areas = mesh.area_faces

            # Calculate angles with vertical (Z-axis)
            vertical = np.array([0, 0, 1])
            cos_angles = np.abs(np.dot(face_normals, vertical))
            angles_deg = np.degrees(np.arccos(np.clip(cos_angles, -1, 1)))

            # Find faces exceeding overhang threshold
            overhang_mask = angles_deg > settings.overhang_angle_threshold
            overhang_faces = np.where(overhang_mask)[0]

            if len(overhang_faces) == 0:
                return overhang_regions

            # Group nearby faces into regions
            regions = self._group_overhang_faces(
                overhang_faces, face_centers, face_areas, angles_deg, settings
            )

            for region_faces, centroid, area, max_angle in regions:
                # Calculate priority based on area and angle
                angle_priority = (max_angle - settings.overhang_angle_threshold) / (90 - settings.overhang_angle_threshold)
                area_priority = min(area / 100.0, 1.0)  # Normalize area
                priority = (angle_priority + area_priority) / 2.0

                region = OverhangRegion(
                    faces=region_faces,
                    centroid=centroid,
                    area=area,
                    max_angle=max_angle,
                    priority=priority
                )
                overhang_regions.append(region)

            # Sort by priority
            overhang_regions.sort(key=lambda r: r.priority, reverse=True)

        except Exception as e:
            self.logger.warning(f"Error identifying overhangs: {e}")

        return overhang_regions

    def _group_overhang_faces(self, overhang_faces: np.ndarray, face_centers: np.ndarray,
                            face_areas: np.ndarray, angles_deg: np.ndarray,
                            settings: SupportGenerationSettings) -> List[Tuple[np.ndarray, np.ndarray, float, float]]:
        """Group nearby overhang faces into regions."""

        regions = []
        processed_faces = set()

        # Build KDTree for efficient neighbor search
        overhang_centers = face_centers[overhang_faces]
        tree = cKDTree(overhang_centers)

        max_spacing = settings.max_support_spacing

        for i, face_idx in enumerate(overhang_faces):
            if face_idx in processed_faces:
                continue

            # Find nearby faces
            neighbors = tree.query_ball_point(overhang_centers[i], max_spacing)
            region_faces = overhang_faces[neighbors]

            # Filter out already processed faces
            region_faces = np.array([f for f in region_faces if f not in processed_faces])

            if len(region_faces) == 0:
                continue

            # Mark as processed
            processed_faces.update(region_faces)

            # Calculate region properties
            region_centers = face_centers[region_faces]
            region_areas = face_areas[region_faces]
            region_angles = angles_deg[region_faces]

            # Centroid weighted by area
            total_area = np.sum(region_areas)
            centroid = np.average(region_centers, weights=region_areas, axis=0)

            max_angle = np.max(region_angles)

            regions.append((region_faces, centroid, total_area, max_angle))

        return regions

    def _generate_tree_supports(self, mesh: trimesh.Trimesh,
                              overhang_regions: List[OverhangRegion],
                              settings: SupportGenerationSettings) -> List[SupportStructure]:
        """Generate tree-like support structures."""

        supports = []

        try:
            # Tree supports grow from build plate up to overhang regions
            build_plate_z = mesh.bounds[0][2] - 0.1  # Slightly below model

            for region in overhang_regions:
                if region.area < settings.min_support_area:
                    continue

                # Create tree trunk
                trunk_height = region.centroid[2] - build_plate_z
                trunk = self._create_support_pillar(
                    np.array([region.centroid[0], region.centroid[1], build_plate_z]),
                    np.array([region.centroid[0], region.centroid[1], region.centroid[2]]),
                    settings.pillar_diameter
                )

                # Create branches to contact points
                contact_points = self._generate_contact_points(region, settings)

                branches = []
                for contact_point in contact_points:
                    branch_start = np.array([
                        region.centroid[0],
                        region.centroid[1],
                        region.centroid[2] - trunk_height * 0.3  # Start branch 30% from top
                    ])
                    branch = self._create_support_pillar(branch_start, contact_point, settings.pillar_diameter * 0.7)
                    branches.append(branch)

                # Combine into tree structure
                tree_parts = [trunk] + branches
                tree_geometry = trimesh.util.concatenate(tree_parts)

                support = SupportStructure(
                    geometry=tree_geometry,
                    contact_points=np.array([cp for cp in contact_points]),
                    support_type=SupportType.TREE,
                    material=settings.material,
                    estimated_volume=float(tree_geometry.volume) if tree_geometry.is_watertight else float(tree_geometry.area * 0.1),
                    estimated_print_time=self._estimate_print_time(tree_geometry, settings)
                )

                supports.append(support)

        except Exception as e:
            self.logger.warning(f"Error generating tree supports: {e}")

        return supports

    def _generate_linear_supports(self, mesh: trimesh.Trimesh,
                                overhang_regions: List[OverhangRegion],
                                settings: SupportGenerationSettings) -> List[SupportStructure]:
        """Generate linear support structures."""

        supports = []

        try:
            build_plate_z = mesh.bounds[0][2] - 0.1

            for region in overhang_regions:
                if region.area < settings.min_support_area:
                    continue

                # Generate contact points
                contact_points = self._generate_contact_points(region, settings)

                # Create pillars from build plate to contact points
                pillars = []
                for contact_point in contact_points:
                    pillar = self._create_support_pillar(
                        np.array([contact_point[0], contact_point[1], build_plate_z]),
                        contact_point,
                        settings.pillar_diameter
                    )
                    pillars.append(pillar)

                if pillars:
                    # Combine pillars
                    support_geometry = trimesh.util.concatenate(pillars)

                    support = SupportStructure(
                        geometry=support_geometry,
                        contact_points=np.array(contact_points),
                        support_type=SupportType.LINEAR,
                        material=settings.material,
                        estimated_volume=float(support_geometry.volume) if support_geometry.is_watertight else float(support_geometry.area * 0.1),
                        estimated_print_time=self._estimate_print_time(support_geometry, settings)
                    )

                    supports.append(support)

        except Exception as e:
            self.logger.warning(f"Error generating linear supports: {e}")

        return supports

    def _generate_grid_supports(self, mesh: trimesh.Trimesh,
                              overhang_regions: List[OverhangRegion],
                              settings: SupportGenerationSettings) -> List[SupportStructure]:
        """Generate grid pattern support structures."""

        supports = []

        try:
            # Create a grid base under the entire model
            bounds = mesh.bounds
            grid_z = bounds[0][2] - 0.1

            # Grid parameters
            spacing = settings.max_support_spacing
            grid_min_x, grid_max_x = bounds[0][0] - 5, bounds[1][0] + 5
            grid_min_y, grid_max_y = bounds[0][1] - 5, bounds[1][1] + 5

            # Create grid lines
            grid_lines = []

            # X-direction lines
            for y in np.arange(grid_min_y, grid_max_y + spacing, spacing):
                line = trimesh.creation.cylinder(
                    radius=settings.pillar_diameter * 0.3,
                    height=grid_max_x - grid_min_x + 10
                )
                # Rotate and position
                line.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
                line.apply_translation([
                    (grid_min_x + grid_max_x) / 2,
                    y,
                    grid_z + 5  # Half height
                ])
                grid_lines.append(line)

            # Y-direction lines
            for x in np.arange(grid_min_x, grid_max_x + spacing, spacing):
                line = trimesh.creation.cylinder(
                    radius=settings.pillar_diameter * 0.3,
                    height=grid_max_y - grid_min_y + 10
                )
                # Rotate and position
                line.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
                line.apply_translation([
                    x,
                    (grid_min_y + grid_max_y) / 2,
                    grid_z + 5  # Half height
                ])
                grid_lines.append(line)

            if grid_lines:
                grid_geometry = trimesh.util.concatenate(grid_lines)

                support = SupportStructure(
                    geometry=grid_geometry,
                    contact_points=np.array([]),  # Grid supports don't have specific contact points
                    support_type=SupportType.GRID,
                    material=settings.material,
                    estimated_volume=float(grid_geometry.volume) if grid_geometry.is_watertight else float(grid_geometry.area * 0.1),
                    estimated_print_time=self._estimate_print_time(grid_geometry, settings)
                )

                supports.append(support)

        except Exception as e:
            self.logger.warning(f"Error generating grid supports: {e}")

        return supports

    def _generate_hybrid_supports(self, mesh: trimesh.Trimesh,
                                overhang_regions: List[OverhangRegion],
                                settings: SupportGenerationSettings) -> List[SupportStructure]:
        """Generate hybrid support structures."""

        # Combine tree and linear supports
        tree_supports = self._generate_tree_supports(mesh, overhang_regions[:len(overhang_regions)//2], settings)
        linear_supports = self._generate_linear_supports(mesh, overhang_regions[len(overhang_regions)//2:], settings)

        return tree_supports + linear_supports

    def _generate_contact_points(self, region: OverhangRegion,
                               settings: SupportGenerationSettings) -> List[np.ndarray]:
        """Generate contact points for a support region."""

        contact_points = []

        try:
            # Calculate number of contact points based on area and density
            num_points = max(1, int(region.area * settings.contact_point_density))

            # Get face centers for the region
            # This is simplified - in practice, we'd get actual face centers
            center = region.centroid

            if num_points == 1:
                # Single contact point
                contact_points.append(center)
            else:
                # Multiple contact points in a pattern
                # Simple circular pattern
                radius = np.sqrt(region.area / np.pi) * 0.5
                angles = np.linspace(0, 2*np.pi, num_points, endpoint=False)

                for angle in angles:
                    offset = np.array([
                        radius * np.cos(angle),
                        radius * np.sin(angle),
                        0
                    ])
                    contact_point = center + offset
                    contact_points.append(contact_point)

        except Exception as e:
            self.logger.warning(f"Error generating contact points: {e}")
            # Fallback to region centroid
            contact_points.append(region.centroid)

        return contact_points

    def _create_support_pillar(self, start_point: np.ndarray, end_point: np.ndarray,
                             diameter: float) -> trimesh.Trimesh:
        """Create a cylindrical support pillar."""

        try:
            direction = end_point - start_point
            height = np.linalg.norm(direction)

            if height < 0.1:  # Too short
                return trimesh.Trimesh()

            # Create cylinder along Z axis
            cylinder = trimesh.creation.cylinder(radius=diameter/2, height=height)

            # Calculate rotation to align with direction
            z_axis = np.array([0, 0, 1])
            rotation_axis = np.cross(z_axis, direction)
            rotation_angle = np.arccos(np.dot(z_axis, direction) / height)

            if np.linalg.norm(rotation_axis) > 1e-6:
                rotation_matrix = trimesh.transformations.rotation_matrix(
                    rotation_angle, rotation_axis
                )
                cylinder.apply_transform(rotation_matrix)

            # Translate to start position
            cylinder.apply_translation(start_point)

            return cylinder

        except Exception as e:
            self.logger.warning(f"Error creating support pillar: {e}")
            return trimesh.Trimesh()

    def _estimate_print_time(self, support_geometry: trimesh.Trimesh,
                           settings: SupportGenerationSettings) -> float:
        """Estimate print time for support structure."""

        try:
            # Rough estimation based on volume and density
            volume = support_geometry.volume if support_geometry.is_watertight else support_geometry.area * 0.1
            density = settings.support_density / 100.0

            # Assume standard print parameters
            layer_height = 0.2
            print_speed = 50  # mm/min

            # Calculate extruded volume
            extruded_volume = volume * density

            # Estimate time (highly simplified)
            time_minutes = extruded_volume / (print_speed * layer_height * 60)

            return time_minutes

        except Exception:
            return 0.0

    def _calculate_optimization_score(self, result: SupportGenerationResult,
                                    settings: SupportGenerationSettings) -> float:
        """Calculate optimization score for support structures."""

        score = 0.5  # Base score

        try:
            # Score based on volume efficiency
            if result.support_ratio < 0.3:  # Less than 30% support volume
                score += 0.2
            elif result.support_ratio > 1.0:  # More than 100% support volume
                score -= 0.3

            # Score based on removal optimization
            if settings.optimize_for_removal:
                # Tree supports are easier to remove
                tree_supports = sum(1 for s in result.support_structures if s.support_type == SupportType.TREE)
                if tree_supports > 0:
                    score += 0.1

            # Score based on number of supports (fewer is better)
            if len(result.support_structures) < 10:
                score += 0.1
            elif len(result.support_structures) > 50:
                score -= 0.1

            # Score based on overhang coverage
            if result.overhang_regions:
                covered_area = sum(s.estimated_volume for s in result.support_structures) * 10  # Rough estimate
                total_overhang_area = sum(r.area for r in result.overhang_regions)
                coverage_ratio = min(covered_area / total_overhang_area, 1.0)
                score += coverage_ratio * 0.1

        except Exception as e:
            self.logger.warning(f"Error calculating optimization score: {e}")

        return np.clip(score, 0.0, 1.0)

    def optimize_support_layout(self, mesh: trimesh.Trimesh,
                              initial_result: SupportGenerationResult,
                              settings: SupportGenerationSettings) -> SupportGenerationResult:
        """Optimize support layout using AI techniques."""

        # This would implement optimization algorithms to minimize support volume
        # while maintaining structural integrity

        # For now, return the initial result
        self.logger.info("Support layout optimization not fully implemented yet")
        return initial_result


# Global instance
advanced_support_generator = AdvancedSupportGenerator()


def generate_advanced_supports(mesh: trimesh.Trimesh,
                             settings: Optional[SupportGenerationSettings] = None) -> SupportGenerationResult:
    """Convenience function for advanced support generation."""
    if settings is None:
        settings = SupportGenerationSettings()

    return advanced_support_generator.generate_supports(mesh, settings)


def optimize_support_layout(mesh: trimesh.Trimesh,
                          initial_supports: SupportGenerationResult,
                          settings: Optional[SupportGenerationSettings] = None) -> SupportGenerationResult:
    """Convenience function for support layout optimization."""
    if settings is None:
        settings = SupportGenerationSettings()

    return advanced_support_generator.optimize_support_layout(mesh, initial_supports, settings)
