"""Material selection optimization for 3D printing applications."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging
import time
import numpy as np
import trimesh


class MaterialCategory(Enum):
    """Material categories."""
    THERMOPLASTICS = "thermoplastics"
    THERMOSETS = "thermosets"
    COMPOSITES = "composites"
    METALS = "metals"
    CERAMICS = "ceramics"
    BIOMATERIALS = "biomaterials"


class MaterialProperty(Enum):
    """Material properties for optimization."""
    STRENGTH = "strength"
    FLEXIBILITY = "flexibility"
    HEAT_RESISTANCE = "heat_resistance"
    CHEMICAL_RESISTANCE = "chemical_resistance"
    COST = "cost"
    PRINTABILITY = "printability"
    POST_PROCESSING = "post_processing"
    ENVIRONMENTAL_IMPACT = "environmental_impact"


class OptimizationCriteria(Enum):
    """Optimization criteria."""
    STRENGTH_WEIGHT_RATIO = "strength_weight_ratio"
    COST_EFFECTIVENESS = "cost_effectiveness"
    PRINT_SPEED = "print_speed"
    SURFACE_FINISH = "surface_finish"
    DURABILITY = "durability"
    SUSTAINABILITY = "sustainability"
    BALANCED = "balanced"


@dataclass
class MaterialProperties:
    """Properties of a 3D printing material."""
    name: str
    category: MaterialCategory
    density: float  # g/cm³
    tensile_strength: float  # MPa
    flexural_modulus: float  # GPa
    elongation_at_break: float  # %
    heat_deflection_temp: float  # °C
    melting_temp: float  # °C
    cost_per_kg: float  # USD/kg
    print_temp_range: Tuple[float, float]  # °C min, max
    bed_temp_range: Tuple[float, float]  # °C min, max
    shrinkage_factor: float  # %
    layer_adhesion_rating: float  # 1-10
    surface_finish_rating: float  # 1-10
    chemical_resistance_rating: float  # 1-10
    environmental_impact_score: float  # 1-10 (lower is better)
    special_properties: List[str] = field(default_factory=list)


@dataclass
class MaterialOptimizationSettings:
    """Settings for material optimization."""
    primary_criteria: OptimizationCriteria = OptimizationCriteria.BALANCED
    secondary_criteria: List[OptimizationCriteria] = field(default_factory=list)
    required_properties: Dict[MaterialProperty, Any] = field(default_factory=dict)
    cost_weight: float = 0.2
    performance_weight: float = 0.4
    sustainability_weight: float = 0.2
    printability_weight: float = 0.2
    budget_limit: Optional[float] = None
    strength_requirement: Optional[float] = None
    flexibility_requirement: Optional[float] = None
    temperature_requirement: Optional[float] = None


@dataclass
class MaterialOptimizationResult:
    """Result of material optimization."""
    success: bool
    recommended_materials: List[Tuple[MaterialProperties, float]]  # Material and score
    best_material: Optional[MaterialProperties]
    alternative_materials: List[MaterialProperties]
    reasoning: List[str]
    trade_off_analysis: Dict[str, Any]
    processing_time: float


class MaterialDatabase:
    """Database of 3D printing materials."""

    def __init__(self):
        """Initialize the material database."""
        self.materials = self._build_material_database()

    def _build_material_database(self) -> List[MaterialProperties]:
        """Build the material properties database."""
        materials = []

        # PLA - Polylactic Acid
        pla = MaterialProperties(
            name="PLA",
            category=MaterialCategory.THERMOPLASTICS,
            density=1.24,
            tensile_strength=60.0,
            flexural_modulus=3.5,
            elongation_at_break=6.0,
            heat_deflection_temp=55.0,
            melting_temp=150.0,
            cost_per_kg=20.0,
            print_temp_range=(190.0, 220.0),
            bed_temp_range=(20.0, 60.0),
            shrinkage_factor=0.2,
            layer_adhesion_rating=8.0,
            surface_finish_rating=9.0,
            chemical_resistance_rating=3.0,
            environmental_impact_score=8.0,  # Biodegradable
            special_properties=["biodegradable", "easy_to_print", "food_safe"]
        )
        materials.append(pla)

        # ABS - Acrylonitrile Butadiene Styrene
        abs = MaterialProperties(
            name="ABS",
            category=MaterialCategory.THERMOPLASTICS,
            density=1.04,
            tensile_strength=40.0,
            flexural_modulus=2.3,
            elongation_at_break=20.0,
            heat_deflection_temp=85.0,
            melting_temp=220.0,
            cost_per_kg=25.0,
            print_temp_range=(220.0, 250.0),
            bed_temp_range=(80.0, 110.0),
            shrinkage_factor=0.8,
            layer_adhesion_rating=7.0,
            surface_finish_rating=6.0,
            chemical_resistance_rating=7.0,
            environmental_impact_score=4.0,
            special_properties=["impact_resistant", "heat_resistant", "post_processable"]
        )
        materials.append(abs)

        # PETG - Polyethylene Terephthalate Glycol
        petg = MaterialProperties(
            name="PETG",
            category=MaterialCategory.THERMOPLASTICS,
            density=1.27,
            tensile_strength=50.0,
            flexural_modulus=2.1,
            elongation_at_break=25.0,
            heat_deflection_temp=70.0,
            melting_temp=230.0,
            cost_per_kg=22.0,
            print_temp_range=(230.0, 250.0),
            bed_temp_range=(70.0, 80.0),
            shrinkage_factor=0.3,
            layer_adhesion_rating=9.0,
            surface_finish_rating=8.0,
            chemical_resistance_rating=8.0,
            environmental_impact_score=6.0,
            special_properties=["chemical_resistant", "transparent_options", "recyclable"]
        )
        materials.append(petg)

        # TPU - Thermoplastic Polyurethane
        tpu = MaterialProperties(
            name="TPU",
            category=MaterialCategory.THERMOPLASTICS,
            density=1.20,
            tensile_strength=35.0,
            flexural_modulus=0.05,
            elongation_at_break=600.0,
            heat_deflection_temp=60.0,
            melting_temp=210.0,
            cost_per_kg=35.0,
            print_temp_range=(210.0, 230.0),
            bed_temp_range=(30.0, 60.0),
            shrinkage_factor=0.5,
            layer_adhesion_rating=10.0,
            surface_finish_rating=7.0,
            chemical_resistance_rating=6.0,
            environmental_impact_score=5.0,
            special_properties=["flexible", "impact_absorbing", "abrasion_resistant"]
        )
        materials.append(tpu)

        # Nylon (PA6)
        nylon = MaterialProperties(
            name="Nylon (PA6)",
            category=MaterialCategory.THERMOPLASTICS,
            density=1.14,
            tensile_strength=75.0,
            flexural_modulus=2.8,
            elongation_at_break=50.0,
            heat_deflection_temp=90.0,
            melting_temp=220.0,
            cost_per_kg=45.0,
            print_temp_range=(240.0, 260.0),
            bed_temp_range=(80.0, 100.0),
            shrinkage_factor=1.5,
            layer_adhesion_rating=8.0,
            surface_finish_rating=5.0,
            chemical_resistance_rating=8.0,
            environmental_impact_score=3.0,
            special_properties=["high_strength", "wear_resistant", "chemical_resistant"]
        )
        materials.append(nylon)

        return materials

    def get_materials_by_category(self, category: MaterialCategory) -> List[MaterialProperties]:
        """Get materials by category."""
        return [m for m in self.materials if m.category == category]

    def search_materials(self, criteria: Dict[str, Any]) -> List[MaterialProperties]:
        """Search materials based on criteria."""
        results = []

        for material in self.materials:
            match = True

            for prop, value in criteria.items():
                if hasattr(material, prop):
                    material_value = getattr(material, prop)
                    if isinstance(value, (tuple, list)):
                        # Range check
                        if not (value[0] <= material_value <= value[1]):
                            match = False
                            break
                    elif isinstance(value, (int, float)):
                        # Threshold check
                        if material_value < value:
                            match = False
                            break

            if match:
                results.append(material)

        return results


class MaterialOptimizer:
    """Material selection optimization engine."""

    def __init__(self, settings: MaterialOptimizationSettings = None):
        """
        Initialize the material optimizer.

        Args:
            settings: Material optimization settings
        """
        self.settings = settings or MaterialOptimizationSettings()
        self.material_db = MaterialDatabase()
        self.logger = logging.getLogger(__name__)

    def optimize_material(self, mesh: trimesh.Trimesh,
                         application_requirements: Dict[str, Any] = None) -> MaterialOptimizationResult:
        """
        Optimize material selection for the given mesh and requirements.

        Args:
            mesh: Input mesh to optimize for
            application_requirements: Application-specific requirements

        Returns:
            MaterialOptimizationResult with recommended materials
        """
        start_time = time.time()
        reasoning = []

        try:
            # Step 1: Analyze mesh requirements
            mesh_requirements = self._analyze_mesh_requirements(mesh, application_requirements)
            reasoning.append(f"Mesh analysis: {mesh_requirements}")

            # Step 2: Filter materials based on requirements
            candidate_materials = self._filter_materials(mesh_requirements)
            reasoning.append(f"Found {len(candidate_materials)} candidate materials")

            if not candidate_materials:
                return MaterialOptimizationResult(
                    success=False,
                    recommended_materials=[],
                    best_material=None,
                    alternative_materials=[],
                    reasoning=["No suitable materials found for requirements"],
                    trade_off_analysis={},
                    processing_time=time.time() - start_time
                )

            # Step 3: Score materials based on criteria
            scored_materials = self._score_materials(candidate_materials, mesh_requirements)
            reasoning.append("Scored materials based on optimization criteria")

            # Step 4: Select best material and alternatives
            best_material = scored_materials[0][0] if scored_materials else None
            alternative_materials = [m for m, _ in scored_materials[1:3]] if len(scored_materials) > 1 else []

            # Step 5: Generate trade-off analysis
            trade_offs = self._analyze_trade_offs(scored_materials, mesh_requirements)

            processing_time = time.time() - start_time

            return MaterialOptimizationResult(
                success=True,
                recommended_materials=scored_materials,
                best_material=best_material,
                alternative_materials=alternative_materials,
                reasoning=reasoning,
                trade_off_analysis=trade_offs,
                processing_time=processing_time
            )

        except Exception as e:
            self.logger.error(f"Material optimization failed: {e}")
            processing_time = time.time() - start_time

            return MaterialOptimizationResult(
                success=False,
                recommended_materials=[],
                best_material=None,
                alternative_materials=[],
                reasoning=[f"Optimization failed: {str(e)}"],
                trade_off_analysis={},
                processing_time=processing_time
            )

    def _analyze_mesh_requirements(self, mesh: trimesh.Trimesh,
                                 application_requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze mesh to determine material requirements."""
        requirements = {
            'mechanical_strength': 'medium',
            'flexibility': 'low',
            'heat_resistance': 'low',
            'chemical_resistance': 'low',
            'surface_finish': 'medium',
            'cost_sensitivity': 'medium',
            'environmental_impact': 'medium'
        }

        try:
            # Analyze mesh characteristics
            volume = mesh.volume if mesh.volume > 0 else 1000.0
            surface_area = mesh.area
            height = mesh.extents[2]

            # Determine complexity
            complexity_score = len(mesh.faces) / max(volume, 1.0)
            if complexity_score > 10:
                requirements['surface_finish'] = 'high'
            elif complexity_score > 5:
                requirements['surface_finish'] = 'medium'
            else:
                requirements['surface_finish'] = 'low'

            # Determine size requirements
            if volume > 10000:  # Large parts
                requirements['mechanical_strength'] = 'high'
            elif volume > 1000:
                requirements['mechanical_strength'] = 'medium'

            # Check for thin features
            if self._has_thin_features(mesh):
                requirements['surface_finish'] = 'high'
                requirements['mechanical_strength'] = 'high'

            # Check for overhangs
            if self._has_significant_overhangs(mesh):
                requirements['printability'] = 'medium'  # May need supports

            # Apply application requirements
            if application_requirements:
                requirements.update(application_requirements)

        except Exception as e:
            self.logger.warning(f"Mesh requirements analysis failed: {e}")

        return requirements

    def _has_thin_features(self, mesh: trimesh.Trimesh) -> bool:
        """Check if mesh has thin features requiring careful material selection."""
        try:
            # Check for small faces
            areas = mesh.area_faces
            return np.min(areas) < 1.0 if len(areas) > 0 else False
        except:
            return False

    def _has_significant_overhangs(self, mesh: trimesh.Trimesh) -> bool:
        """Check if mesh has significant overhangs."""
        try:
            for normal in mesh.face_normals:
                angle = np.degrees(np.arccos(max(-1.0, min(1.0, normal[2]))))
                if angle > 45:
                    return True
            return False
        except:
            return False

    def _filter_materials(self, requirements: Dict[str, Any]) -> List[MaterialProperties]:
        """Filter materials based on requirements."""
        candidate_materials = []

        for material in self.material_db.materials:
            # Check temperature requirements
            if 'min_temp' in requirements:
                if material.heat_deflection_temp < requirements['min_temp']:
                    continue

            # Check strength requirements
            if 'min_strength' in requirements:
                if material.tensile_strength < requirements['min_strength']:
                    continue

            # Check flexibility requirements
            if 'flexibility' in requirements:
                flexibility_needed = requirements['flexibility']
                if flexibility_needed == 'high' and material.elongation_at_break < 100:
                    continue
                elif flexibility_needed == 'medium' and material.elongation_at_break < 20:
                    continue

            # Check cost constraints
            if 'max_cost_per_kg' in requirements:
                if material.cost_per_kg > requirements['max_cost_per_kg']:
                    continue

            candidate_materials.append(material)

        return candidate_materials

    def _score_materials(self, materials: List[MaterialProperties],
                        requirements: Dict[str, Any]) -> List[Tuple[MaterialProperties, float]]:
        """Score materials based on optimization criteria."""
        scored_materials = []

        for material in materials:
            score = self._calculate_material_score(material, requirements)
            scored_materials.append((material, score))

        # Sort by score (highest first)
        scored_materials.sort(key=lambda x: x[1], reverse=True)

        return scored_materials

    def _calculate_material_score(self, material: MaterialProperties,
                                requirements: Dict[str, Any]) -> float:
        """Calculate overall score for a material."""
        score = 0.0

        # Cost effectiveness score
        cost_score = max(0, 100 - material.cost_per_kg * 2)  # Lower cost = higher score
        score += cost_score * self.settings.cost_weight

        # Performance score
        strength_score = min(100, material.tensile_strength)
        flexibility_score = min(100, material.elongation_at_break / 5)
        heat_score = min(100, material.heat_deflection_temp / 2)

        performance_score = (strength_score + flexibility_score + heat_score) / 3
        score += performance_score * self.settings.performance_weight

        # Printability score
        printability_score = (material.layer_adhesion_rating + material.surface_finish_rating) * 5
        score += printability_score * self.settings.printability_weight

        # Sustainability score (inverted - lower impact = higher score)
        sustainability_score = (11 - material.environmental_impact_score) * 10
        score += sustainability_score * self.settings.sustainability_weight

        # Apply requirement modifiers
        if requirements.get('mechanical_strength') == 'high':
            score *= 1.2 if material.tensile_strength > 50 else 0.8

        if requirements.get('surface_finish') == 'high':
            score *= 1.3 if material.surface_finish_rating > 7 else 0.7

        return score

    def _analyze_trade_offs(self, scored_materials: List[Tuple[MaterialProperties, float]],
                          requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trade-offs between top materials."""
        if len(scored_materials) < 2:
            return {}

        best, alt = scored_materials[0], scored_materials[1]

        trade_offs = {
            'cost_difference': best[0].cost_per_kg - alt[0].cost_per_kg,
            'strength_difference': best[0].tensile_strength - alt[0].tensile_strength,
            'printability_difference': (best[0].layer_adhesion_rating - alt[0].layer_adhesion_rating) * 5,
            'environmental_impact_difference': alt[0].environmental_impact_score - best[0].environmental_impact_score
        }

        return trade_offs


def optimize_material_selection(mesh: trimesh.Trimesh,
                              primary_criteria: OptimizationCriteria = OptimizationCriteria.BALANCED,
                              application_requirements: Dict[str, Any] = None,
                              settings: MaterialOptimizationSettings = None) -> MaterialOptimizationResult:
    """
    Convenience function for material selection optimization.

    Args:
        mesh: Input mesh to optimize for
        primary_criteria: Primary optimization criteria
        application_requirements: Application-specific requirements
        settings: Optional material optimization settings

    Returns:
        MaterialOptimizationResult with recommended materials
    """
    if settings is None:
        settings = MaterialOptimizationSettings(primary_criteria=primary_criteria)
    else:
        settings.primary_criteria = primary_criteria

    optimizer = MaterialOptimizer(settings)
    return optimizer.optimize_material(mesh, application_requirements)
