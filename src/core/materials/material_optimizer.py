"""Advanced Materials Science Integration for 3D Print CAD Assistant."""

from __future__ import annotations

import numpy as np
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import hashlib
import time

logger = logging.getLogger(__name__)


class MaterialType(Enum):
    """Supported 3D printing materials."""
    PLA = "PLA"
    ABS = "ABS"
    PETG = "PETG"
    TPU = "TPU"
    NYLON = "Nylon"
    PC = "Polycarbonate"
    PVA = "PVA"
    HIPS = "HIPS"
    WOOD_FILL = "Wood Fill"
    METAL_FILL = "Metal Fill"
    CARBON_FIBER = "Carbon Fiber"
    ASA = "ASA"
    PMMA = "PMMA"
    PP = "Polypropylene"
    FLEXIBLE = "Flexible"
    COMPOSITE = "Composite"
    CERAMIC = "Ceramic"
    METAL = "Metal"


class MaterialProperty(Enum):
    """Material properties for optimization."""
    TENSILE_STRENGTH = "tensile_strength"
    FLEXURAL_STRENGTH = "flexural_strength"
    COMPRESSIVE_STRENGTH = "compressive_strength"
    IMPACT_STRENGTH = "impact_strength"
    HARDNESS = "hardness"
    DENSITY = "density"
    MELTING_POINT = "melting_point"
    GLASS_TRANSITION = "glass_transition"
    THERMAL_EXPANSION = "thermal_expansion"
    THERMAL_CONDUCTIVITY = "thermal_conductivity"
    ELECTRICAL_CONDUCTIVITY = "electrical_conductivity"
    CHEMICAL_RESISTANCE = "chemical_resistance"
    UV_RESISTANCE = "uv_resistance"
    MOISTURE_ABSORPTION = "moisture_absorption"
    SHRINKAGE = "shrinkage"
    WARPING = "warping"
    BED_ADHESION = "bed_adhesion"
    LAYER_ADHESION = "layer_adhesion"


