"""Advanced slicing engine for 3D printing preparation."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import logging


class InfillPattern(Enum):
    """Infill pattern types."""
    RECTILINEAR = "rectilinear"
    GRID = "grid"
    TRIANGULAR = "triangular"
    HONEYCOMB = "honeycomb"
    GYROID = "gyroid"
    CUBIC = "cubic"
    CONCENTRIC = "concentric"
    ZIGZAG = "zigzag"
    CROSS = "cross"
    CROSS_3D = "cross_3d"


class SeamPosition(Enum):
    """Seam position preferences."""
    RANDOM = "random"
    NEAREST = "nearest"
    ALIGNED = "aligned"
    REAR = "rear"
    SHARPEST_CORNER = "sharpest_corner"
    USER_SPECIFIED = "user_specified"


class TopBottomPattern(Enum):
    """Top/bottom layer patterns."""
    RECTILINEAR = "rectilinear"
    CONCENTRIC = "concentric"
    ZIGZAG = "zigzag"
    ARCHIMEDEAN = "archimedean"
    OCTAGRAM_SPIRAL = "octagram_spiral"
    HILBERT_CURVE = "hilbert_curve"
    MONOTONIC = "monotonic"


@dataclass
class SliceSettings:
    """Comprehensive slicing settings."""
    # Layer settings
    layer_height: float = 0.2
    first_layer_height: float = 0.2
    adaptive_layers: bool = False
    adaptive_layer_height_min: float = 0.1
    adaptive_layer_height_max: float = 0.3

    # Perimeter settings
    perimeter_count: int = 3
    perimeter_width: float = 0.45
    external_perimeter_width: float = 0.45
    external_perimeter_speed: float = 30
    perimeter_speed: float = 60
    small_perimeter_speed: float = 20
    small_perimeter_threshold: float = 15

    # Infill settings
    infill_density: float = 20.0
    infill_pattern: InfillPattern = InfillPattern.GYROID
    infill_width: float = 0.45
    infill_speed: float = 80
    infill_angle: float = 45
    infill_overlap: float = 10  # Percentage
    combine_infill_every: int = 1
    gradual_infill: bool = False
    gradual_infill_steps: int = 3

    # Top/bottom settings
    top_layers: int = 5
    bottom_layers: int = 4
    top_bottom_pattern: TopBottomPattern = TopBottomPattern.MONOTONIC
    top_bottom_speed: float = 30
    solid_infill_speed: float = 40
    ironing: bool = False
    ironing_speed: float = 15
    ironing_flow: float = 10  # Percentage

    # Support settings
    support_enabled: bool = True
    support_threshold_angle: float = 60
    support_pattern: str = "rectilinear"
    support_density: float = 15
    support_z_distance: float = 0.2
    support_xy_distance: float = 0.7
    support_interface_layers: int = 2

    # Bridge settings
    bridge_speed: float = 30
    bridge_flow: float = 100
    bridge_fan_speed: int = 100
    bridge_angle: float = 0

    # Speed settings
    travel_speed: float = 180
    first_layer_speed: float = 20
    max_volumetric_speed: float = 15  # mm³/s
    acceleration_enabled: bool = True
    default_acceleration: float = 1000
    perimeter_acceleration: float = 800
    infill_acceleration: float = 1000
    travel_acceleration: float = 1500

    # Retraction settings
    retraction_enabled: bool = True
    retraction_distance: float = 0.8
    retraction_speed: float = 35
    retraction_extra_prime: float = 0
    retraction_min_travel: float = 2
    retract_on_layer_change: bool = True
    wipe_enabled: bool = True
    wipe_distance: float = 2

    # Cooling settings
    fan_enabled: bool = True
    min_fan_speed: int = 35
    max_fan_speed: int = 100
    bridge_fan_speed: int = 100
    disable_fan_first_layers: int = 3
    min_layer_time: float = 10
    min_print_speed: float = 10

    # Advanced settings
    seam_position: SeamPosition = SeamPosition.ALIGNED
    xy_size_compensation: float = 0
    hole_size_compensation: float = 0
    avoid_crossing_perimeters: bool = True
    thin_walls: bool = True
    overhangs: bool = True
    fuzzy_skin: bool = False
    fuzzy_skin_thickness: float = 0.3
    fuzzy_skin_point_distance: float = 0.8

    # Experimental
    arc_fitting: bool = False
    resolution: float = 0.05
    variable_layer_height: bool = False
    mold_mode: bool = False
    spiral_vase: bool = False
    smooth_spiralized_contours: bool = True


@dataclass
class LayerData:
    """Data for a single sliced layer."""
    z_height: float
    layer_height: float
    perimeters: List[List[Tuple[float, float]]]
    infill: List[List[Tuple[float, float]]]
    supports: List[List[Tuple[float, float]]]
    bridges: List[List[Tuple[float, float]]]
    solid_infill: List[List[Tuple[float, float]]]
    top_surface: List[List[Tuple[float, float]]]
    bottom_surface: List[List[Tuple[float, float]]]
    travel_moves: List[List[Tuple[float, float]]]
    layer_time_estimate: float
    material_used_mm3: float


@dataclass
class SlicingResult:
    """Result of slicing operation."""
    success: bool
    layers: List[LayerData]
    total_layers: int
    total_print_time_seconds: float
    total_material_mm3: float
    total_material_grams: float
    total_travel_distance_mm: float
    bounding_box: Tuple[float, float, float]
    max_layer_time: float
    min_layer_time: float
    warnings: List[str]
    statistics: Dict[str, Any]


class SlicingEngine:
    """Advanced slicing engine for 3D models."""

    def __init__(self, settings: SliceSettings = None):
        """Initialize slicing engine."""
        self.settings = settings or SliceSettings()
        self.logger = logging.getLogger(__name__)
        self.mesh: Optional[trimesh.Trimesh] = None
        self.layers: List[LayerData] = []

    def slice_mesh(self, mesh: trimesh.Trimesh, material_density: float = 1.24) -> SlicingResult:
        """
        Slice a mesh into printable layers.

        Args:
            mesh: Trimesh object to slice
            material_density: Material density in g/cm³ (default PLA)

        Returns:
            SlicingResult with all layer data
        """
        start_time = time.time()
        self.mesh = mesh
        self.layers = []
        warnings = []

        try:
            # Calculate layer heights
            layer_heights = self._calculate_layer_heights()

            # Generate slices
            for i, (z_height, layer_height) in enumerate(layer_heights):
                layer_data = self._slice_at_height(z_height, layer_height, i == 0)
                self.layers.append(layer_data)

                # Check for issues
                if layer_data.layer_time_estimate < self.settings.min_layer_time:
                    warnings.append(f"Layer {i} may have cooling issues (time: {layer_data.layer_time_estimate:.1f}s)")

            # Calculate statistics
            statistics = self._calculate_statistics()

            # Calculate totals
            total_time = sum(layer.layer_time_estimate for layer in self.layers)
            total_material = sum(layer.material_used_mm3 for layer in self.layers)
            total_weight = (total_material / 1000) * material_density  # Convert mm³ to cm³
            total_travel = self._calculate_total_travel()

            processing_time = time.time() - start_time

            return SlicingResult(
                success=True,
                layers=self.layers,
                total_layers=len(self.layers),
                total_print_time_seconds=total_time,
                total_material_mm3=total_material,
                total_material_grams=total_weight,
                total_travel_distance_mm=total_travel,
                bounding_box=tuple(mesh.extents),
                max_layer_time=max(l.layer_time_estimate for l in self.layers) if self.layers else 0,
                min_layer_time=min(l.layer_time_estimate for l in self.layers) if self.layers else 0,
                warnings=warnings,
                statistics=statistics
            )

        except Exception as e:
            self.logger.error(f"Slicing failed: {e}")
            return SlicingResult(
                success=False,
                layers=[],
                total_layers=0,
                total_print_time_seconds=0,
                total_material_mm3=0,
                total_material_grams=0,
                total_travel_distance_mm=0,
                bounding_box=(0, 0, 0),
                max_layer_time=0,
                min_layer_time=0,
                warnings=[f"Slicing failed: {str(e)}"],
                statistics={}
            )

    def _calculate_layer_heights(self) -> List[Tuple[float, float]]:
        """Calculate layer heights for the model."""
        if not self.mesh:
            return []

        min_z = self.mesh.bounds[0][2]
        max_z = self.mesh.bounds[1][2]

        layer_heights = []
        current_z = min_z

        # First layer
        layer_heights.append((current_z + self.settings.first_layer_height,
                            self.settings.first_layer_height))
        current_z += self.settings.first_layer_height

        # Adaptive or fixed layers
        if self.settings.adaptive_layers:
            while current_z < max_z:
                # Calculate optimal layer height based on surface angle
                optimal_height = self._calculate_adaptive_height(current_z)
                current_z += optimal_height
                if current_z <= max_z:
                    layer_heights.append((current_z, optimal_height))
        else:
            # Fixed layer height
            while current_z < max_z:
                current_z += self.settings.layer_height
                if current_z <= max_z:
                    layer_heights.append((current_z, self.settings.layer_height))
                else:
                    # Last partial layer
                    remaining = max_z - (current_z - self.settings.layer_height)
                    if remaining > 0.01:  # Minimum layer height
                        layer_heights.append((max_z, remaining))

        return layer_heights

    def _calculate_adaptive_height(self, z: float) -> float:
        """Calculate adaptive layer height based on surface angle."""
        # Sample surface normals at this height
        try:
            section = self.mesh.section(plane_origin=[0, 0, z],
                                       plane_normal=[0, 0, 1])
            if section:
                # Analyze surface angles
                max_angle = 0
                for path in section.discrete:
                    if len(path) > 1:
                        for i in range(len(path) - 1):
                            dx = path[i+1][0] - path[i][0]
                            dy = path[i+1][1] - path[i][1]
                            angle = np.arctan2(dy, dx)
                            max_angle = max(max_angle, abs(angle))

                # Map angle to layer height
                if max_angle > np.pi / 3:  # 60 degrees
                    return self.settings.adaptive_layer_height_min
                elif max_angle < np.pi / 6:  # 30 degrees
                    return self.settings.adaptive_layer_height_max
                else:
                    # Linear interpolation
                    t = (max_angle - np.pi/6) / (np.pi/3 - np.pi/6)
                    return (self.settings.adaptive_layer_height_min * t +
                           self.settings.adaptive_layer_height_max * (1-t))
        except:
            pass

        return self.settings.layer_height

    def _slice_at_height(self, z: float, layer_height: float, is_first: bool) -> LayerData:
        """Generate slice data at specific height."""
        layer_data = LayerData(
            z_height=z,
            layer_height=layer_height,
            perimeters=[],
            infill=[],
            supports=[],
            bridges=[],
            solid_infill=[],
            top_surface=[],
            bottom_surface=[],
            travel_moves=[],
            layer_time_estimate=0,
            material_used_mm3=0
        )

        try:
            # Get cross-section at this height
            section = self.mesh.section(plane_origin=[0, 0, z],
                                       plane_normal=[0, 0, 1])

            if section:
                # Convert to 2D paths
                paths_2d = []
                for path in section.discrete:
                    path_2d = [(p[0], p[1]) for p in path]
                    paths_2d.append(path_2d)

                # Generate perimeters
                perimeters = self._generate_perimeters(paths_2d)
                layer_data.perimeters = perimeters

                # Check if solid layer needed
                is_solid = self._is_solid_layer(z)

                if is_solid:
                    # Generate solid infill
                    solid_infill = self._generate_solid_infill(paths_2d)
                    layer_data.solid_infill = solid_infill
                else:
                    # Generate sparse infill
                    infill = self._generate_infill(paths_2d, z)
                    layer_data.infill = infill

                # Detect and generate bridges
                bridges = self._detect_bridges(paths_2d, z)
                layer_data.bridges = bridges

                # Generate supports if needed
                if self.settings.support_enabled:
                    supports = self._generate_supports(paths_2d, z)
                    layer_data.supports = supports

                # Calculate travel moves
                travel_moves = self._calculate_travel_moves(layer_data)
                layer_data.travel_moves = travel_moves

                # Estimate print time and material
                layer_data.layer_time_estimate = self._estimate_layer_time(layer_data, is_first)
                layer_data.material_used_mm3 = self._calculate_material_usage(layer_data)

        except Exception as e:
            self.logger.warning(f"Error slicing at height {z}: {e}")

        return layer_data

    def _generate_perimeters(self, paths: List[List[Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
        """Generate perimeter paths from outline."""
        perimeters = []

        for path in paths:
            if len(path) < 3:
                continue

            # Create polygon from path
            try:
                poly = Polygon(path)

                # Generate multiple perimeters
                for i in range(self.settings.perimeter_count):
                    offset = -i * self.settings.perimeter_width

                    # Offset polygon inward
                    offset_poly = poly.buffer(offset)

                    if offset_poly.is_empty:
                        break

                    # Extract coordinates
                    if isinstance(offset_poly, Polygon):
                        coords = list(offset_poly.exterior.coords)
                        perimeters.append(coords)
                    elif isinstance(offset_poly, MultiPolygon):
                        for p in offset_poly.geoms:
                            coords = list(p.exterior.coords)
                            perimeters.append(coords)
            except:
                continue

        return perimeters

    def _generate_infill(self, paths: List[List[Tuple[float, float]]], z: float) -> List[List[Tuple[float, float]]]:
        """Generate infill pattern."""
        infill_lines = []

        if self.settings.infill_density <= 0:
            return infill_lines

        # Calculate infill spacing
        spacing = self.settings.infill_width * (100 / self.settings.infill_density)

        for path in paths:
            if len(path) < 3:
                continue

            try:
                poly = Polygon(path)

                # Offset inward by perimeter width
                infill_area = poly.buffer(-self.settings.perimeter_count * self.settings.perimeter_width)

                if infill_area.is_empty:
                    continue

                # Generate infill pattern
                if self.settings.infill_pattern == InfillPattern.RECTILINEAR:
                    lines = self._generate_rectilinear_infill(infill_area, spacing, z)
                elif self.settings.infill_pattern == InfillPattern.GRID:
                    lines = self._generate_grid_infill(infill_area, spacing, z)
                elif self.settings.infill_pattern == InfillPattern.HONEYCOMB:
                    lines = self._generate_honeycomb_infill(infill_area, spacing, z)
                elif self.settings.infill_pattern == InfillPattern.GYROID:
                    lines = self._generate_gyroid_infill(infill_area, spacing, z)
                else:
                    lines = self._generate_rectilinear_infill(infill_area, spacing, z)

                infill_lines.extend(lines)

            except:
                continue

        return infill_lines

    def _generate_rectilinear_infill(self, area: Polygon, spacing: float, z: float) -> List[List[Tuple[float, float]]]:
        """Generate rectilinear infill pattern."""
        lines = []
        bounds = area.bounds  # (minx, miny, maxx, maxy)

        # Calculate angle for this layer
        angle = self.settings.infill_angle
        if self.settings.infill_angle == 45:
            # Alternate between 45 and -45 degrees
            layer_num = int(z / self.settings.layer_height)
            angle = 45 if layer_num % 2 == 0 else -45

        angle_rad = np.radians(angle)

        # Generate parallel lines
        line_count = int((bounds[2] - bounds[0]) / spacing) + 1

        for i in range(line_count):
            x = bounds[0] + i * spacing

            # Create line from bottom to top
            start = (x, bounds[1] - 10)  # Extend beyond bounds
            end = (x, bounds[3] + 10)

            # Rotate line
            center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)
            start_rot = self._rotate_point(start, center, angle_rad)
            end_rot = self._rotate_point(end, center, angle_rad)

            # Clip line to polygon
            from shapely.geometry import LineString
            line = LineString([start_rot, end_rot])
            clipped = area.intersection(line)

            if not clipped.is_empty:
                if isinstance(clipped, LineString):
                    lines.append(list(clipped.coords))

        return lines

    def _generate_grid_infill(self, area: Polygon, spacing: float, z: float) -> List[List[Tuple[float, float]]]:
        """Generate grid infill pattern."""
        lines = []

        # Generate lines in two perpendicular directions
        lines.extend(self._generate_rectilinear_infill(area, spacing, z))

        # Rotate 90 degrees and generate again
        angle_rad = np.radians(90)
        rotated_lines = self._generate_rectilinear_infill(area, spacing, z + 0.01)  # Slight offset to avoid z-fighting

        lines.extend(rotated_lines)

        return lines

    def _generate_honeycomb_infill(self, area: Polygon, spacing: float, z: float) -> List[List[Tuple[float, float]]]:
        """Generate honeycomb infill pattern."""
        lines = []
        bounds = area.bounds

        # Hexagon parameters
        hex_size = spacing * 1.5
        hex_height = hex_size * np.sqrt(3)

        # Generate hexagonal grid
        y = bounds[1]
        row = 0

        while y < bounds[3]:
            x = bounds[0] if row % 2 == 0 else bounds[0] + hex_size * 1.5

            while x < bounds[2]:
                # Generate hexagon vertices
                hex_points = []
                for i in range(6):
                    angle = np.pi / 3 * i
                    px = x + hex_size * np.cos(angle)
                    py = y + hex_size * np.sin(angle)
                    hex_points.append((px, py))

                # Check if hexagon intersects with area
                from shapely.geometry import LineString
                for i in range(6):
                    line = LineString([hex_points[i], hex_points[(i+1) % 6]])
                    clipped = area.intersection(line)

                    if not clipped.is_empty:
                        if isinstance(clipped, LineString):
                            lines.append(list(clipped.coords))

                x += hex_size * 3

            y += hex_height / 2
            row += 1

        return lines

    def _generate_gyroid_infill(self, area: Polygon, spacing: float, z: float) -> List[List[Tuple[float, float]]]:
        """Generate gyroid infill pattern."""
        lines = []
        bounds = area.bounds

        # Gyroid equation: sin(x) * cos(y) + sin(y) * cos(z) + sin(z) * cos(x) = 0
        # We'll approximate with a wave pattern

        resolution = spacing / 4

        # Generate wave pattern
        x = bounds[0]
        while x < bounds[2]:
            points = []
            y = bounds[1]

            while y < bounds[3]:
                # Calculate wave offset based on 3D position
                wave = np.sin(x / spacing * 2 * np.pi) * np.cos(z / spacing * 2 * np.pi) * spacing / 2
                point = (x + wave, y)

                # Check if point is inside area
                from shapely.geometry import Point
                if area.contains(Point(point)):
                    points.append(point)

                y += resolution

            if len(points) > 1:
                lines.append(points)

            x += spacing

        return lines

    def _generate_solid_infill(self, paths: List[List[Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
        """Generate solid infill for top/bottom layers."""
        # Use tighter spacing for solid layers
        spacing = self.settings.perimeter_width
        return self._generate_infill(paths, 0)  # Use default rectilinear for solid

    def _is_solid_layer(self, z: float) -> bool:
        """Check if layer should be solid (top/bottom)."""
        if not self.mesh:
            return False

        min_z = self.mesh.bounds[0][2]
        max_z = self.mesh.bounds[1][2]

        # Check if bottom layer
        if z - min_z < self.settings.bottom_layers * self.settings.layer_height:
            return True

        # Check if top layer
        if max_z - z < self.settings.top_layers * self.settings.layer_height:
            return True

        return False

    def _detect_bridges(self, paths: List[List[Tuple[float, float]]], z: float) -> List[List[Tuple[float, float]]]:
        """Detect and mark bridging areas."""
        bridges = []

        # Check for unsupported spans
        for path in paths:
            for i in range(len(path) - 1):
                start = path[i]
                end = path[i + 1]

                # Check if span is unsupported
                span_length = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)

                if span_length > 5.0:  # Bridge threshold 5mm
                    # Check support below
                    if not self._has_support_below(start, end, z):
                        bridges.append([start, end])

        return bridges

    def _has_support_below(self, start: Tuple[float, float], end: Tuple[float, float], z: float) -> bool:
        """Check if there's support below a span."""
        # Simplified check - would need proper layer comparison in production
        check_z = z - self.settings.layer_height * 2

        if check_z < 0:
            return True  # Build plate

        # Check previous layers for support
        # This is simplified - production would check actual geometry
        return False

    def _generate_supports(self, paths: List[List[Tuple[float, float]]], z: float) -> List[List[Tuple[float, float]]]:
        """Generate support structures."""
        supports = []

        # This is a simplified support generation
        # Production system would use more sophisticated algorithms

        for path in paths:
            try:
                poly = Polygon(path)

                # Check overhang areas
                # Simplified: just add support under entire part if needed
                if self._needs_support(poly, z):
                    # Generate support pattern
                    support_spacing = self.settings.perimeter_width * (100 / self.settings.support_density)
                    support_lines = self._generate_rectilinear_infill(poly, support_spacing, z)
                    supports.extend(support_lines)

            except:
                continue

        return supports

    def _needs_support(self, poly: Polygon, z: float) -> bool:
        """Check if area needs support."""
        # Simplified check - production would analyze actual geometry
        # and check overhangs against threshold angle
        return z > self.mesh.bounds[0][2] + 5  # Support if above 5mm

    def _calculate_travel_moves(self, layer: LayerData) -> List[List[Tuple[float, float]]]:
        """Calculate travel moves between print paths."""
        travel_moves = []

        # Combine all paths
        all_paths = (layer.perimeters + layer.infill + layer.solid_infill +
                    layer.supports + layer.bridges)

        # Calculate travel between paths
        for i in range(len(all_paths) - 1):
            if all_paths[i] and all_paths[i+1]:
                end_point = all_paths[i][-1]
                start_point = all_paths[i+1][0]
                travel_moves.append([end_point, start_point])

        return travel_moves

    def _estimate_layer_time(self, layer: LayerData, is_first: bool) -> float:
        """Estimate print time for layer."""
        time_estimate = 0

        # Speed settings
        perimeter_speed = self.settings.first_layer_speed if is_first else self.settings.perimeter_speed
        infill_speed = self.settings.first_layer_speed if is_first else self.settings.infill_speed
        travel_speed = self.settings.travel_speed

        # Calculate perimeter time
        for path in layer.perimeters:
            length = self._calculate_path_length(path)
            time_estimate += length / perimeter_speed

        # Calculate infill time
        for path in layer.infill + layer.solid_infill:
            length = self._calculate_path_length(path)
            time_estimate += length / infill_speed

        # Calculate support time
        for path in layer.supports:
            length = self._calculate_path_length(path)
            time_estimate += length / infill_speed

        # Calculate bridge time
        for path in layer.bridges:
            length = self._calculate_path_length(path)
            time_estimate += length / self.settings.bridge_speed

        # Calculate travel time
        for path in layer.travel_moves:
            length = self._calculate_path_length(path)
            time_estimate += length / travel_speed

        return time_estimate

    def _calculate_material_usage(self, layer: LayerData) -> float:
        """Calculate material usage for layer in mm³."""
        material = 0

        # Calculate extrusion volume
        nozzle_area = np.pi * (self.settings.perimeter_width / 2) ** 2

        # Perimeters
        for path in layer.perimeters:
            length = self._calculate_path_length(path)
            material += length * nozzle_area * layer.layer_height

        # Infill
        for path in layer.infill + layer.solid_infill:
            length = self._calculate_path_length(path)
            material += length * nozzle_area * layer.layer_height

        # Supports
        for path in layer.supports:
            length = self._calculate_path_length(path)
            material += length * nozzle_area * layer.layer_height

        # Bridges (may use different flow)
        for path in layer.bridges:
            length = self._calculate_path_length(path)
            flow_multiplier = self.settings.bridge_flow / 100
            material += length * nozzle_area * layer.layer_height * flow_multiplier

        return material

    def _calculate_path_length(self, path: List[Tuple[float, float]]) -> float:
        """Calculate total length of a path."""
        if len(path) < 2:
            return 0

        length = 0
        for i in range(len(path) - 1):
            dx = path[i+1][0] - path[i][0]
            dy = path[i+1][1] - path[i][1]
            length += np.sqrt(dx*dx + dy*dy)

        return length

    def _rotate_point(self, point: Tuple[float, float], center: Tuple[float, float],
                     angle: float) -> Tuple[float, float]:
        """Rotate a point around a center."""
        s = np.sin(angle)
        c = np.cos(angle)

        # Translate to origin
        x = point[0] - center[0]
        y = point[1] - center[1]

        # Rotate
        xnew = x * c - y * s
        ynew = x * s + y * c

        # Translate back
        return (xnew + center[0], ynew + center[1])

    def _calculate_total_travel(self) -> float:
        """Calculate total travel distance."""
        total = 0
        for layer in self.layers:
            for path in layer.travel_moves:
                total += self._calculate_path_length(path)
        return total

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate slicing statistics."""
        if not self.layers:
            return {}

        stats = {
            'layer_count': len(self.layers),
            'average_layer_time': sum(l.layer_time_estimate for l in self.layers) / len(self.layers),
            'perimeter_length': sum(self._calculate_path_length(p) for l in self.layers for p in l.perimeters),
            'infill_length': sum(self._calculate_path_length(p) for l in self.layers for p in l.infill),
            'support_length': sum(self._calculate_path_length(p) for l in self.layers for p in l.supports),
            'bridge_count': sum(len(l.bridges) for l in self.layers),
            'solid_layers': sum(1 for l in self.layers if l.solid_infill),
            'sparse_layers': sum(1 for l in self.layers if l.infill and not l.solid_infill),
        }

        return stats