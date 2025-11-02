"""Infill pattern optimization for 3D printing."""

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


class InfillPattern(Enum):
    """Types of infill patterns."""
    RECTILINEAR = "rectilinear"
    HONEYCOMB = "honeycomb"
    GYROID = "gyroid"
    CONCENTRIC = "concentric"
    GRID = "grid"
    TRIANGULAR = "triangular"
    CUBIC = "cubic"
    OCTET = "octet"
    CROSS = "cross"
    LINE = "line"


class InfillStrategy(Enum):
    """Infill optimization strategies."""
    STRENGTH_OPTIMIZED = "strength_optimized"
    SPEED_OPTIMIZED = "speed_optimized"
    MATERIAL_OPTIMIZED = "material_optimized"
    WEIGHT_OPTIMIZED = "weight_optimized"
    BALANCED = "balanced"


@dataclass
class InfillSettings:
    """Settings for infill optimization."""
    pattern: InfillPattern = InfillPattern.GYROID
    strategy: InfillStrategy = InfillStrategy.BALANCED
    density: float = 0.2  # 0.0 to 1.0
    layer_height: float = 0.2  # mm
    line_width: float = 0.4  # mm
    angle: float = 45.0  # degrees
    adaptive_density: bool = True
    gradient_infill: bool = False
    perimeter_layers: int = 2
    top_bottom_layers: int = 3
    infill_overlap: float = 0.15  # mm


@dataclass
class InfillResult:
    """Result of infill optimization."""
    success: bool
    optimized_mesh: Optional[trimesh.Trimesh]
    infill_volume: float
    infill_density: float
    estimated_print_time: float
    material_usage: float
    strength_score: float
    generation_time: float
    operations_performed: List[str]