@dataclass
class MaterialProfile:
    """Comprehensive material profile for 3D printing optimization."""

    material_id: str
    name: str
    type: MaterialType
    manufacturer: str
    grade: str

    # Physical properties
    density_g_cm3: float
    melting_point_c: float
    glass_transition_c: Optional[float] = None

    # Mechanical properties
    tensile_strength_mpa: Optional[float] = None
    flexural_strength_mpa: Optional[float] = None
    compressive_strength_mpa: Optional[float] = None
    impact_strength_j_m: Optional[float] = None
    hardness_shore: Optional[float] = None

    # Thermal properties
    thermal_expansion_coefficient: Optional[float] = None
    thermal_conductivity_w_mk: Optional[float] = None

    # Printing properties
    recommended_nozzle_temp_min: float = 180
    recommended_nozzle_temp_max: float = 250
    recommended_bed_temp_min: float = 20
    recommended_bed_temp_max: float = 80
    shrinkage_percent: float = 0.0
    warping_risk: float = 0.0  # 0-1 scale
    bed_adhesion_rating: float = 0.5  # 0-1 scale
    layer_adhesion_rating: float = 0.8  # 0-1 scale

    # Environmental resistance
    uv_resistance_rating: float = 0.3  # 0-1 scale
    chemical_resistance_rating: float = 0.4  # 0-1 scale
    moisture_absorption_percent: float = 0.0

    # Cost and availability
    cost_per_kg_usd: Optional[float] = None
    availability_rating: float = 0.8  # 0-1 scale

    # Compatibility
    compatible_printers: List[str] = field(default_factory=list)
    compatible_nozzle_sizes: List[float] = field(default_factory=list)

    # Optimization parameters
    strength_to_weight_ratio: Optional[float] = None
    cost_effectiveness_score: Optional[float] = None
    environmental_impact_score: Optional[float] = None

    def calculate_optimization_score(self, requirements: Dict[MaterialProperty, float]) -> float:
        """Calculate material optimization score based on requirements."""
        score = 0.0
        total_weight = 0.0

        # Mechanical requirements
        if MaterialProperty.TENSILE_STRENGTH in requirements and self.tensile_strength_mpa:
            weight = requirements[MaterialProperty.TENSILE_STRENGTH]
            score += weight * min(self.tensile_strength_mpa / 100, 1.0)  # Normalize to 0-1
            total_weight += weight

        if MaterialProperty.FLEXURAL_STRENGTH in requirements and self.flexural_strength_mpa:
            weight = requirements[MaterialProperty.FLEXURAL_STRENGTH]
            score += weight * min(self.flexural_strength_mpa / 150, 1.0)
            total_weight += weight

        # Thermal requirements
        if MaterialProperty.MELTING_POINT in requirements and self.melting_point_c:
            weight = requirements[MaterialProperty.MELTING_POINT]
            score += weight * min(self.melting_point_c / 300, 1.0)
            total_weight += weight

        # Printing requirements
        if MaterialProperty.BED_ADHESION in requirements:
            weight = requirements[MaterialProperty.BED_ADHESION]
            score += weight * self.bed_adhesion_rating
            total_weight += weight

        if MaterialProperty.WARPING in requirements:
            weight = requirements[MaterialProperty.WARPING]
            score += weight * (1.0 - self.warping_risk)  # Lower warping is better
            total_weight += weight

        # Cost effectiveness
        if MaterialProperty.DENSITY in requirements and self.cost_per_kg_usd:
            weight = requirements[MaterialProperty.DENSITY]
            cost_effectiveness = self.strength_to_weight_ratio or (self.tensile_strength_mpa or 50) / (self.density_g_cm3 * self.cost_per_kg_usd)
            score += weight * min(cost_effectiveness / 10, 1.0)
            total_weight += weight

        return score / total_weight if total_weight > 0 else 0.5

    def get_recommended_print_settings(self) -> Dict[str, Any]:
        """Get recommended print settings for this material."""
        return {
            'nozzle_temperature': (self.recommended_nozzle_temp_min + self.recommended_nozzle_temp_max) / 2,
            'bed_temperature': (self.recommended_bed_temp_min + self.recommended_bed_temp_max) / 2,
            'print_speed': 50,  # Base speed, adjust based on material
            'layer_height': 0.2,
            'infill_density': 20,
            'supports_needed': self.warping_risk > 0.3,
            'brim_needed': self.warping_risk > 0.5,
            'cooling_fan_speed': 100 if self.warping_risk < 0.3 else 50
        }

    def estimate_print_time(self, model_volume: float, settings: Dict[str, Any]) -> float:
        """Estimate print time based on material properties and model characteristics."""
        base_time = model_volume * 10  # Base time per cm³

        # Adjust for material properties
        if self.warping_risk > 0.5:
            base_time *= 1.2  # Slower printing to reduce warping

        if self.bed_adhesion_rating < 0.5:
            base_time *= 1.1  # Additional time for better adhesion

        # Adjust for print settings
        layer_height = settings.get('layer_height', 0.2)
        base_time /= layer_height  # Thinner layers = more time

        print_speed = settings.get('print_speed', 50)
        base_time *= (60 / print_speed)  # Slower speed = more time

        return base_time

    def estimate_material_usage(self, model_volume: float, infill_density: float = 20) -> float:
        """Estimate material usage in grams."""
        # Base material for walls and surfaces
        surface_material = model_volume * self.density_g_cm3 * 1000

        # Additional material for infill
        infill_material = (model_volume * infill_density / 100) * self.density_g_cm3 * 1000

        # Account for support structures (simplified)
        support_material = surface_material * 0.1 if self.warping_risk > 0.3 else 0

        total_grams = surface_material + infill_material + support_material

        # Add waste factor based on material properties
        waste_factor = 1.0 + (self.shrinkage_percent / 100) + (self.warping_risk * 0.1)

        return total_grams * waste_factor

    def get_environmental_impact(self) -> Dict[str, float]:
        """Get environmental impact assessment."""
        return {
            'carbon_footprint_per_kg': 2.5 + (self.cost_per_kg_usd or 20) * 0.1,  # Higher cost materials may have higher impact
            'recyclability_score': 0.8 if self.type in [MaterialType.PLA, MaterialType.PETG] else 0.4,
            'biodegradability_score': 0.9 if self.type == MaterialType.PLA else 0.1,
            'toxicity_score': 0.1,  # Most 3D printing materials have low toxicity
            'energy_consumption_per_kg': 15.0 + (self.melting_point_c / 200) * 5  # Higher melting point = more energy
        }


