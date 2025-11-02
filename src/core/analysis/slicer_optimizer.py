"""Automatic slicer settings optimization for 3D printing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging
import time
import numpy as np
import trimesh


class SlicerType(Enum):
    """Supported slicer types."""
    PRUSA_SLICER = "prusa_slicer"
    CURA = "cura"
    SIMPLIFY3D = "simplify3d"
    SLIC3R = "slic3r"
    IDEA_MAKER = "idea_maker"
    KISS_SLICER = "kiss_slicer"


class PrintQuality(Enum):
    """Print quality presets."""
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    ULTRA = "ultra"


@dataclass
class SlicerSettings:
    """Optimized slicer settings."""
    slicer_type: SlicerType = SlicerType.CURA
    quality: PrintQuality = PrintQuality.STANDARD

    # Basic settings
    layer_height: float = 0.2  # mm
    line_width: float = 0.4  # mm
    infill_density: float = 0.2  # 0.0 to 1.0

    # Speed settings
    print_speed: float = 50.0  # mm/s
    travel_speed: float = 150.0  # mm/s
    first_layer_speed: float = 20.0  # mm/s

    # Temperature settings
    nozzle_temperature: float = 200.0  # °C
    bed_temperature: float = 60.0  # °C

    # Support settings
    support_enabled: bool = False
    support_angle: float = 45.0  # degrees
    support_density: float = 0.2  # 0.0 to 1.0

    # Infill settings
    infill_pattern: str = "gyroid"
    infill_angle: float = 45.0  # degrees

    # Advanced settings
    retraction_enabled: bool = True
    retraction_distance: float = 6.0  # mm
    retraction_speed: float = 25.0  # mm/s
    coasting_enabled: bool = False
    wipe_enabled: bool = True


@dataclass
class SlicerOptimizationResult:
    """Result of slicer settings optimization."""
    success: bool
    optimized_settings: SlicerSettings
    estimated_print_time: float  # minutes
    estimated_material_usage: float  # grams
    estimated_cost: float  # currency units
    quality_score: float  # 0-100
    optimization_time: float  # seconds
    reasoning: List[str]


class SlicerOptimizer:
    """Automatic slicer settings optimization engine."""

    def __init__(self, material_cost_per_kg: float = 25.0, energy_cost_per_hour: float = 0.15):
        """
        Initialize the slicer optimizer.

        Args:
            material_cost_per_kg: Cost of material in currency per kg
            energy_cost_per_hour: Energy cost per hour of printing
        """
        self.material_cost_per_kg = material_cost_per_kg
        self.energy_cost_per_hour = energy_cost_per_hour
        self.logger = logging.getLogger(__name__)

    def optimize_settings(self, mesh: trimesh.Trimesh,
                         target_quality: PrintQuality = PrintQuality.STANDARD,
                         slicer_type: SlicerType = SlicerType.CURA) -> SlicerOptimizationResult:
        """
        Optimize slicer settings for the given mesh.

        Args:
            mesh: Input mesh to optimize for
            target_quality: Desired print quality
            slicer_type: Target slicer software

        Returns:
            SlicerOptimizationResult with optimized settings
        """
        start_time = time.time()
        reasoning = []

        try:
            # Step 1: Analyze mesh characteristics
            mesh_analysis = self._analyze_mesh(mesh)
            reasoning.append(f"Mesh analysis: {mesh_analysis}")

            # Step 2: Determine base settings from quality preset
            base_settings = self._get_quality_preset(target_quality, slicer_type)
            reasoning.append(f"Applied quality preset: {target_quality.value}")

            # Step 3: Optimize for mesh characteristics
            optimized_settings = self._optimize_for_mesh(base_settings, mesh_analysis, slicer_type)
            reasoning.append("Optimized settings for mesh characteristics")

            # Step 4: Calculate estimated metrics
            estimated_time = self._estimate_print_time(mesh, optimized_settings)
            estimated_material = self._estimate_material_usage(mesh, optimized_settings)
            estimated_cost = self._estimate_cost(estimated_time, estimated_material)
            quality_score = self._calculate_quality_score(mesh_analysis, optimized_settings)

            optimization_time = time.time() - start_time

            return SlicerOptimizationResult(
                success=True,
                optimized_settings=optimized_settings,
                estimated_print_time=estimated_time,
                estimated_material_usage=estimated_material,
                estimated_cost=estimated_cost,
                quality_score=quality_score,
                optimization_time=optimization_time,
                reasoning=reasoning
            )

        except Exception as e:
            self.logger.error(f"Slicer optimization failed: {e}")
            optimization_time = time.time() - start_time

            # Return default settings on failure
            default_settings = SlicerSettings(slicer_type=slicer_type, quality=target_quality)

            return SlicerOptimizationResult(
                success=False,
                optimized_settings=default_settings,
                estimated_print_time=60.0,  # Default 1 hour
                estimated_material_usage=100.0,  # Default 100g
                estimated_cost=5.0,  # Default cost
                quality_score=50.0,
                optimization_time=optimization_time,
                reasoning=[f"Optimization failed: {str(e)}"]
            )

    def _analyze_mesh(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Analyze mesh for slicer optimization."""
        analysis = {}

        try:
            analysis['volume'] = mesh.volume if mesh.is_volume else 1000.0
            analysis['surface_area'] = mesh.area
            analysis['height'] = mesh.extents[2]
            analysis['complexity'] = len(mesh.faces) / max(analysis['volume'], 1.0)
            analysis['is_watertight'] = mesh.is_watertight
            analysis['has_overhangs'] = self._detect_overhangs(mesh)
            analysis['thin_features'] = self._detect_thin_features(mesh)
            analysis['detail_level'] = self._assess_detail_level(mesh)

        except Exception as e:
            self.logger.warning(f"Mesh analysis failed: {e}")
            analysis = {
                'volume': 1000.0,
                'surface_area': 1000.0,
                'height': 50.0,
                'complexity': 1.0,
                'is_watertight': True,
                'has_overhangs': False,
                'thin_features': False,
                'detail_level': 'medium'
            }

        return analysis

    def _detect_overhangs(self, mesh: trimesh.Trimesh) -> bool:
        """Detect if mesh has significant overhangs."""
        try:
            for normal in mesh.face_normals:
                # Check for faces pointing downward at >45 degrees
                angle = np.degrees(np.arccos(max(-1.0, min(1.0, normal[2]))))
                if angle > 45:
                    return True
            return False
        except:
            return False

    def _detect_thin_features(self, mesh: trimesh.Trimesh) -> bool:
        """Detect thin features that need careful printing."""
        try:
            # Check for very small faces
            areas = mesh.area_faces
            min_area = np.min(areas) if len(areas) > 0 else 1.0
            return min_area < 1.0  # Less than 1mm² is considered thin
        except:
            return False

    def _assess_detail_level(self, mesh: trimesh.Trimesh) -> str:
        """Assess the level of detail in the mesh."""
        try:
            face_count = len(mesh.faces)
            volume = mesh.volume if mesh.volume > 0 else 1000.0

            if face_count / volume > 10:
                return 'high'
            elif face_count / volume > 5:
                return 'medium'
            else:
                return 'low'
        except:
            return 'medium'

    def _get_quality_preset(self, quality: PrintQuality, slicer_type: SlicerType) -> SlicerSettings:
        """Get base settings for quality preset."""
        settings = SlicerSettings(slicer_type=slicer_type, quality=quality)

        if quality == PrintQuality.DRAFT:
            settings.layer_height = 0.3
            settings.infill_density = 0.15
            settings.print_speed = 80.0
            settings.nozzle_temperature = 190.0

        elif quality == PrintQuality.STANDARD:
            settings.layer_height = 0.2
            settings.infill_density = 0.2
            settings.print_speed = 50.0
            settings.nozzle_temperature = 200.0

        elif quality == PrintQuality.HIGH:
            settings.layer_height = 0.15
            settings.infill_density = 0.25
            settings.print_speed = 40.0
            settings.nozzle_temperature = 210.0

        elif quality == PrintQuality.ULTRA:
            settings.layer_height = 0.1
            settings.infill_density = 0.3
            settings.print_speed = 30.0
            settings.nozzle_temperature = 220.0

        return settings

    def _optimize_for_mesh(self, base_settings: SlicerSettings,
                         mesh_analysis: Dict[str, Any],
                         slicer_type: SlicerType) -> SlicerSettings:
        """Optimize settings based on mesh characteristics."""
        settings = base_settings

        try:
            # Adjust for complexity
            complexity = mesh_analysis.get('complexity', 1.0)
            if complexity > 5:  # High complexity
                settings.print_speed *= 0.8  # Slower for better quality
                settings.layer_height *= 0.9

            # Adjust for overhangs
            if mesh_analysis.get('has_overhangs', False):
                settings.support_enabled = True
                settings.support_angle = 50.0  # More conservative
                settings.print_speed *= 0.9  # Slower for supports

            # Adjust for thin features
            if mesh_analysis.get('thin_features', False):
                settings.layer_height *= 0.8  # Finer layers
                settings.line_width *= 0.9  # Thinner lines

            # Adjust for detail level
            detail_level = mesh_analysis.get('detail_level', 'medium')
            if detail_level == 'high':
                settings.layer_height *= 0.85
                settings.infill_density *= 1.1

            # Slicer-specific optimizations
            if slicer_type == SlicerType.PRUSA_SLICER:
                # PrusaSlicer specific optimizations
                settings.retraction_distance = 0.8  # PrusaSlicer default
                settings.infill_pattern = "gyroid"

            elif slicer_type == SlicerType.CURA:
                # Cura specific optimizations
                settings.retraction_distance = 6.5  # Cura default
                settings.infill_pattern = "cubic"

        except Exception as e:
            self.logger.warning(f"Mesh optimization failed: {e}")

        return settings

    def _estimate_print_time(self, mesh: trimesh.Trimesh, settings: SlicerSettings) -> float:
        """Estimate print time in minutes."""
        try:
            volume = mesh.volume if mesh.volume > 0 else 1000.0
            height = mesh.extents[2]

            # Base time calculation
            volume_time = volume * 0.01  # 0.01 minutes per mm³
            height_time = height * 0.5   # 0.5 minutes per mm height

            # Adjust for speed
            speed_factor = 50.0 / settings.print_speed  # Base speed is 50mm/s

            # Adjust for infill
            infill_factor = 1.0 + (settings.infill_density * 0.5)

            # Adjust for layer height
            layer_factor = 0.2 / settings.layer_height

            total_time = (volume_time + height_time) * speed_factor * infill_factor * layer_factor

            return max(5.0, total_time)  # Minimum 5 minutes

        except:
            return 60.0  # Default 1 hour

    def _estimate_material_usage(self, mesh: trimesh.Trimesh, settings: SlicerSettings) -> float:
        """Estimate material usage in grams."""
        try:
            volume = mesh.volume if mesh.volume > 0 else 1000.0

            # Base material for walls and infill
            wall_volume = mesh.area * settings.line_width * 2  # Rough estimate
            infill_volume = volume * settings.infill_density

            total_volume = wall_volume + infill_volume

            # Assume PLA density of 1.24 g/cm³
            material_density = 1.24
            material_grams = (total_volume / 1000.0) * material_density  # Convert mm³ to cm³

            return max(1.0, material_grams)

        except:
            return 50.0  # Default estimate

    def _estimate_cost(self, print_time_minutes: float, material_grams: float) -> float:
        """Estimate total cost."""
        try:
            # Material cost
            material_cost = (material_grams / 1000.0) * self.material_cost_per_kg

            # Energy cost (assuming printer uses ~100W)
            energy_hours = print_time_minutes / 60.0
            energy_cost = energy_hours * self.energy_cost_per_hour

            return material_cost + energy_cost

        except:
            return 5.0  # Default cost

    def _calculate_quality_score(self, mesh_analysis: Dict[str, Any],
                               settings: SlicerSettings) -> float:
        """Calculate quality score (0-100)."""
        try:
            score = 50.0

            # Base score from quality preset
            if settings.quality == PrintQuality.DRAFT:
                score += 10.0
            elif settings.quality == PrintQuality.STANDARD:
                score += 20.0
            elif settings.quality == PrintQuality.HIGH:
                score += 30.0
            elif settings.quality == PrintQuality.ULTRA:
                score += 40.0

            # Adjustments for mesh characteristics
            if mesh_analysis.get('has_overhangs', False) and settings.support_enabled:
                score += 10.0  # Good support handling

            if mesh_analysis.get('thin_features', False) and settings.layer_height < 0.15:
                score += 10.0  # Fine layers for thin features

            if mesh_analysis.get('detail_level') == 'high' and settings.layer_height < 0.15:
                score += 10.0  # Fine layers for detailed models

            # Speed vs quality balance
            if settings.print_speed < 40.0:
                score += 10.0  # Slower speed for better quality

            return min(100.0, score)

        except:
            return 50.0


def optimize_slicer_settings(mesh: trimesh.Trimesh,
                           quality: PrintQuality = PrintQuality.STANDARD,
                           slicer_type: SlicerType = SlicerType.CURA,
                           material_cost_per_kg: float = 25.0,
                           energy_cost_per_hour: float = 0.15) -> SlicerOptimizationResult:
    """
    Convenience function for slicer settings optimization.

    Args:
        mesh: Input mesh to optimize for
        quality: Desired print quality
        slicer_type: Target slicer software
        material_cost_per_kg: Cost of material per kg
        energy_cost_per_hour: Energy cost per hour

    Returns:
        SlicerOptimizationResult with optimized settings
    """
    optimizer = SlicerOptimizer(material_cost_per_kg, energy_cost_per_hour)
    return optimizer.optimize_settings(mesh, quality, slicer_type)
