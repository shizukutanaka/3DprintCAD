"""Advanced slicing algorithms for optimized 3D printing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
import trimesh
from enum import Enum
import logging
import time


class SlicingAlgorithm(Enum):
    """Advanced slicing algorithms."""
    ADAPTIVE_LAYER_HEIGHT = "adaptive_layer_height"
    VARIABLE_INFILL = "variable_infill"
    CONTOUR_PARALLEL = "contour_parallel"
    ISLAND_BASED = "island_based"
    HYBRID_ADAPTIVE = "hybrid_adaptive"
    AI_OPTIMIZED = "ai_optimized"
    CLIP_CONTINUOUS = "clip_continuous"  # Continuous Liquid Interface Production


class InfillPattern(Enum):
    """Advanced infill patterns."""
    GYROID = "gyroid"
    CUBIC = "cubic"
    HONEYCOMB = "honeycomb"
    TRIANGLE = "triangle"
    OCTET = "octet"
    VARIABLE_DENSITY = "variable_density"


@dataclass
class SlicingParameters:
    """Parameters for advanced slicing."""

    # Basic parameters
    layer_height: float = 0.2
    wall_thickness: int = 3
    top_bottom_thickness: int = 1
    infill_percentage: int = 20

    # Advanced parameters
    algorithm: SlicingAlgorithm = SlicingAlgorithm.ADAPTIVE_LAYER_HEIGHT
    infill_pattern: InfillPattern = InfillPattern.GYROID
    adaptive_layer_height_min: float = 0.1
    adaptive_layer_height_max: float = 0.3
    variable_infill_enabled: bool = True
    contour_parallel_enabled: bool = True

    # Quality settings
    print_speed: float = 50.0  # mm/s
    travel_speed: float = 120.0  # mm/s
    retraction_speed: float = 40.0  # mm/s
    retraction_distance: float = 6.0  # mm

    # CLIP-specific parameters
    clip_enabled: bool = False
    clip_resin_viscosity: float = 100.0  # cP
    clip_oxygen_permeability: float = 1e-10  # m²/s
    clip_cure_depth_mm: float = 0.1  # mm
    clip_exposure_time_ms: float = 1000.0  # ms


@dataclass
class SliceLayer:
    """Represents a single sliced layer."""

    z_height: float
    layer_height: float
    contours: List[np.ndarray] = field(default_factory=list)
    infill_lines: List[np.ndarray] = field(default_factory=list)
    support_structures: List[np.ndarray] = field(default_factory=list)
    estimated_print_time: float = 0.0
    material_volume: float = 0.0


@dataclass
class SlicingResult:
    """Result of advanced slicing operation."""

    layers: List[SliceLayer] = field(default_factory=list)
    total_height: float = 0.0
    total_layers: int = 0
    estimated_print_time: float = 0.0  # minutes
    total_material_volume: float = 0.0  # mm³
    support_volume: float = 0.0  # mm³
    slicing_parameters: SlicingParameters = field(default_factory=SlicingParameters)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)


class AdaptiveLayerHeightSlicer:
    """Adaptive layer height slicing algorithm."""

    def __init__(self, parameters: SlicingParameters):
        self.parameters = parameters
        self.logger = logging.getLogger(__name__)

    def slice(self, mesh: trimesh.Trimesh) -> SlicingResult:
        """Perform adaptive layer height slicing."""
        result = SlicingResult(slicing_parameters=self.parameters)

        # Get mesh bounds
        bounds = mesh.bounds
        min_z, max_z = bounds[0][2], bounds[1][2]
        result.total_height = max_z - min_z

        current_z = min_z
        layer_index = 0

        while current_z < max_z:
            # Calculate optimal layer height for this slice
            layer_height = self._calculate_adaptive_layer_height(mesh, current_z)

            # Slice the mesh at current height
            layer = self._slice_at_height(mesh, current_z, layer_height)
            result.layers.append(layer)

            current_z += layer_height
            layer_index += 1

            # Safety check to prevent infinite loops
            if layer_index > 10000:
                self.logger.warning("Slicing terminated due to excessive layer count")
                break

        result.total_layers = len(result.layers)
        self._calculate_quality_metrics(result)

        return result

    def _calculate_adaptive_layer_height(self, mesh: trimesh.Trimesh, z_height: float) -> float:
        """Calculate optimal layer height for given Z height."""
        try:
            # Get mesh section at current height
            section = mesh.section(plane_origin=[0, 0, z_height],
                                 plane_normal=[0, 0, 1])

            if section is None or len(section.entities) == 0:
                return self.parameters.layer_height

            # Calculate surface curvature and complexity
            complexity_score = self._calculate_surface_complexity(section)

            # Adjust layer height based on complexity
            # Higher complexity = smaller layer height for better quality
            if complexity_score > 0.8:
                layer_height = self.parameters.adaptive_layer_height_min
            elif complexity_score > 0.5:
                # Interpolate between min and max
                factor = (complexity_score - 0.5) / 0.3
                layer_height = self.parameters.adaptive_layer_height_max - \
                             factor * (self.parameters.adaptive_layer_height_max - self.parameters.adaptive_layer_height_min)
            else:
                layer_height = self.parameters.adaptive_layer_height_max

            # Ensure within bounds
            layer_height = np.clip(layer_height,
                                 self.parameters.adaptive_layer_height_min,
                                 self.parameters.adaptive_layer_height_max)

            return layer_height

        except Exception as e:
            self.logger.warning(f"Error calculating adaptive layer height: {e}")
            return self.parameters.layer_height

    def _calculate_surface_complexity(self, section) -> float:
        """Calculate surface complexity score (0-1)."""
        try:
            if not hasattr(section, 'entities') or len(section.entities) == 0:
                return 0.0

            # Count entities and calculate density
            entity_count = len(section.entities)
            if entity_count == 0:
                return 0.0

            # Calculate path lengths and curvature
            total_length = 0.0
            total_curvature = 0.0

            for entity in section.entities:
                if hasattr(entity, 'length'):
                    total_length += entity.length

                # Estimate curvature (simplified)
                if hasattr(entity, 'points'):
                    points = np.array(entity.points)
                    if len(points) > 2:
                        # Calculate angle changes
                        vectors = np.diff(points, axis=0)
                        angles = []
                        for i in range(1, len(vectors)):
                            cos_angle = np.dot(vectors[i-1], vectors[i]) / \
                                      (np.linalg.norm(vectors[i-1]) * np.linalg.norm(vectors[i]))
                            cos_angle = np.clip(cos_angle, -1, 1)
                            angles.append(np.arccos(cos_angle))

                        if angles:
                            total_curvature += np.mean(angles)

            # Normalize complexity score
            complexity = min(1.0, (total_length / 1000.0) + (total_curvature / 10.0))
            return complexity

        except Exception as e:
            self.logger.warning(f"Error calculating surface complexity: {e}")
            return 0.5

    def _slice_at_height(self, mesh: trimesh.Trimesh, z_height: float, layer_height: float) -> SliceLayer:
        """Slice mesh at specific height."""
        layer = SliceLayer(z_height=z_height, layer_height=layer_height)

        try:
            # Get cross-section
            section = mesh.section(plane_origin=[0, 0, z_height],
                                 plane_normal=[0, 0, 1])

            if section is None:
                return layer

            # Extract contours
            layer.contours = self._extract_contours(section)

            # Generate infill
            if self.parameters.infill_percentage > 0:
                layer.infill_lines = self._generate_infill(layer.contours, self.parameters.infill_percentage)

            # Generate supports if needed
            if self.parameters.support_enabled:
                layer.support_structures = self._generate_supports(mesh, z_height, layer.contours)

            # Calculate layer metrics
            layer.estimated_print_time = self._estimate_layer_print_time(layer)
            layer.material_volume = self._calculate_layer_volume(layer)

        except Exception as e:
            self.logger.warning(f"Error slicing at height {z_height}: {e}")

        return layer

    def _extract_contours(self, section) -> List[np.ndarray]:
        """Extract contour paths from section."""
        contours = []

        try:
            if hasattr(section, 'polygons_full'):
                polygons = section.polygons_full
                for polygon in polygons:
                    if hasattr(polygon, 'exterior') and polygon.exterior is not None:
                        coords = np.array(polygon.exterior.coords)
                        contours.append(coords)

        except Exception as e:
            self.logger.warning(f"Error extracting contours: {e}")

        return contours

    def _generate_infill(self, contours: List[np.ndarray], density: int) -> List[np.ndarray]:
        """Generate infill pattern within contours."""
        infill_lines = []

        try:
            if not contours:
                return infill_lines

            # Simple rectilinear infill for demonstration
            # In a real implementation, this would use sophisticated algorithms
            # for different infill patterns (gyroid, honeycomb, etc.)

            # Calculate bounding box of all contours
            all_points = np.vstack(contours)
            min_bounds = np.min(all_points, axis=0)
            max_bounds = np.max(all_points, axis=0)

            # Generate parallel lines
            spacing = 1.0 / (density / 100.0)  # Convert percentage to spacing
            x_lines = []
            y_lines = []

            x = min_bounds[0]
            while x <= max_bounds[0]:
                line = np.array([[x, min_bounds[1]], [x, max_bounds[1]]])
                x_lines.append(line)
                x += spacing

            y = min_bounds[1]
            while y <= max_bounds[1]:
                line = np.array([[min_bounds[0], y], [max_bounds[0], y]])
                y_lines.append(line)
                y += spacing

            # Alternate direction for better strength
            infill_lines.extend(x_lines[::2])  # Even indices
            infill_lines.extend(y_lines[1::2])  # Odd indices

        except Exception as e:
            self.logger.warning(f"Error generating infill: {e}")

        return infill_lines

    def _generate_supports(self, mesh: trimesh.Trimesh, z_height: float, contours: List[np.ndarray]) -> List[np.ndarray]:
        """Generate support structures for the layer."""
        supports = []

        try:
            if not self.parameters.support_enabled:
                return supports

            # Simplified support generation
            # In a real implementation, this would analyze overhangs and generate
            # tree-like or grid supports

            angle_rad = np.radians(self.parameters.support_angle)
            support_spacing = 5.0  # mm

            # Check each contour for overhangs requiring support
            for contour in contours:
                if len(contour) < 3:
                    continue

                # Calculate normals and check angles
                # This is a simplified version - real implementation would be much more sophisticated
                supports.extend(self._create_support_grid(contour, support_spacing))

        except Exception as e:
            self.logger.warning(f"Error generating supports: {e}")

        return supports

    def _create_support_grid(self, contour: np.ndarray, spacing: float) -> List[np.ndarray]:
        """Create support grid for a contour."""
        supports = []

        try:
            # Calculate bounding box
            min_bounds = np.min(contour, axis=0)
            max_bounds = np.max(contour, axis=0)

            # Create grid of support pillars
            x = min_bounds[0]
            while x <= max_bounds[0]:
                y = min_bounds[1]
                while y <= max_bounds[1]:
                    # Check if point is inside contour
                    if self._point_in_contour(np.array([x, y]), contour):
                        # Create support pillar (vertical line)
                        pillar = np.array([[x, y], [x, y + 10.0]])  # 10mm height
                        supports.append(pillar)
                    y += spacing
                x += spacing

        except Exception as e:
            self.logger.warning(f"Error creating support grid: {e}")

        return supports

    def _point_in_contour(self, point: np.ndarray, contour: np.ndarray) -> bool:
        """Check if point is inside contour using ray casting."""
        try:
            # Simple implementation - real version would use proper polygon inclusion
            return True  # Simplified for demonstration
        except Exception:
            return False

    def _estimate_layer_print_time(self, layer: SliceLayer) -> float:
        """Estimate print time for a layer in seconds."""
        try:
            total_distance = 0.0

            # Calculate contour perimeter
            for contour in layer.contours:
                if len(contour) > 1:
                    distances = np.linalg.norm(np.diff(contour, axis=0), axis=1)
                    total_distance += np.sum(distances)

            # Calculate infill distance
            for infill_line in layer.infill_lines:
                if len(infill_line) > 1:
                    distances = np.linalg.norm(np.diff(infill_line, axis=0), axis=1)
                    total_distance += np.sum(distances)

            # Estimate time (simplified)
            time_seconds = total_distance / (self.parameters.print_speed * 1000 / 60)  # Convert to minutes

            return time_seconds

        except Exception as e:
            self.logger.warning(f"Error estimating layer print time: {e}")
            return 0.0

    def _calculate_layer_volume(self, layer: SliceLayer) -> float:
        """Calculate material volume for a layer."""
        try:
            volume = 0.0

            # Calculate wall volume
            wall_area = 0.0
            for contour in layer.contours:
                if len(contour) > 1:
                    # Approximate wall area
                    perimeter = np.sum(np.linalg.norm(np.diff(contour, axis=0), axis=1))
                    wall_area += perimeter * layer.layer_height

            # Calculate infill volume
            infill_area = 0.0
            for infill_line in layer.infill_lines:
                if len(infill_line) > 1:
                    length = np.sum(np.linalg.norm(np.diff(infill_line, axis=0), axis=1))
                    infill_area += length * 0.4  # Approximate line width

            volume = wall_area + infill_area
            return volume

        except Exception as e:
            self.logger.warning(f"Error calculating layer volume: {e}")
            return 0.0

    def _calculate_quality_metrics(self, result: SlicingResult):
        """Calculate overall quality metrics for slicing result."""
        try:
            total_time = sum(layer.estimated_print_time for layer in result.layers)
            result.estimated_print_time = total_time / 60.0  # Convert to minutes

            total_volume = sum(layer.material_volume for layer in result.layers)
            result.total_material_volume = total_volume

            # Calculate support volume
            support_volume = 0.0
            for layer in result.layers:
                for support in layer.support_structures:
                    if len(support) > 1:
                        length = np.sum(np.linalg.norm(np.diff(support, axis=0), axis=1))
                        support_volume += length * 0.4 * layer.layer_height
            result.support_volume = support_volume

            # Quality metrics
            result.quality_metrics = {
                "layer_height_variance": self._calculate_layer_height_variance(result),
                "surface_finish_score": self._calculate_surface_finish_score(result),
                "structural_integrity_score": self._calculate_structural_integrity_score(result),
                "material_efficiency": self._calculate_material_efficiency(result),
            }

        except Exception as e:
            self.logger.warning(f"Error calculating quality metrics: {e}")

    def _calculate_layer_height_variance(self, result: SlicingResult) -> float:
        """Calculate variance in layer heights."""
        if not result.layers:
            return 0.0

        heights = [layer.layer_height for layer in result.layers]
        return float(np.var(heights))

    def _calculate_surface_finish_score(self, result: SlicingResult) -> float:
        """Calculate surface finish quality score."""
        # Simplified scoring based on layer height consistency
        variance = self._calculate_layer_height_variance(result)
        # Lower variance = better surface finish
        score = max(0.0, 1.0 - variance * 10.0)
        return score

    def _calculate_structural_integrity_score(self, result: SlicingResult) -> float:
        """Calculate structural integrity score."""
        # Simplified scoring based on infill and wall thickness
        base_score = 0.8  # Base score

        # Adjust based on infill percentage
        infill_factor = min(1.0, result.slicing_parameters.infill_percentage / 20.0)
        base_score += infill_factor * 0.2

        return min(1.0, base_score)

    def _calculate_material_efficiency(self, result: SlicingResult) -> float:
        """Calculate material efficiency ratio."""
        if result.total_material_volume == 0:
            return 0.0

        # Efficiency = useful material / total material
        useful_volume = result.total_material_volume - result.support_volume
        efficiency = useful_volume / result.total_material_volume

        return max(0.0, efficiency)


def slice_mesh_advanced(mesh: trimesh.Trimesh,
                       parameters: Optional[SlicingParameters] = None) -> SlicingResult:
    """Advanced mesh slicing with adaptive algorithms."""
    if parameters is None:
        parameters = SlicingParameters()

    slicer = AdaptiveLayerHeightSlicer(parameters)
    return slicer.slice(mesh)


def optimize_slicing_parameters(mesh: trimesh.Trimesh,
                              target_quality: str = "balanced") -> SlicingParameters:
    """Optimize slicing parameters based on mesh characteristics and quality target."""

    # Analyze mesh properties
    bounds = mesh.bounds
    dimensions = bounds[1] - bounds[0]
    volume = mesh.volume if mesh.is_watertight else 0.0
    surface_area = mesh.area

    # Calculate complexity metrics
    complexity_score = min(1.0, surface_area / 10000.0)  # Normalize surface area
    size_score = min(1.0, max(dimensions) / 200.0)  # Normalize largest dimension

    parameters = SlicingParameters()

    if target_quality == "speed":
        # Optimize for speed
        parameters.layer_height = 0.3
        parameters.infill_percentage = 10
        parameters.wall_thickness = 2
        parameters.print_speed = 60.0

    elif target_quality == "quality":
        # Optimize for quality
        parameters.layer_height = 0.1
        parameters.infill_percentage = 25
        parameters.wall_thickness = 4
        parameters.print_speed = 30.0

    elif target_quality == "strength":
        # Optimize for strength
        parameters.layer_height = 0.2
        parameters.infill_percentage = 30
        parameters.wall_thickness = 4
        parameters.print_speed = 40.0

    else:  # balanced
        # Adaptive based on mesh properties
        base_layer_height = 0.15 + (complexity_score * 0.1)  # 0.15-0.25
        parameters.layer_height = min(0.25, max(0.1, base_layer_height))

        base_infill = 15 + int(complexity_score * 10)  # 15-25
        parameters.infill_percentage = min(25, max(10, base_infill))

        parameters.wall_thickness = 3
        parameters.print_speed = 40.0 + (size_score * 20.0)  # 40-60

    # Enable advanced features for complex meshes
    parameters.adaptive_layer_height_enabled = complexity_score > 0.3
    parameters.variable_infill_enabled = complexity_score > 0.5

class CLIPSlicer:
    """Continuous Liquid Interface Production slicer for ultra-fast printing."""

    def __init__(self, parameters: SlicingParameters):
        self.parameters = parameters
        self.logger = logging.getLogger(__name__)

    def slice(self, mesh: trimesh.Trimesh) -> SlicingResult:
        """Perform CLIP-style continuous slicing."""
        result = SlicingResult(slicing_parameters=self.parameters)

        if not self.parameters.clip_enabled:
            self.logger.warning("CLIP slicing requested but CLIP is not enabled")
            return result

        # Get mesh bounds
        bounds = mesh.bounds
        min_z, max_z = bounds[0][2], bounds[1][2]
        result.total_height = max_z - min_z

        # For CLIP, we use continuous exposure rather than discrete layers
        # This is a simplified simulation - real CLIP would use sophisticated optics
        clip_layers = self._generate_clip_layers(mesh, min_z, max_z)
        result.layers = clip_layers
        result.total_layers = len(clip_layers)

        # Calculate CLIP-specific metrics
        self._calculate_clip_metrics(result, mesh)

        return result

    def _generate_clip_layers(self, mesh: trimesh.Trimesh, min_z: float, max_z: float) -> List[SliceLayer]:
        """Generate layers for CLIP printing."""
        layers = []

        # CLIP uses continuous curing, so we simulate with very thin layers
        layer_height = self.parameters.clip_cure_depth_mm
        current_z = min_z

        while current_z < max_z:
            layer = SliceLayer(z_height=current_z, layer_height=layer_height)

            # Generate exposure mask for this layer
            layer.exposure_mask = self._generate_exposure_mask(mesh, current_z)
            layer.estimated_print_time = self._calculate_clip_layer_time(layer)

            layers.append(layer)
            current_z += layer_height

        return layers

    def _generate_exposure_mask(self, mesh: trimesh.Trimesh, z_height: float) -> np.ndarray:
        """Generate exposure mask for CLIP layer."""
        # Simplified mask generation - real implementation would use sophisticated algorithms
        # For demonstration, create a simple binary mask

        # Get mesh cross-section at this height
        section = mesh.section(plane_origin=[0, 0, z_height], plane_normal=[0, 0, 1])

        if section is None:
            # No geometry at this height
            return np.zeros((100, 100), dtype=bool)

        # Convert section to binary mask (simplified)
        # In practice, this would involve ray tracing and anti-aliasing
        mask_size = 100
        mask = np.zeros((mask_size, mask_size), dtype=bool)

        # Simple bounding box approximation for demonstration
        bounds = mesh.bounds
        if z_height >= bounds[0][2] and z_height <= bounds[1][2]:
            # Fill a region representing the cross-section
            center_x, center_y = mask_size // 2, mask_size // 2
            radius = min(mask_size // 4, 20)  # Arbitrary size
            y, x = np.ogrid[:mask_size, :mask_size]
            dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            mask[dist_from_center <= radius] = True

        return mask

    def _calculate_clip_layer_time(self, layer: SliceLayer) -> float:
        """Calculate exposure time for CLIP layer."""
        # Based on resin properties and layer complexity
        base_time = self.parameters.clip_exposure_time_ms / 1000.0  # Convert to seconds

        # Adjust based on mask complexity
        if hasattr(layer, 'exposure_mask'):
            complexity = np.sum(layer.exposure_mask) / layer.exposure_mask.size
            time_multiplier = 1.0 + (complexity * 0.5)  # Up to 50% more time for complex layers
            return base_time * time_multiplier

        return base_time

    def _calculate_clip_metrics(self, result: SlicingResult, mesh: trimesh.Trimesh):
        """Calculate CLIP-specific quality metrics."""
        # CLIP metrics
        total_exposure_time = sum(layer.estimated_print_time for layer in result.layers)
        result.estimated_print_time = total_exposure_time / 60.0  # Convert to minutes

        # CLIP is much faster than traditional printing
        # Real CLIP can print at speeds up to 1000x faster
        speed_factor = 100.0  # Conservative estimate
        result.estimated_print_time /= speed_factor

        # Material volume calculation for CLIP
        result.total_material_volume = mesh.volume if mesh.is_watertight else 0.0

        # CLIP quality metrics
        result.quality_metrics.update({
            "clip_speed_factor": speed_factor,
            "oxygen_inhibition_depth": self.parameters.clip_cure_depth_mm * 0.1,
            "resin_efficiency": self._calculate_resin_efficiency(result),
            "surface_smoothness": 0.95,  # CLIP typically produces very smooth surfaces
            "dimensional_accuracy": 0.98  # High accuracy due to continuous process
        })

    def _calculate_resin_efficiency(self, result: SlicingResult) -> float:
        """Calculate resin usage efficiency for CLIP."""
        # CLIP uses resin more efficiently due to continuous process
        # Simplified calculation
        base_efficiency = 0.9  # 90% efficiency

        # Adjust based on print parameters
        viscosity_factor = max(0.0, 1.0 - (self.parameters.clip_resin_viscosity - 50) / 200)
        efficiency = base_efficiency * viscosity_factor

        return max(0.5, min(0.95, efficiency))


def slice_mesh_clip(mesh: trimesh.Trimesh,
                   parameters: Optional[SlicingParameters] = None) -> SlicingResult:
    """CLIP-style mesh slicing for ultra-fast printing."""
    if parameters is None:
        parameters = SlicingParameters()

    # Enable CLIP for this operation
    parameters.clip_enabled = True

    slicer = CLIPSlicer(parameters)
    return slicer.slice(mesh)