class MaterialDatabase:
    """Comprehensive database of 3D printing materials."""

    def __init__(self, database_file: Optional[Path] = None):
        self.database_file = database_file or Path.home() / '.printcad' / 'materials.json'
        self.database_file.parent.mkdir(parents=True, exist_ok=True)
        self.materials: Dict[str, MaterialProfile] = {}
        self.logger = logging.getLogger(__name__)

        # Initialize with comprehensive material profiles
        self._initialize_default_materials()
        self._load_custom_materials()

    def _initialize_default_materials(self):
        """Initialize database with comprehensive material profiles."""

        # PLA (Polylactic Acid) - Most common 3D printing material
        pla_profile = MaterialProfile(
            material_id="pla_standard",
            name="PLA Standard",
            type=MaterialType.PLA,
            manufacturer="Generic",
            grade="Standard",
            density_g_cm3=1.24,
            melting_point_c=150,
            glass_transition_c=60,
            tensile_strength_mpa=50,
            flexural_strength_mpa=80,
            impact_strength_j_m=25,
            hardness_shore=85,
            recommended_nozzle_temp_min=180,
            recommended_nozzle_temp_max=220,
            recommended_bed_temp_min=20,
            recommended_bed_temp_max=60,
            shrinkage_percent=0.2,
            warping_risk=0.1,
            bed_adhesion_rating=0.8,
            layer_adhesion_rating=0.9,
            uv_resistance_rating=0.2,
            chemical_resistance_rating=0.3,
            moisture_absorption_percent=0.5,
            cost_per_kg_usd=15,
            compatible_printers=["All"],
            compatible_nozzle_sizes=[0.2, 0.3, 0.4, 0.5, 0.6, 0.8],
            strength_to_weight_ratio=40,
            cost_effectiveness_score=0.9,
            environmental_impact_score=0.8
        )
        self.materials[pla_profile.material_id] = pla_profile

        # ABS (Acrylonitrile Butadiene Styrene) - Engineering grade
        abs_profile = MaterialProfile(
            material_id="abs_standard",
            name="ABS Standard",
            type=MaterialType.ABS,
            manufacturer="Generic",
            grade="Standard",
            density_g_cm3=1.04,
            melting_point_c=220,
            glass_transition_c=105,
            tensile_strength_mpa=40,
            flexural_strength_mpa=70,
            impact_strength_j_m=200,
            hardness_shore=80,
            recommended_nozzle_temp_min=220,
            recommended_nozzle_temp_max=260,
            recommended_bed_temp_min=80,
            recommended_bed_temp_max=110,
            shrinkage_percent=0.8,
            warping_risk=0.6,
            bed_adhesion_rating=0.6,
            layer_adhesion_rating=0.8,
            uv_resistance_rating=0.1,
            chemical_resistance_rating=0.7,
            moisture_absorption_percent=0.3,
            cost_per_kg_usd=18,
            compatible_printers=["All"],
            compatible_nozzle_sizes=[0.3, 0.4, 0.5, 0.6, 0.8],
            strength_to_weight_ratio=38,
            cost_effectiveness_score=0.7,
            environmental_impact_score=0.3
        )
        self.materials[abs_profile.material_id] = abs_profile

        # PETG (Polyethylene Terephthalate Glycol)
        petg_profile = MaterialProfile(
            material_id="petg_standard",
            name="PETG Standard",
            type=MaterialType.PETG,
            manufacturer="Generic",
            grade="Standard",
            density_g_cm3=1.27,
            melting_point_c=230,
            glass_transition_c=80,
            tensile_strength_mpa=50,
            flexural_strength_mpa=70,
            impact_strength_j_m=100,
            hardness_shore=85,
            recommended_nozzle_temp_min=220,
            recommended_nozzle_temp_max=250,
            recommended_bed_temp_min=60,
            recommended_bed_temp_max=80,
            shrinkage_percent=0.3,
            warping_risk=0.2,
            bed_adhesion_rating=0.9,
            layer_adhesion_rating=0.9,
            uv_resistance_rating=0.4,
            chemical_resistance_rating=0.9,
            moisture_absorption_percent=0.2,
            cost_per_kg_usd=20,
            compatible_printers=["All"],
            compatible_nozzle_sizes=[0.2, 0.3, 0.4, 0.5, 0.6, 0.8],
            strength_to_weight_ratio=39,
            cost_effectiveness_score=0.8,
            environmental_impact_score=0.7
        )
        self.materials[petg_profile.material_id] = petg_profile

        # TPU (Thermoplastic Polyurethane) - Flexible
        tpu_profile = MaterialProfile(
            material_id="tpu_95a",
            name="TPU 95A",
            type=MaterialType.TPU,
            manufacturer="Generic",
            grade="95A",
            density_g_cm3=1.20,
            melting_point_c=210,
            glass_transition_c=-20,
            tensile_strength_mpa=35,
            flexural_strength_mpa=25,
            impact_strength_j_m=500,
            hardness_shore=95,
            recommended_nozzle_temp_min=200,
            recommended_nozzle_temp_max=230,
            recommended_bed_temp_min=20,
            recommended_bed_temp_max=60,
            shrinkage_percent=0.5,
            warping_risk=0.1,
            bed_adhesion_rating=0.7,
            layer_adhesion_rating=0.9,
            uv_resistance_rating=0.3,
            chemical_resistance_rating=0.8,
            moisture_absorption_percent=0.8,
            cost_per_kg_usd=25,
            compatible_printers=["All"],
            compatible_nozzle_sizes=[0.4, 0.5, 0.6, 0.8],
            strength_to_weight_ratio=29,
            cost_effectiveness_score=0.6,
            environmental_impact_score=0.5
        )
        self.materials[tpu_profile.material_id] = tpu_profile

        # Nylon (Polyamide)
        nylon_profile = MaterialProfile(
            material_id="nylon_6",
            name="Nylon 6",
            type=MaterialType.NYLON,
            manufacturer="Generic",
            grade="PA6",
            density_g_cm3=1.14,
            melting_point_c=220,
            glass_transition_c=50,
            tensile_strength_mpa=75,
            flexural_strength_mpa=100,
            impact_strength_j_m=150,
            hardness_shore=85,
            recommended_nozzle_temp_min=240,
            recommended_nozzle_temp_max=280,
            recommended_bed_temp_min=80,
            recommended_bed_temp_max=100,
            shrinkage_percent=1.5,
            warping_risk=0.7,
            bed_adhesion_rating=0.4,
            layer_adhesion_rating=0.9,
            uv_resistance_rating=0.2,
            chemical_resistance_rating=0.9,
            moisture_absorption_percent=2.5,
            cost_per_kg_usd=30,
            compatible_printers=["Enclosed"],
            compatible_nozzle_sizes=[0.4, 0.5, 0.6, 0.8],
            strength_to_weight_ratio=66,
            cost_effectiveness_score=0.7,
            environmental_impact_score=0.4
        )
        self.materials[nylon_profile.material_id] = nylon_profile

        # Carbon Fiber Composite
        cf_profile = MaterialProfile(
            material_id="pla_carbon_fiber",
            name="PLA Carbon Fiber",
            type=MaterialType.CARBON_FIBER,
            manufacturer="Generic",
            grade="15% CF",
            density_g_cm3=1.30,
            melting_point_c=155,
            glass_transition_c=65,
            tensile_strength_mpa=85,
            flexural_strength_mpa=120,
            impact_strength_j_m=40,
            hardness_shore=90,
            recommended_nozzle_temp_min=190,
            recommended_nozzle_temp_max=230,
            recommended_bed_temp_min=40,
            recommended_bed_temp_max=70,
            shrinkage_percent=0.1,
            warping_risk=0.2,
            bed_adhesion_rating=0.9,
            layer_adhesion_rating=0.9,
            uv_resistance_rating=0.3,
            chemical_resistance_rating=0.4,
            moisture_absorption_percent=0.3,
            cost_per_kg_usd=45,
            compatible_printers=["Hardened Nozzle"],
            compatible_nozzle_sizes=[0.4, 0.5, 0.6, 0.8],
            strength_to_weight_ratio=65,
            cost_effectiveness_score=0.8,
            environmental_impact_score=0.3
        )
        self.materials[cf_profile.material_id] = cf_profile

        # Add more materials...
        self._add_specialty_materials()

    def _add_specialty_materials(self):
        """Add specialty and advanced materials."""

        # ASA (Acrylonitrile Styrene Acrylate) - UV resistant
        asa_profile = MaterialProfile(
            material_id="asa_standard",
            name="ASA Standard",
            type=MaterialType.ASA,
            manufacturer="Generic",
            grade="Standard",
            density_g_cm3=1.05,
            melting_point_c=240,
            glass_transition_c=100,
            tensile_strength_mpa=45,
            flexural_strength_mpa=75,
            impact_strength_j_m=180,
            hardness_shore=82,
            recommended_nozzle_temp_min=230,
            recommended_nozzle_temp_max=270,
            recommended_bed_temp_min=90,
            recommended_bed_temp_max=110,
            shrinkage_percent=0.4,
            warping_risk=0.3,
            bed_adhesion_rating=0.7,
            layer_adhesion_rating=0.8,
            uv_resistance_rating=0.9,
            chemical_resistance_rating=0.8,
            moisture_absorption_percent=0.4,
            cost_per_kg_usd=22,
            compatible_printers=["All"],
            compatible_nozzle_sizes=[0.3, 0.4, 0.5, 0.6, 0.8],
            strength_to_weight_ratio=43,
            cost_effectiveness_score=0.8,
            environmental_impact_score=0.4
        )
        self.materials[asa_profile.material_id] = asa_profile

        # PMMA (Polymethyl Methacrylate) - Clear
        pmma_profile = MaterialProfile(
            material_id="pmma_clear",
            name="PMMA Clear",
            type=MaterialType.PMMA,
            manufacturer="Generic",
            grade="Optical",
            density_g_cm3=1.19,
            melting_point_c=160,
            glass_transition_c=105,
            tensile_strength_mpa=65,
            flexural_strength_mpa=90,
            impact_strength_j_m=20,
            hardness_shore=90,
            recommended_nozzle_temp_min=220,
            recommended_nozzle_temp_max=250,
            recommended_bed_temp_min=80,
            recommended_bed_temp_max=100,
            shrinkage_percent=0.6,
            warping_risk=0.4,
            bed_adhesion_rating=0.6,
            layer_adhesion_rating=0.7,
            uv_resistance_rating=0.1,
            chemical_resistance_rating=0.6,
            moisture_absorption_percent=0.3,
            cost_per_kg_usd=35,
            compatible_printers=["Enclosed"],
            compatible_nozzle_sizes=[0.2, 0.3, 0.4],
            strength_to_weight_ratio=55,
            cost_effectiveness_score=0.6,
            environmental_impact_score=0.3
        )
        self.materials[pmma_profile.material_id] = pmma_profile

    def _load_custom_materials(self):
        """Load custom material profiles from file."""
        try:
            if self.database_file.exists():
                with open(self.database_file, 'r') as f:
                    custom_materials = json.load(f)

                for material_data in custom_materials:
                    try:
                        material = MaterialProfile(**material_data)
                        self.materials[material.material_id] = material
                    except Exception as e:
                        self.logger.warning(f"Failed to load custom material: {e}")

        except Exception as e:
            self.logger.warning(f"Could not load custom materials: {e}")

    def save_custom_materials(self):
        """Save custom material profiles to file."""
        try:
            # Get only custom materials (not default ones)
            custom_materials = []
            for material in self.materials.values():
                # Identify custom materials (simplified check)
                if material.manufacturer not in ["Generic"]:
                    custom_materials.append({
                        'material_id': material.material_id,
                        'name': material.name,
                        'type': material.type.value,
                        'manufacturer': material.manufacturer,
                        'grade': material.grade,
                        'density_g_cm3': material.density_g_cm3,
                        'melting_point_c': material.melting_point_c,
                        'glass_transition_c': material.glass_transition_c,
                        'tensile_strength_mpa': material.tensile_strength_mpa,
                        'flexural_strength_mpa': material.flexural_strength_mpa,
                        'compressive_strength_mpa': material.compressive_strength_mpa,
                        'impact_strength_j_m': material.impact_strength_j_m,
                        'hardness_shore': material.hardness_shore,
                        'recommended_nozzle_temp_min': material.recommended_nozzle_temp_min,
                        'recommended_nozzle_temp_max': material.recommended_nozzle_temp_max,
                        'recommended_bed_temp_min': material.recommended_bed_temp_min,
                        'recommended_bed_temp_max': material.recommended_bed_temp_max,
                        'shrinkage_percent': material.shrinkage_percent,
                        'warping_risk': material.warping_risk,
                        'bed_adhesion_rating': material.bed_adhesion_rating,
                        'layer_adhesion_rating': material.layer_adhesion_rating,
                        'uv_resistance_rating': material.uv_resistance_rating,
                        'chemical_resistance_rating': material.chemical_resistance_rating,
                        'moisture_absorption_percent': material.moisture_absorption_percent,
                        'cost_per_kg_usd': material.cost_per_kg_usd,
                        'compatible_printers': material.compatible_printers,
                        'compatible_nozzle_sizes': material.compatible_nozzle_sizes,
                        'strength_to_weight_ratio': material.strength_to_weight_ratio,
                        'cost_effectiveness_score': material.cost_effectiveness_score,
                        'environmental_impact_score': material.environmental_impact_score
                    })

            with open(self.database_file, 'w') as f:
                json.dump(custom_materials, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save custom materials: {e}")

    def get_material(self, material_id: str) -> Optional[MaterialProfile]:
        """Get material profile by ID."""
        return self.materials.get(material_id)

    def find_optimal_material(self, requirements: Dict[MaterialProperty, float],
                            constraints: Optional[Dict[str, Any]] = None) -> List[MaterialProfile]:
        """Find optimal materials based on requirements and constraints."""
        candidates = []

        for material in self.materials.values():
            # Apply constraints
            if constraints:
                if 'max_cost_per_kg' in constraints and material.cost_per_kg_usd:
                    if material.cost_per_kg_usd > constraints['max_cost_per_kg']:
                        continue

                if 'printer_type' in constraints:
                    if constraints['printer_type'] not in material.compatible_printers:
                        continue

                if 'uv_resistance_required' in constraints:
                    if material.uv_resistance_rating < 0.7:
                        continue

            # Calculate optimization score
            score = material.calculate_optimization_score(requirements)
            material._optimization_score = score
            candidates.append(material)

        # Sort by optimization score
        candidates.sort(key=lambda m: getattr(m, '_optimization_score', 0), reverse=True)

        return candidates

    def add_custom_material(self, material: MaterialProfile) -> bool:
        """Add custom material profile."""
        try:
            self.materials[material.material_id] = material
            self.save_custom_materials()
            self.logger.info(f"Added custom material: {material.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add custom material: {e}")
            return False

    def get_material_comparison(self, material_ids: List[str]) -> Dict[str, Any]:
        """Get detailed comparison of multiple materials."""
        materials = []
        for material_id in material_ids:
            material = self.get_material(material_id)
            if material:
                materials.append(material)

        if not materials:
            return {'error': 'No materials found for comparison'}

        comparison = {
            'materials': [
                {
                    'id': m.material_id,
                    'name': m.name,
                    'type': m.type.value,
                    'properties': {
                        'density': m.density_g_cm3,
                        'tensile_strength': m.tensile_strength_mpa,
                        'melting_point': m.melting_point_c,
                        'cost_per_kg': m.cost_per_kg_usd,
                        'warping_risk': m.warping_risk,
                        'bed_adhesion': m.bed_adhesion_rating,
                        'uv_resistance': m.uv_resistance_rating
                    }
                }
                for m in materials
            ],
            'recommendations': self._generate_comparison_recommendations(materials)
        }

        return comparison

    def _generate_comparison_recommendations(self, materials: List[MaterialProfile]) -> List[str]:
        """Generate recommendations based on material comparison."""
        recommendations = []

        if len(materials) < 2:
            return recommendations

        # Find best material for different use cases
        best_strength = max(materials, key=lambda m: m.tensile_strength_mpa or 0)
        best_cost_effective = max(materials, key=lambda m: (m.strength_to_weight_ratio or 0) / (m.cost_per_kg_usd or 1))
        best_environmental = max(materials, key=lambda m: m.environmental_impact_score or 0)
        best_printing = min(materials, key=lambda m: m.warping_risk)

        recommendations.append(f"For maximum strength: {best_strength.name} ({best_strength.tensile_strength_mpa} MPa)")
        recommendations.append(f"For cost effectiveness: {best_cost_effective.name}")
        recommendations.append(f"For environmental impact: {best_environmental.name}")
        recommendations.append(f"For easiest printing: {best_printing.name} (warping risk: {best_printing.warping_risk})")

        return recommendations


class MaterialOptimizer:
    """Advanced material optimization for 3D printing."""

    def __init__(self, material_database: MaterialDatabase):
        self.material_db = material_database
        self.logger = logging.getLogger(__name__)

    def optimize_for_strength(self, required_strength_mpa: float, max_cost_per_kg: float = 50) -> List[MaterialProfile]:
        """Find materials optimized for strength requirements."""
        requirements = {
            MaterialProperty.TENSILE_STRENGTH: 0.8,
            MaterialProperty.FLEXURAL_STRENGTH: 0.6,
            MaterialProperty.IMPACT_STRENGTH: 0.4
        }

        constraints = {'max_cost_per_kg': max_cost_per_kg}

        return self.material_db.find_optimal_material(requirements, constraints)

    def optimize_for_cost(self, max_cost_per_kg: float, required_properties: Dict[MaterialProperty, float]) -> List[MaterialProfile]:
        """Find cost-effective materials meeting requirements."""
        requirements = required_properties.copy()
        requirements[MaterialProperty.DENSITY] = 0.3  # Add cost consideration

        constraints = {'max_cost_per_kg': max_cost_per_kg}

        return self.material_db.find_optimal_material(requirements, constraints)

    def optimize_for_environment(self, required_properties: Dict[MaterialProperty, float]) -> List[MaterialProfile]:
        """Find environmentally friendly materials meeting requirements."""
        requirements = required_properties.copy()
        requirements[MaterialProperty.DENSITY] = 0.2  # Environmental consideration

        return self.material_db.find_optimal_material(requirements)

    def suggest_material_alternatives(self, current_material_id: str,
                                   requirements: Dict[MaterialProperty, float]) -> List[MaterialProfile]:
        """Suggest alternative materials based on current choice and requirements."""
        current_material = self.material_db.get_material(current_material_id)
        if not current_material:
            return []

        # Get optimal materials for requirements
        alternatives = self.material_db.find_optimal_material(requirements)

        # Filter out the current material and return top alternatives
        alternatives = [m for m in alternatives if m.material_id != current_material_id]

        return alternatives[:5]  # Return top 5 alternatives

    def calculate_material_cost_benefit(self, material_id: str, model_volume: float,
                                      production_volume: int = 1) -> Dict[str, float]:
        """Calculate cost-benefit analysis for a material."""
        material = self.material_db.get_material(material_id)
        if not material:
            return {'error': 'Material not found'}

        # Calculate material cost
        material_grams = material.estimate_material_usage(model_volume)
        material_cost = (material_grams / 1000) * (material.cost_per_kg_usd or 20)

        # Calculate printing cost (simplified)
        print_time_hours = material.estimate_print_time(model_volume, {}) / 3600
        energy_cost = print_time_hours * 0.5  # Assume $0.5 per hour for electricity
        labor_cost = print_time_hours * 25  # Assume $25 per hour for labor

        # Calculate total cost
        total_cost_per_unit = material_cost + energy_cost + labor_cost
        total_cost_production = total_cost_per_unit * production_volume

        # Calculate benefit based on material properties
        strength_benefit = (material.tensile_strength_mpa or 50) / 100
        durability_benefit = material.chemical_resistance_rating * 0.5 + material.uv_resistance_rating * 0.3
        quality_benefit = material.layer_adhesion_rating * 0.8 + (1 - material.warping_risk) * 0.2

        total_benefit_score = (strength_benefit + durability_benefit + quality_benefit) / 3

        return {
            'material_cost_per_unit': material_cost,
            'printing_cost_per_unit': energy_cost + labor_cost,
            'total_cost_per_unit': total_cost_per_unit,
            'total_cost_production': total_cost_production,
            'strength_benefit_score': strength_benefit,
            'durability_benefit_score': durability_benefit,
            'quality_benefit_score': quality_benefit,
            'overall_benefit_score': total_benefit_score,
            'cost_benefit_ratio': total_benefit_score / total_cost_per_unit if total_cost_per_unit > 0 else 0,
            'material_grams_per_unit': material_grams,
            'print_time_hours_per_unit': print_time_hours
        }


# Global material database instance
_material_database = MaterialDatabase()
_material_optimizer = MaterialOptimizer(_material_database)


def get_optimal_material_for_requirements(requirements: Dict[MaterialProperty, float],
                                        constraints: Optional[Dict[str, Any]] = None) -> List[MaterialProfile]:
    """Get optimal materials for given requirements."""
    return _material_database.find_optimal_material(requirements, constraints)


def suggest_material_alternatives(current_material_id: str,
                                requirements: Dict[MaterialProperty, float]) -> List[MaterialProfile]:
    """Suggest alternative materials."""
    return _material_optimizer.suggest_material_alternatives(current_material_id, requirements)


def calculate_material_cost_benefit(material_id: str, model_volume: float,
                                 production_volume: int = 1) -> Dict[str, float]:
    """Calculate cost-benefit analysis for a material."""
    return _material_optimizer.calculate_material_cost_benefit(material_id, model_volume, production_volume)


def get_material_comparison(material_ids: List[str]) -> Dict[str, Any]:
    """Get detailed comparison of multiple materials."""
    return _material_database.get_material_comparison(material_ids)
