"""Interlayer adhesion optimization for improved 3D printing quality."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging
import time
import numpy as np
import trimesh


class AdhesionEnhancementTechnique(Enum):
    """Techniques for improving interlayer adhesion."""
    TEMPERATURE_OPTIMIZATION = "temperature_optimization"
    SPEED_ADJUSTMENT = "speed_adjustment"
    FAN_CONTROL = "fan_control"
    MATERIAL_MODIFICATION = "material_modification"
    LAYER_PATTERN_OPTIMIZATION = "layer_pattern_optimization"
    INFILL_MODIFICATION = "infill_modification"


class AdhesionQuality(Enum):
    """Quality levels for interlayer adhesion."""
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


@dataclass
class InterlayerAdhesionSettings:
    """Settings for interlayer adhesion optimization."""
    target_quality: AdhesionQuality = AdhesionQuality.GOOD
    material_type: str = "PLA"
    printer_type: str = "FDM"
    nozzle_diameter: float = 0.4  # mm
    layer_height: float = 0.2  # mm
    ambient_temperature: float = 25.0  # °C
    humidity: float = 50.0  # %
    print_speed: float = 50.0  # mm/s
    enable_fan_control: bool = True
    enable_temperature_variation: bool = True
    enable_speed_variation: bool = True


@dataclass
class AdhesionOptimizationResult:
    """Result of interlayer adhesion optimization."""
    success: bool
    optimized_settings: Dict[str, Any]
    expected_adhesion_improvement: float  # %
    temperature_profile: List[Tuple[float, float]]  # [layer, temperature]
    speed_profile: List[Tuple[float, float]]  # [layer, speed]
    fan_profile: List[Tuple[float, float]]  # [layer, fan_speed]
    reasoning: List[str]
    warnings: List[str]
    processing_time: float


class InterlayerAdhesionOptimizer:
    """Interlayer adhesion optimization engine."""

    def __init__(self, settings: InterlayerAdhesionSettings = None):
        """
        Initialize the interlayer adhesion optimizer.

        Args:
            settings: Interlayer adhesion optimization settings
        """
        self.settings = settings or InterlayerAdhesionSettings()
        self.logger = logging.getLogger(__name__)
        self.material_database = self._build_material_database()

    def _build_material_database(self) -> Dict[str, Dict[str, Any]]:
        """Build database of material adhesion properties."""
        return {
            "PLA": {
                "optimal_temp_range": (200, 220),
                "temp_sensitivity": "medium",
                "humidity_sensitivity": "low",
                "speed_sensitivity": "medium",
                "recommended_fan_speed": 30
            },
            "ABS": {
                "optimal_temp_range": (230, 250),
                "temp_sensitivity": "high",
                "humidity_sensitivity": "high",
                "speed_sensitivity": "low",
                "recommended_fan_speed": 20
            },
            "PETG": {
                "optimal_temp_range": (230, 250),
                "temp_sensitivity": "high",
                "humidity_sensitivity": "medium",
                "speed_sensitivity": "high",
                "recommended_fan_speed": 25
            },
            "TPU": {
                "optimal_temp_range": (210, 230),
                "temp_sensitivity": "medium",
                "humidity_sensitivity": "low",
                "speed_sensitivity": "high",
                "recommended_fan_speed": 40
            },
            "Nylon": {
                "optimal_temp_range": (240, 260),
                "temp_sensitivity": "high",
                "humidity_sensitivity": "very_high",
                "speed_sensitivity": "medium",
                "recommended_fan_speed": 15
            }
        }

    def optimize_adhesion(self, mesh: trimesh.Trimesh,
                         print_settings: Dict[str, Any] = None) -> AdhesionOptimizationResult:
        """
        Optimize interlayer adhesion for the given mesh.

        Args:
            mesh: Input mesh to optimize for
            print_settings: Current print settings

        Returns:
            AdhesionOptimizationResult with optimized settings
        """
        start_time = time.time()
        reasoning = []
        warnings = []

        try:
            # Step 1: Analyze mesh characteristics
            mesh_analysis = self._analyze_mesh_for_adhesion(mesh)
            reasoning.append(f"Mesh analysis: {mesh_analysis}")

            # Step 2: Get material properties
            material_props = self._get_material_properties()
            reasoning.append(f"Material properties: {material_props}")

            # Step 3: Analyze current settings
            current_analysis = self._analyze_current_settings(print_settings)
            reasoning.append(f"Current settings analysis: {current_analysis}")

            # Step 4: Generate temperature profile
            temp_profile = self._optimize_temperature_profile(mesh, material_props)
            reasoning.append("Generated temperature profile")

            # Step 5: Generate speed profile
            speed_profile = self._optimize_speed_profile(mesh, material_props)
            reasoning.append("Generated speed profile")

            # Step 6: Generate fan control profile
            fan_profile = self._optimize_fan_profile(mesh, material_props)
            reasoning.append("Generated fan profile")

            # Step 7: Calculate expected improvement
            expected_improvement = self._calculate_expected_improvement(
                mesh_analysis, material_props, current_analysis
            )

            # Step 8: Generate warnings
            warnings = self._generate_warnings(material_props, mesh_analysis)

            processing_time = time.time() - start_time

            # Compile optimized settings
            optimized_settings = {
                'temperature_profile': temp_profile,
                'speed_profile': speed_profile,
                'fan_profile': fan_profile,
                'base_temperature': material_props['optimal_temp_range'][0],
                'base_speed': self.settings.print_speed,
                'enable_adaptive_control': True
            }

            return AdhesionOptimizationResult(
                success=True,
                optimized_settings=optimized_settings,
                expected_adhesion_improvement=expected_improvement,
                temperature_profile=temp_profile,
                speed_profile=speed_profile,
                fan_profile=fan_profile,
                reasoning=reasoning,
                warnings=warnings,
                processing_time=processing_time
            )

        except Exception as e:
            self.logger.error(f"Adhesion optimization failed: {e}")
            processing_time = time.time() - start_time

            return AdhesionOptimizationResult(
                success=False,
                optimized_settings={},
                expected_adhesion_improvement=0.0,
                temperature_profile=[],
                speed_profile=[],
                fan_profile=[],
                reasoning=[f"Optimization failed: {str(e)}"],
                warnings=["Adhesion optimization failed, using default settings"],
                processing_time=processing_time
            )

    def _analyze_mesh_for_adhesion(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Analyze mesh characteristics affecting interlayer adhesion."""
        analysis = {}

        try:
            # Calculate layer count
            height = mesh.extents[2]
            layer_count = int(height / self.settings.layer_height) if height > 0 else 50
            analysis['layer_count'] = layer_count

            # Analyze surface area per layer
            surface_area = mesh.area
            analysis['surface_area_per_layer'] = surface_area / layer_count

            # Analyze overhang complexity
            overhang_complexity = self._calculate_overhang_complexity(mesh)
            analysis['overhang_complexity'] = overhang_complexity

            # Analyze thin features
            thin_feature_ratio = self._calculate_thin_feature_ratio(mesh)
            analysis['thin_feature_ratio'] = thin_feature_ratio

            # Calculate cooling time requirements
            cooling_factor = self._calculate_cooling_factor(mesh)
            analysis['cooling_factor'] = cooling_factor

        except Exception as e:
            self.logger.warning(f"Mesh adhesion analysis failed: {e}")
            analysis = {
                'layer_count': 50,
                'surface_area_per_layer': 100.0,
                'overhang_complexity': 0.5,
                'thin_feature_ratio': 0.1,
                'cooling_factor': 1.0
            }

        return analysis

    def _calculate_overhang_complexity(self, mesh: trimesh.Trimesh) -> float:
        """Calculate overhang complexity (0-1 scale)."""
        try:
            overhang_count = 0
            for normal in mesh.face_normals:
                angle = np.degrees(np.arccos(max(-1.0, min(1.0, normal[2]))))
                if angle > 45:
                    overhang_count += 1

            return overhang_count / len(mesh.faces)
        except:
            return 0.5

    def _calculate_thin_feature_ratio(self, mesh: trimesh.Trimesh) -> float:
        """Calculate ratio of thin features requiring careful adhesion."""
        try:
            thin_faces = 0
            for area in mesh.area_faces:
                if area < 2.0:  # Small faces
                    thin_faces += 1

            return thin_faces / len(mesh.faces)
        except:
            return 0.1

    def _calculate_cooling_factor(self, mesh: trimesh.Trimesh) -> float:
        """Calculate cooling requirements based on geometry."""
        try:
            # Larger parts and complex geometries need more cooling control
            volume = mesh.volume if mesh.volume > 0 else 1000.0
            complexity = len(mesh.faces) / max(volume, 1.0)

            cooling_factor = 1.0 + (complexity / 10.0) + (volume / 10000.0)
            return min(2.0, cooling_factor)
        except:
            return 1.0

    def _get_material_properties(self) -> Dict[str, Any]:
        """Get material-specific adhesion properties."""
        return self.material_database.get(self.settings.material_type, {
            "optimal_temp_range": (200, 220),
            "temp_sensitivity": "medium",
            "humidity_sensitivity": "low",
            "speed_sensitivity": "medium",
            "recommended_fan_speed": 30
        })

    def _analyze_current_settings(self, print_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current print settings for adhesion optimization."""
        analysis = {
            'temperature_adequate': True,
            'speed_adequate': True,
            'fan_control_adequate': True,
            'humidity_controlled': self.settings.humidity < 60
        }

        if print_settings:
            # Check temperature settings
            temp = print_settings.get('nozzle_temperature', 200)
            material_props = self._get_material_properties()
            temp_range = material_props['optimal_temp_range']

            if not (temp_range[0] <= temp <= temp_range[1]):
                analysis['temperature_adequate'] = False

            # Check speed settings
            speed = print_settings.get('print_speed', 50)
            if speed > 60:  # Too fast for good adhesion
                analysis['speed_adequate'] = False

        return analysis

    def _optimize_temperature_profile(self, mesh: trimesh.Trimesh,
                                    material_props: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Generate optimized temperature profile."""
        profile = []
        layer_count = int(mesh.extents[2] / self.settings.layer_height) if mesh.extents[2] > 0 else 50

        try:
            base_temp = material_props['optimal_temp_range'][0]

            for layer in range(min(layer_count, 100)):  # Limit to first 100 layers for profile
                # Temperature variation based on layer height and complexity
                layer_ratio = layer / max(layer_count, 1)

                if layer_ratio < 0.1:  # First layers - slightly higher temp for bed adhesion
                    temp = base_temp + 5
                elif layer_ratio > 0.8:  # Top layers - slightly lower temp for detail
                    temp = base_temp - 3
                else:  # Middle layers - optimal temperature
                    temp = base_temp

                profile.append((float(layer), temp))

        except Exception as e:
            self.logger.warning(f"Temperature profile generation failed: {e}")
            profile = [(0.0, base_temp)]

        return profile

    def _optimize_speed_profile(self, mesh: trimesh.Trimesh,
                              material_props: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Generate optimized speed profile."""
        profile = []
        layer_count = int(mesh.extents[2] / self.settings.layer_height) if mesh.extents[2] > 0 else 50

        try:
            base_speed = self.settings.print_speed

            for layer in range(min(layer_count, 100)):
                layer_ratio = layer / max(layer_count, 1)

                if layer_ratio < 0.05:  # First few layers - slower for adhesion
                    speed = base_speed * 0.7
                elif layer_ratio > 0.95:  # Top layers - slightly faster for detail
                    speed = base_speed * 1.1
                else:  # Middle layers - normal speed
                    speed = base_speed

                profile.append((float(layer), speed))

        except Exception as e:
            self.logger.warning(f"Speed profile generation failed: {e}")
            profile = [(0.0, base_speed)]

        return profile

    def _optimize_fan_profile(self, mesh: trimesh.Trimesh,
                            material_props: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Generate optimized fan control profile."""
        profile = []
        layer_count = int(mesh.extents[2] / self.settings.layer_height) if mesh.extents[2] > 0 else 50

        try:
            base_fan_speed = material_props.get('recommended_fan_speed', 30)

            for layer in range(min(layer_count, 100)):
                layer_ratio = layer / max(layer_count, 1)

                if layer_ratio < 0.1:  # First layers - minimal cooling
                    fan_speed = base_fan_speed * 0.3
                elif layer_ratio < 0.3:  # Early layers - gradual increase
                    fan_speed = base_fan_speed * (layer_ratio / 0.3)
                else:  # Later layers - normal cooling
                    fan_speed = base_fan_speed

                profile.append((float(layer), min(100.0, fan_speed)))

        except Exception as e:
            self.logger.warning(f"Fan profile generation failed: {e}")
            profile = [(0.0, base_fan_speed)]

        return profile

    def _calculate_expected_improvement(self, mesh_analysis: Dict[str, Any],
                                      material_props: Dict[str, Any],
                                      current_analysis: Dict[str, Any]) -> float:
        """Calculate expected adhesion improvement."""
        try:
            improvement = 0.0

            # Base improvement from optimization
            improvement += 15.0

            # Additional improvement based on current settings
            if not current_analysis.get('temperature_adequate', True):
                improvement += 10.0

            if not current_analysis.get('speed_adequate', True):
                improvement += 8.0

            # Improvement based on material sensitivity
            if material_props.get('temp_sensitivity') == 'high':
                improvement += 5.0

            # Improvement based on mesh complexity
            complexity_factor = mesh_analysis.get('overhang_complexity', 0.5)
            improvement += complexity_factor * 10.0

            return min(50.0, improvement)  # Cap at 50% improvement

        except:
            return 20.0  # Default improvement

    def _generate_warnings(self, material_props: Dict[str, Any],
                         mesh_analysis: Dict[str, Any]) -> List[str]:
        """Generate warnings for adhesion optimization."""
        warnings = []

        # Material-specific warnings
        if material_props.get('humidity_sensitivity') == 'high':
            if self.settings.humidity > 60:
                warnings.append("High humidity may affect interlayer adhesion")

        # Mesh-specific warnings
        if mesh_analysis.get('thin_feature_ratio', 0) > 0.3:
            warnings.append("Thin features may be prone to delamination")

        if mesh_analysis.get('overhang_complexity', 0) > 0.7:
            warnings.append("Complex overhangs require careful temperature control")

        return warnings


def optimize_interlayer_adhesion(mesh: trimesh.Trimesh,
                               material_type: str = "PLA",
                               target_quality: AdhesionQuality = AdhesionQuality.GOOD,
                               print_settings: Dict[str, Any] = None,
                               settings: InterlayerAdhesionSettings = None) -> AdhesionOptimizationResult:
    """
    Convenience function for interlayer adhesion optimization.

    Args:
        mesh: Input mesh to optimize for
        material_type: Material being used
        target_quality: Target adhesion quality
        print_settings: Current print settings
        settings: Optional interlayer adhesion settings

    Returns:
        AdhesionOptimizationResult with optimized settings
    """
    if settings is None:
        settings = InterlayerAdhesionSettings(
            material_type=material_type,
            target_quality=target_quality
        )
    else:
        settings.material_type = material_type
        settings.target_quality = target_quality

    optimizer = InterlayerAdhesionOptimizer(settings)
    return optimizer.optimize_adhesion(mesh, print_settings)