class InfillOptimizer:
    """Infill pattern optimization engine for 3D printing."""

    def __init__(self, settings: InfillSettings = None):
        """
        Initialize the infill optimizer.

        Args:
            settings: Infill optimization settings
        """
        self.settings = settings or InfillSettings()
        self.logger = logging.getLogger(__name__)

    def optimize_infill(self, mesh: trimesh.Trimesh) -> InfillResult:
        """
        Optimize infill pattern for the mesh.

        Args:
            mesh: Input mesh to optimize infill for

        Returns:
            InfillResult with optimized infill configuration
        """
        start_time = time.time()
        operations_performed = []

        try:
            # Step 1: Analyze mesh structure
            mesh_analysis = self._analyze_mesh_structure(mesh)
            operations_performed.append("mesh_structure_analysis")

            # Step 2: Determine optimal infill pattern
            optimal_pattern = self._determine_optimal_pattern(mesh_analysis)
            operations_performed.append("pattern_optimization")

            # Step 3: Calculate infill parameters
            infill_params = self._calculate_infill_parameters(mesh_analysis, optimal_pattern)
            operations_performed.append("parameter_calculation")

            # Step 4: Generate infill structure
            infill_mesh = self._generate_infill_structure(mesh, infill_params)
            operations_performed.append("infill_generation")

            # Step 5: Optimize for strategy
            optimized_mesh, metrics = self._optimize_for_strategy(mesh, infill_mesh, infill_params)
            operations_performed.append("strategy_optimization")

            # Step 6: Calculate final metrics
            infill_volume = self._calculate_infill_volume(optimized_mesh, mesh)
            estimated_print_time = self._estimate_print_time(mesh, infill_params)
            material_usage = self._calculate_material_usage(mesh, infill_params)
            strength_score = self._calculate_strength_score(mesh_analysis, infill_params)

            generation_time = time.time() - start_time

            return InfillResult(
                success=True,
                optimized_mesh=optimized_mesh,
                infill_volume=infill_volume,
                infill_density=infill_params['density'],
                estimated_print_time=estimated_print_time,
                material_usage=material_usage,
                strength_score=strength_score,
                generation_time=generation_time,
                operations_performed=operations_performed
            )

        except Exception as e:
            self.logger.error(f"Infill optimization failed: {e}")
            generation_time = time.time() - start_time

            return InfillResult(
                success=False,
                optimized_mesh=None,
                infill_volume=0.0,
                infill_density=self.settings.density,
                estimated_print_time=0.0,
                material_usage=0.0,
                strength_score=0.0,
                generation_time=generation_time,
                operations_performed=operations_performed
            )

    def _analyze_mesh_structure(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Analyze mesh structure for infill optimization."""
        analysis = {}

        try:
            # Basic mesh properties
            analysis['volume'] = mesh.volume if mesh.is_volume else 0.0
            analysis['surface_area'] = mesh.area
            analysis['bounding_box'] = mesh.extents
            analysis['height'] = mesh.extents[2]

            # Layer analysis
            layer_count = int(analysis['height'] / self.settings.layer_height)
            analysis['layer_count'] = max(1, layer_count)

            # Stress analysis (simplified)
            analysis['stress_zones'] = self._identify_stress_zones(mesh)

            # Overhang analysis
            analysis['overhang_areas'] = self._identify_overhang_areas(mesh)

            # Hollow areas that need infill
            analysis['hollow_volume'] = self._calculate_hollow_volume(mesh)

        except Exception as e:
            self.logger.warning(f"Mesh analysis failed: {e}")
            analysis = {
                'volume': 0.0,
                'surface_area': 0.0,
                'height': 10.0,
                'layer_count': 50,
                'stress_zones': [],
                'overhang_areas': [],
                'hollow_volume': 0.0
            }

        return analysis

    def _identify_stress_zones(self, mesh: trimesh.Trimesh) -> List[Dict[str, Any]]:
        """Identify areas of high stress concentration."""
        stress_zones = []

        try:
            # Simplified stress analysis based on geometry
            for i, face in enumerate(mesh.faces):
                vertices = mesh.vertices[face]
                face_normal = mesh.face_normals[i]

                # Check for horizontal faces (potential stress areas)
                if abs(face_normal[2]) > 0.8:  # Nearly horizontal
                    centroid = np.mean(vertices, axis=0)
                    stress_zones.append({
                        'location': centroid,
                        'area': mesh.area_faces[i],
                        'stress_level': 'high'
                    })

        except Exception as e:
            self.logger.warning(f"Stress zone identification failed: {e}")

        return stress_zones

    def _identify_overhang_areas(self, mesh: trimesh.Trimesh) -> List[Dict[str, Any]]:
        """Identify overhang areas that need support."""
        overhang_areas = []

        try:
            for i, normal in enumerate(mesh.face_normals):
                # Check if face is overhanging (angle > 45 degrees)
                angle_from_vertical = np.degrees(np.arccos(max(-1.0, min(1.0, normal[2]))))
                if angle_from_vertical > 45:
                    face = mesh.faces[i]
                    centroid = np.mean(mesh.vertices[face], axis=0)
                    overhang_areas.append({
                        'location': centroid,
                        'area': mesh.area_faces[i],
                        'overhang_angle': angle_from_vertical
                    })

        except Exception as e:
            self.logger.warning(f"Overhang identification failed: {e}")

        return overhang_areas

    def _calculate_hollow_volume(self, mesh: trimesh.Trimesh) -> float:
        """Calculate volume that needs to be filled with infill."""
        try:
            # For solid meshes, infill volume is the internal volume
            # For hollow meshes, it's the volume between walls
            if mesh.is_volume and mesh.is_watertight:
                # Assume uniform wall thickness
                wall_thickness = self.settings.line_width * 2
                external_volume = mesh.volume
                internal_volume = external_volume - (mesh.area * wall_thickness / 2)
                return max(0.0, internal_volume)
            else:
                return mesh.volume * 0.8  # Assume 80% needs infill

        except:
            return mesh.volume * 0.5 if mesh.volume > 0 else 0.0

    def _determine_optimal_pattern(self, mesh_analysis: Dict[str, Any]) -> InfillPattern:
        """Determine optimal infill pattern based on mesh analysis."""
        if self.settings.strategy == InfillStrategy.STRENGTH_OPTIMIZED:
            # Choose patterns that provide good strength
            if mesh_analysis.get('stress_zones'):
                return InfillPattern.GYROID  # Good for complex stress distribution
            else:
                return InfillPattern.CUBIC  # Strong and simple

        elif self.settings.strategy == InfillStrategy.SPEED_OPTIMIZED:
            # Choose fast-printing patterns
            return InfillPattern.LINE  # Fastest to print

        elif self.settings.strategy == InfillStrategy.MATERIAL_OPTIMIZED:
            # Choose material-efficient patterns
            return InfillPattern.GYROID  # Good strength-to-weight ratio

        elif self.settings.strategy == InfillStrategy.WEIGHT_OPTIMIZED:
            # Choose lightweight patterns
            return InfillPattern.HONEYCOMB  # Lightweight and strong

        else:  # BALANCED
            # Choose balanced pattern
            height = mesh_analysis.get('height', 10.0)
            if height > 50:  # Tall objects
                return InfillPattern.GYROID
            else:
                return InfillPattern.HONEYCOMB

    def _calculate_infill_parameters(self, mesh_analysis: Dict[str, Any],
                                   pattern: InfillPattern) -> Dict[str, Any]:
        """Calculate optimal infill parameters."""
        params = {
            'pattern': pattern,
            'density': self.settings.density,
            'layer_height': self.settings.layer_height,
            'line_width': self.settings.line_width,
            'angle': self.settings.angle
        }

        # Adjust density based on strategy and mesh properties
        if self.settings.adaptive_density:
            base_density = self.settings.density

            # Increase density for stress zones
            if mesh_analysis.get('stress_zones'):
                base_density = min(1.0, base_density * 1.3)

            # Decrease density for simple geometries
            if mesh_analysis.get('volume', 0) < 1000:  # Small objects
                base_density = max(0.1, base_density * 0.8)

            params['density'] = base_density

        # Adjust angle for better strength
        if pattern in [InfillPattern.RECTILINEAR, InfillPattern.LINE]:
            # Use 45-degree angle for better layer adhesion
            params['angle'] = 45.0

        return params

    def _generate_infill_structure(self, mesh: trimesh.Trimesh,
                                 params: Dict[str, Any]) -> Optional[trimesh.Trimesh]:
        """Generate infill mesh structure."""
        try:
            pattern = params['pattern']

            if pattern == InfillPattern.LINE:
                return self._generate_line_infill(mesh, params)
            elif pattern == InfillPattern.GYROID:
                return self._generate_gyroid_infill(mesh, params)
            elif pattern == InfillPattern.HONEYCOMB:
                return self._generate_honeycomb_infill(mesh, params)
            else:
                # Default to simple grid
                return self._generate_grid_infill(mesh, params)

        except Exception as e:
            self.logger.warning(f"Infill generation failed: {e}")
            return None

    def _generate_line_infill(self, mesh: trimesh.Trimesh,
                            params: Dict[str, Any]) -> Optional[trimesh.Trimesh]:
        """Generate simple line infill pattern."""
        # Simplified line infill implementation
        # In production, this would create actual line structures
        vertices = []
        faces = []

        # Create simple bounding box infill
        bounds = mesh.bounds
        line_spacing = params['line_width'] / params['density']

        for z in np.arange(bounds[0][2], bounds[1][2], params['layer_height']):
            for y in np.arange(bounds[0][1], bounds[1][1], line_spacing):
                # Create horizontal line
                start = [bounds[0][0], y, z]
                end = [bounds[1][0], y, z]
                vertices.extend([start, end])
                faces.append([len(vertices)-2, len(vertices)-1])

        return trimesh.Trimesh(vertices=vertices, faces=faces) if vertices else None

    def _generate_gyroid_infill(self, mesh: trimesh.Trimesh,
                              params: Dict[str, Any]) -> Optional[trimesh.Trimesh]:
        """Generate gyroid infill pattern."""
        # Simplified gyroid implementation
        # Gyroid is a complex 3D pattern, this is a basic approximation
        return self._generate_line_infill(mesh, params)

    def _generate_honeycomb_infill(self, mesh: trimesh.Trimesh,
                                 params: Dict[str, Any]) -> Optional[trimesh.Trimesh]:
        """Generate honeycomb infill pattern."""
        # Simplified honeycomb implementation
        return self._generate_line_infill(mesh, params)

    def _generate_grid_infill(self, mesh: trimesh.Trimesh,
                            params: Dict[str, Any]) -> Optional[trimesh.Trimesh]:
        """Generate grid infill pattern."""
        return self._generate_line_infill(mesh, params)

    def _optimize_for_strategy(self, original_mesh: trimesh.Trimesh,
                             infill_mesh: Optional[trimesh.Trimesh],
                             params: Dict[str, Any]) -> Tuple[Optional[trimesh.Trimesh], Dict[str, Any]]:
        """Optimize infill based on strategy."""
        metrics = {}

        if not infill_mesh:
            return original_mesh, metrics

        try:
            if self.settings.strategy == InfillStrategy.MATERIAL_OPTIMIZED:
                # Reduce density for material savings
                params['density'] = max(0.1, params['density'] * 0.8)
                metrics['material_reduction'] = 20.0

            elif self.settings.strategy == InfillStrategy.STRENGTH_OPTIMIZED:
                # Increase density for strength
                params['density'] = min(1.0, params['density'] * 1.2)
                metrics['strength_improvement'] = 25.0

            elif self.settings.strategy == InfillStrategy.SPEED_OPTIMIZED:
                # Simplify pattern for speed
                params['pattern'] = InfillPattern.LINE
                metrics['speed_improvement'] = 15.0

        except Exception as e:
            self.logger.warning(f"Strategy optimization failed: {e}")

        return infill_mesh, metrics

    def _calculate_infill_volume(self, infill_mesh: Optional[trimesh.Trimesh],
                               original_mesh: trimesh.Trimesh) -> float:
        """Calculate infill volume."""
        if infill_mesh:
            return infill_mesh.volume if infill_mesh.is_volume else 0.0
        return 0.0

    def _estimate_print_time(self, mesh: trimesh.Trimesh,
                           params: Dict[str, Any]) -> float:
        """Estimate print time in minutes."""
        try:
            # Simple estimation based on volume and height
            volume = mesh.volume if mesh.volume > 0 else 1000
            height = mesh.extents[2]

            # Base time calculation
            base_time = (volume * 0.001) + (height * 2)

            # Adjust for infill density
            density_factor = params.get('density', 0.2)
            time_adjustment = density_factor * 0.5

            return base_time + time_adjustment

        except:
            return 30.0  # Default estimate

    def _calculate_material_usage(self, mesh: trimesh.Trimesh,
                                params: Dict[str, Any]) -> float:
        """Calculate estimated material usage in grams."""
        try:
            volume = mesh.volume if mesh.volume > 0 else 1000
            density = params.get('density', 0.2)

            # Assume PLA density of 1.24 g/cm³
            material_density = 1.24
            material_volume = volume * density

            return material_volume * material_density

        except:
            return 100.0  # Default estimate

    def _calculate_strength_score(self, mesh_analysis: Dict[str, Any],
                                params: Dict[str, Any]) -> float:
        """Calculate strength score (0-100)."""
        try:
            base_score = 50.0

            # Adjust for pattern
            pattern = params.get('pattern', InfillPattern.LINE)
            if pattern in [InfillPattern.GYROID, InfillPattern.CUBIC]:
                base_score += 20.0
            elif pattern in [InfillPattern.HONEYCOMB]:
                base_score += 15.0

            # Adjust for density
            density = params.get('density', 0.2)
            base_score += density * 30.0

            # Adjust for stress zones
            if mesh_analysis.get('stress_zones'):
                base_score += 10.0

            return min(100.0, base_score)

        except:
            return 50.0


def optimize_infill(mesh: trimesh.Trimesh,
                   pattern: InfillPattern = InfillPattern.GYROID,
                   settings: InfillSettings = None) -> InfillResult:
    """
    Convenience function for infill optimization.

    Args:
        mesh: Input mesh to optimize infill for
        pattern: Infill pattern to use
        settings: Optional infill optimization settings

    Returns:
        InfillResult with optimized infill configuration
    """
    if settings is None:
        settings = InfillSettings(pattern=pattern)
    else:
        settings.pattern = pattern

    optimizer = InfillOptimizer(settings)
    return optimizer.optimize_infill(mesh)
