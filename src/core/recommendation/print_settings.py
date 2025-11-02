"""Print settings recommendation engine."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import trimesh

from ..analysis.mesh_validator import MeshValidationMetrics, MeshValidationResult
from ..materials import (
    MaterialDatabase, get_material_database, MaterialSelector, SelectionRequirements,
    MaterialType, PrinterType, MaterialPreset, create_requirements_from_application
)
from ..materials.presets import MaterialPresetManager
from ..logging import get_logger
    SLA = "sla"
    SLS = "sls"
    MULTI_MATERIAL = "multi_material"


@dataclass(frozen=True)
class MaterialPreset:
    """Material property definitions."""
    name: str
    material_type: MaterialType
    printer_type: PrinterType

    # Temperature settings (°C)
    nozzle_temp_min: int
    nozzle_temp_max: int
    bed_temp: int

    # Print speeds (mm/min)
    print_speed: int
    travel_speed: int
    first_layer_speed: int

    # Layer settings (mm)
    layer_height_min: float
    layer_height_max: float
    layer_height_recommended: float

    # Mechanical properties
    density: float  # g/cm³
    shrinkage_factor: float  # %
    min_wall_thickness: float  # mm
    min_feature_size: float  # mm

    # Support and adhesion
    support_angle_threshold: float  # degrees
    bed_adhesion_type: str  # "none", "brim", "raft"
    cooling_fan: bool

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = asdict(self)
        result['material_type'] = self.material_type.value
        result['printer_type'] = self.printer_type.value
        return result


@dataclass
class PrintRecommendations:
    """Complete print recommendations for a model."""
    material_preset: MaterialPreset

    # Temperature recommendations
    nozzle_temperature: int
    bed_temperature: int

    # Speed recommendations
    print_speed: int
    first_layer_speed: int

    # Layer and geometry
    layer_height: float
    line_width: float
    infill_density: float  # %

    # Support structures
    supports_required: bool
    support_type: str  # "tree", "linear", "none"
    support_density: float  # %
    support_angle: float  # degrees

    # Adhesion and cooling
    bed_adhesion: str
    cooling_fan_speed: float  # %

    # Print time and material estimates
    estimated_print_time_hours: float
    estimated_material_volume_cm3: float
    estimated_material_cost_usd: float

    # Quality settings
    shell_thickness: float
    top_bottom_layers: int

    # Orientation recommendations
    optimal_orientation: Tuple[float, float, float]  # Euler angles
    orientation_reason: str

    # Explainability metadata
    rationales: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = asdict(self)
        result['material_preset'] = self.material_preset.to_dict()
        return result


class RecommendationEngine:
    """Analyzes mesh validation results and provides print recommendations."""

    def __init__(self):
        self._material_presets = self._load_default_materials()

    def _load_default_materials(self) -> Dict[str, MaterialPreset]:
        """Load default material presets."""
        presets = {}

        # PLA - beginner friendly
        presets['pla_standard'] = MaterialPreset(
            name="PLA Standard",
            material_type=MaterialType.PLA,
            printer_type=PrinterType.FDM,
            nozzle_temp_min=190,
            nozzle_temp_max=220,
            bed_temp=60,
            print_speed=3600,  # 60 mm/s
            travel_speed=9000,  # 150 mm/s
            first_layer_speed=1800,  # 30 mm/s
            layer_height_min=0.1,
            layer_height_max=0.3,
            layer_height_recommended=0.2,
            density=1.24,
            shrinkage_factor=0.3,
            min_wall_thickness=0.8,
            min_feature_size=0.4,
            support_angle_threshold=60.0,
            bed_adhesion_type="brim",
            cooling_fan=True
        )

        # ABS - higher strength
        presets['abs_standard'] = MaterialPreset(
            name="ABS Standard",
            material_type=MaterialType.ABS,
            printer_type=PrinterType.FDM,
            nozzle_temp_min=220,
            nozzle_temp_max=260,
            bed_temp=100,
            print_speed=3000,  # 50 mm/s
            travel_speed=9000,
            first_layer_speed=1500,  # 25 mm/s
            layer_height_min=0.1,
            layer_height_max=0.4,
            layer_height_recommended=0.25,
            density=1.05,
            shrinkage_factor=0.8,
            min_wall_thickness=1.2,
            min_feature_size=0.6,
            support_angle_threshold=45.0,
            bed_adhesion_type="raft",
            cooling_fan=False
        )

        # PETG - chemical resistance
        presets['petg_standard'] = MaterialPreset(
            name="PETG Standard",
            material_type=MaterialType.PETG,
            printer_type=PrinterType.FDM,
            nozzle_temp_min=220,
            nozzle_temp_max=250,
            bed_temp=80,
            print_speed=2400,  # 40 mm/s
            travel_speed=7200,
            first_layer_speed=1200,  # 20 mm/s
            layer_height_min=0.15,
            layer_height_max=0.3,
            layer_height_recommended=0.2,
            density=1.27,
            shrinkage_factor=0.2,
            min_wall_thickness=1.0,
            min_feature_size=0.5,
            support_angle_threshold=50.0,
            bed_adhesion_type="brim",
            cooling_fan=True
        )

        # Resin - high detail
        presets['resin_standard'] = MaterialPreset(
            name="Standard Resin",
            material_type=MaterialType.RESIN,
            printer_type=PrinterType.SLA,
            nozzle_temp_min=0,  # Not applicable
            nozzle_temp_max=0,
            bed_temp=0,
            print_speed=0,  # Different units for SLA
            travel_speed=0,
            first_layer_speed=0,
            layer_height_min=0.01,
            layer_height_max=0.2,
            layer_height_recommended=0.05,
            density=1.15,
            shrinkage_factor=0.1,
            min_wall_thickness=0.4,
            min_feature_size=0.1,
            support_angle_threshold=30.0,
            bed_adhesion_type="none",
            cooling_fan=False
        )

        return presets

    def recommend_material(self, validation_result: MeshValidationResult) -> str:
        """Recommend material based on model characteristics."""
        if not validation_result.metrics:
            return "pla_standard"

        metrics = validation_result.metrics

        # High detail requirements -> Resin
        if (metrics.min_feature_size_mm < 0.2 or
            metrics.surface_roughness_score < 0.1):
            return "resin_standard"

        # Large models -> ABS for strength
        volume_cm3 = metrics.volume_cm3
        if volume_cm3 > 100:
            return "abs_standard"

        # Chemical resistance or mechanical stress -> PETG
        if (metrics.sharp_internal_corners > 10 or
            metrics.thin_tip_faces > 5):
            return "petg_standard"

        # Default to PLA for general use
        return "pla_standard"

    def calculate_infill_density(self, validation_result: MeshValidationResult) -> float:
        """Calculate optimal infill density based on model characteristics."""
        if not validation_result.metrics:
            return 15.0

        metrics = validation_result.metrics
        base_density = 15.0

        # Increase for thin walls
        if metrics.min_wall_thickness_mm < 1.2:
            base_density += 10.0

        # Increase for stress concentration areas
        if metrics.sharp_internal_corners > 5:
            base_density += 15.0

        # Increase for functional parts (large volume)
        if metrics.volume_cm3 > 50:
            base_density += 10.0

        # Decrease for decorative parts (high surface quality)
        if metrics.surface_roughness_score < 0.5:
            base_density -= 5.0

        return min(max(base_density, 10.0), 100.0)

    def estimate_print_time(self,
                          validation_result: MeshValidationResult,
                          material_preset: MaterialPreset,
                          layer_height: float,
                          infill_density: float) -> float:
        """Estimate print time in hours."""
        if not validation_result.metrics:
            return 1.0

        metrics = validation_result.metrics

        # Base calculation from volume and layer height
        layers = max(metrics.bounding_box_mm[2] / layer_height, 1)

        # Estimate print area per layer (simplified)
        base_area = metrics.bounding_box_mm[0] * metrics.bounding_box_mm[1]
        print_area_per_layer = min(base_area * 0.7, metrics.surface_area_mm2 / layers)

        # Calculate time based on print speed
        speed_mm_per_min = material_preset.print_speed
        speed_mm2_per_min = speed_mm_per_min * 0.4  # Line width approximation

        layer_time_min = print_area_per_layer / speed_mm2_per_min

        # Add infill time
        infill_factor = 1.0 + (infill_density / 100.0) * 0.5
        layer_time_min *= infill_factor

        # Add support time
        if metrics.overhang_face_count > 0:
            layer_time_min *= 1.3

        total_time_hours = (layers * layer_time_min) / 60.0

        # Add setup and finishing time
        return max(total_time_hours + 0.5, 0.1)

    def determine_optimal_orientation(self, validation_result: MeshValidationResult) -> Tuple[Tuple[float, float, float], str]:
        """Determine optimal print orientation."""
        if not validation_result.metrics:
            return (0.0, 0.0, 0.0), "Default orientation"

        metrics = validation_result.metrics

        # Use pre-calculated auto-orientation if available
        if metrics.auto_orientation_euler_deg:
            euler = tuple(metrics.auto_orientation_euler_deg[:3])

            # Determine reason
            if metrics.overhang_face_count > 10:
                reason = "Minimized overhangs for support reduction"
            elif metrics.bed_contact_area_mm2 < 200:
                reason = "Maximized bed contact area for stability"
            else:
                reason = "Balanced orientation for quality and support"

            return euler, reason

        return (0.0, 0.0, 0.0), "Default orientation"

    def generate_recommendations(self, validation_result: MeshValidationResult) -> PrintRecommendations:
        """Generate comprehensive print recommendations."""
        # Select optimal material
        material_key = self.recommend_material(validation_result)
        material_preset = self._material_presets[material_key]
        rationales: List[Dict[str, str]] = []

        material_reason_en = "Selected material preset '{}' for {} printer to match geometry requirements.".format(
            material_preset.name,
            material_preset.printer_type.value.upper()
        )
        material_reason_ja = "形状要件に合わせるため、{} プリンタ向けに '{}' プリセットを選択しました。".format(
            material_preset.printer_type.value.upper(),
            material_preset.name
        )
        rationales.append({
            "code": "material_selection",
            "en": material_reason_en,
            "ja": material_reason_ja
        })

        # Calculate layer height
        if validation_result.metrics and validation_result.metrics.min_feature_size_mm < 0.3:
            layer_height = material_preset.layer_height_min
            rationales.append({
                "code": "layer_height",
                "en": "Fine features detected; using minimum layer height {:.2f} mm.".format(layer_height),
                "ja": "細かい形状を検出したため、最小層厚 {:.2f} mm を採用しました。".format(layer_height)
            })
        else:
            layer_height = material_preset.layer_height_recommended
            rationales.append({
                "code": "layer_height",
                "en": "Using recommended layer height {:.2f} mm for balanced quality.".format(layer_height),
                "ja": "品質と速度の両立のため、推奨層厚 {:.2f} mm を使用します。".format(layer_height)
            })

        # Calculate infill
        infill_density = self.calculate_infill_density(validation_result)
        rationales.append({
            "code": "infill_density",
            "en": "Infill set to {:.1f}% based on wall thickness and stress indicators.".format(infill_density),
            "ja": "肉厚と応力指標に基づきインフィル密度を {:.1f}% に設定しました。".format(infill_density)
        })

        # Determine support requirements
        supports_required = False
        support_angle = material_preset.support_angle_threshold

        if validation_result.metrics:
            supports_required = validation_result.metrics.overhang_face_count > 0
            if supports_required:
                rationales.append({
                    "code": "supports",
                    "en": "Detected overhang faces; enabling supports at {:.0f}° threshold.".format(support_angle),
                    "ja": "オーバーハング面を検出したため、{:.0f}° 閾値でサポートを有効化します。".format(support_angle)
                })
            else:
                rationales.append({
                    "code": "supports",
                    "en": "No critical overhangs; supports not required.",
                    "ja": "重要なオーバーハングがないためサポートは不要です。"
                })

        # Calculate orientation
        orientation, orientation_reason = self.determine_optimal_orientation(validation_result)
        rationales.append({
            "code": "orientation",
            "en": orientation_reason,
            "ja": "{}".format(orientation_reason)
        })

        # Estimate print time
        print_time = self.estimate_print_time(validation_result, material_preset, layer_height, infill_density)

        # Estimate material usage
        material_volume = validation_result.metrics.volume_cm3 if validation_result.metrics else 10.0
        material_volume *= (1.0 + infill_density / 100.0)  # Account for infill
        if supports_required:
            material_volume *= 1.2  # Account for supports

        # Estimate cost (rough approximation)
        cost_per_cm3 = 0.05  # USD per cm³ for standard PLA
        if material_preset.material_type == MaterialType.ABS:
            cost_per_cm3 = 0.06
        elif material_preset.material_type == MaterialType.RESIN:
            cost_per_cm3 = 0.15

        estimated_cost = material_volume * cost_per_cm3
        rationales.append({
            "code": "cost_estimate",
            "en": "Estimated material cost ${:.2f} using cost factor ${:.2f}/cm³.".format(estimated_cost, cost_per_cm3),
            "ja": "材料単価 ${:.2f}/cm³ を基準に推定コスト ${:.2f} を算出しました。".format(cost_per_cm3, estimated_cost)
        })

        return PrintRecommendations(
            material_preset=material_preset,
            nozzle_temperature=(material_preset.nozzle_temp_min + material_preset.nozzle_temp_max) // 2,
            bed_temperature=material_preset.bed_temp,
            print_speed=material_preset.print_speed,
            first_layer_speed=material_preset.first_layer_speed,
            layer_height=layer_height,
            line_width=0.4,  # Standard nozzle width
            infill_density=infill_density,
            supports_required=supports_required,
            support_type="tree" if supports_required else "none",
            support_density=15.0 if supports_required else 0.0,
            support_angle=support_angle,
            bed_adhesion=material_preset.bed_adhesion_type,
            cooling_fan_speed=100.0 if material_preset.cooling_fan else 0.0,
            estimated_print_time_hours=print_time,
            estimated_material_volume_cm3=material_volume,
            estimated_material_cost_usd=estimated_cost,
            shell_thickness=1.2,
            top_bottom_layers=3,
            optimal_orientation=orientation,
            orientation_reason=orientation_reason,
            rationales=rationales
        )

    def save_recommendations(self, recommendations: PrintRecommendations, output_path: Path):
        """Save recommendations to JSON file."""
        output_path.write_text(
            json.dumps(recommendations.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def get_available_materials(self) -> List[str]:
        """Get list of available material preset names."""
        return list(self._material_presets.keys())

    def get_material_preset(self, name: str) -> Optional[MaterialPreset]:
        """Get material preset by name."""
        return self._material_presets.get(name)