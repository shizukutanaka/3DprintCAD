"""Intelligent material selection system."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import math

from .models import MaterialPreset, MaterialType, MaterialCategory, PrinterType
from .database import MaterialDatabase, get_material_database
from ..analysis.mesh_validator import MeshValidationResult
from ..logging import get_logger


class SelectionCriterion(Enum):
    """Material selection criteria."""
    STRENGTH = "strength"
    FLEXIBILITY = "flexibility"
    HEAT_RESISTANCE = "heat_resistance"
    CHEMICAL_RESISTANCE = "chemical_resistance"
    SURFACE_QUALITY = "surface_quality"
    EASE_OF_PRINTING = "ease_of_printing"
    COST = "cost"
    SPEED = "speed"
    FOOD_SAFETY = "food_safety"
    TRANSPARENCY = "transparency"


@dataclass
class SelectionRequirements:
    """Material selection requirements."""
    printer_type: PrinterType
    application: Optional[str] = None
    strength_required: Optional[str] = None  # low, medium, high
    heat_resistance_required: Optional[str] = None  # low, medium, high
    flexibility_required: Optional[str] = None  # rigid, semi_flexible, flexible
    surface_finish: Optional[str] = None  # standard, high, ultra_high
    chemical_exposure: Optional[str] = None
    food_contact: Optional[bool] = None
    transparency_required: Optional[bool] = None
    budget_per_kg: Optional[float] = None
    print_speed_priority: Optional[str] = None  # low, medium, high
    ease_of_printing: Optional[str] = None  # beginner, intermediate, advanced


@dataclass
class MaterialScore:
    """Material selection score with breakdown."""
    material: MaterialPreset
    total_score: float
    criteria_scores: Dict[str, float]
    compatibility_issues: List[str]
    recommendations: List[str]
    cost_estimate: Optional[float] = None


class MaterialSelector:
    """Intelligent material selection system."""

    def __init__(self, database: Optional[MaterialDatabase] = None):
        """Initialize material selector."""
        self.database = database or get_material_database()
        self.logger = get_logger(__name__)

    def select_materials(
        self,
        requirements: SelectionRequirements,
        validation_result: Optional[MeshValidationResult] = None,
        top_n: int = 5
    ) -> List[MaterialScore]:
        """Select best materials based on requirements and model analysis."""
        # Get candidate materials
        candidates = self._get_candidate_materials(requirements)

        if not candidates:
            self.logger.warning("No candidate materials found for requirements")
            return []

        # Score each material
        scored_materials = []
        for material in candidates:
            score = self._score_material(material, requirements, validation_result)
            if score.total_score > 0:  # Only include viable materials
                scored_materials.append(score)

        # Sort by total score (descending)
        scored_materials.sort(key=lambda x: x.total_score, reverse=True)

        # Add cost estimates
        self._add_cost_estimates(scored_materials, validation_result)

        return scored_materials[:top_n]

    def _get_candidate_materials(self, requirements: SelectionRequirements) -> List[MaterialPreset]:
        """Get candidate materials based on basic requirements."""
        materials = self.database.search_materials(
            compatible_with=requirements.printer_type
        )

        # Filter by hard requirements
        filtered = []
        for material in materials:
            # Check budget constraint
            if requirements.budget_per_kg and material.cost_per_kg:
                if material.cost_per_kg > requirements.budget_per_kg:
                    continue

            # Check food safety requirement
            if requirements.food_contact and not material.properties.food_safe:
                continue

            filtered.append(material)

        return filtered

    def _score_material(
        self,
        material: MaterialPreset,
        requirements: SelectionRequirements,
        validation_result: Optional[MeshValidationResult]
    ) -> MaterialScore:
        """Score a material based on requirements."""
        criteria_scores = {}
        compatibility_issues = []
        recommendations = []

        # Base compatibility score
        base_score = 50.0

        # Score individual criteria
        criteria_scores["strength"] = self._score_strength(material, requirements)
        criteria_scores["heat_resistance"] = self._score_heat_resistance(material, requirements)
        criteria_scores["flexibility"] = self._score_flexibility(material, requirements)
        criteria_scores["surface_quality"] = self._score_surface_quality(material, requirements)
        criteria_scores["ease_of_printing"] = self._score_ease_of_printing(material, requirements)
        criteria_scores["cost"] = self._score_cost(material, requirements)
        criteria_scores["speed"] = self._score_print_speed(material, requirements)

        # Application-specific scoring
        if requirements.application:
            criteria_scores["application"] = self._score_application_fit(material, requirements.application)

        # Model-specific scoring
        if validation_result:
            model_score, issues, recs = self._score_model_compatibility(material, validation_result)
            criteria_scores["model_compatibility"] = model_score
            compatibility_issues.extend(issues)
            recommendations.extend(recs)

        # Calculate weighted total score
        weights = self._get_criteria_weights(requirements)
        total_score = base_score

        for criterion, score in criteria_scores.items():
            weight = weights.get(criterion, 1.0)
            total_score += score * weight

        # Normalize score to 0-100 range
        total_score = max(0.0, min(100.0, total_score))

        return MaterialScore(
            material=material,
            total_score=total_score,
            criteria_scores=criteria_scores,
            compatibility_issues=compatibility_issues,
            recommendations=recommendations
        )

    def _score_strength(self, material: MaterialPreset, requirements: SelectionRequirements) -> float:
        """Score material strength based on requirements."""
        if not requirements.strength_required:
            return 0.0

        strength_map = {"low": 30.0, "medium": 50.0, "high": 70.0}
        required_strength = strength_map.get(requirements.strength_required, 50.0)

        if not material.properties.tensile_strength_mpa:
            return -10.0  # Penalty for unknown strength

        # Rough strength categories (MPa):
        # Low: < 40, Medium: 40-60, High: > 60
        actual_strength = material.properties.tensile_strength_mpa

        if actual_strength >= required_strength:
            return 10.0  # Bonus for meeting requirement
        else:
            # Penalty proportional to shortfall
            shortfall = (required_strength - actual_strength) / required_strength
            return -shortfall * 15.0

    def _score_heat_resistance(self, material: MaterialPreset, requirements: SelectionRequirements) -> float:
        """Score heat resistance based on requirements."""
        if not requirements.heat_resistance_required:
            return 0.0

        temp_map = {"low": 60.0, "medium": 80.0, "high": 120.0}
        required_temp = temp_map.get(requirements.heat_resistance_required, 80.0)

        glass_temp = material.properties.glass_transition_temp
        if not glass_temp:
            return -5.0

        if glass_temp >= required_temp:
            return 10.0
        else:
            shortfall = (required_temp - glass_temp) / required_temp
            return -shortfall * 20.0

    def _score_flexibility(self, material: MaterialPreset, requirements: SelectionRequirements) -> float:
        """Score flexibility based on requirements."""
        if not requirements.flexibility_required:
            return 0.0

        flexibility_req = requirements.flexibility_required

        if flexibility_req == "rigid":
            # Favor rigid materials
            if material.material_type in [MaterialType.THERMOPLASTIC]:
                if material.properties.elongation_at_break_percent and material.properties.elongation_at_break_percent < 10:
                    return 10.0
            return 0.0

        elif flexibility_req == "flexible":
            # Favor flexible materials
            if material.material_type == MaterialType.FLEXIBLE:
                return 15.0
            return -10.0

        elif flexibility_req == "semi_flexible":
            # Moderate flexibility
            if material.properties.elongation_at_break_percent:
                elongation = material.properties.elongation_at_break_percent
                if 50 <= elongation <= 200:
                    return 10.0

        return 0.0

    def _score_surface_quality(self, material: MaterialPreset, requirements: SelectionRequirements) -> float:
        """Score surface quality potential."""
        if not requirements.surface_finish:
            return 0.0

        finish_req = requirements.surface_finish

        # Material-specific surface quality scores
        surface_scores = {
            MaterialType.RESIN: {"standard": 5, "high": 15, "ultra_high": 20},
            MaterialType.THERMOPLASTIC: {"standard": 0, "high": 5, "ultra_high": 10},
        }

        material_scores = surface_scores.get(material.material_type, {"standard": 0, "high": 0, "ultra_high": 0})
        return material_scores.get(finish_req, 0)

    def _score_ease_of_printing(self, material: MaterialPreset, requirements: SelectionRequirements) -> float:
        """Score ease of printing based on user skill level."""
        if not requirements.ease_of_printing:
            return 0.0

        skill_level = requirements.ease_of_printing

        # Scoring based on printing difficulty
        ease_scores = {
            "beginner": {
                MaterialType.THERMOPLASTIC: 10 if material.properties.warping_tendency == "low" else -5,
                MaterialType.RESIN: -10,  # Resin is harder for beginners
            },
            "intermediate": {
                MaterialType.THERMOPLASTIC: 5,
                MaterialType.RESIN: 0,
            },
            "advanced": {
                MaterialType.THERMOPLASTIC: 0,
                MaterialType.RESIN: 5,
            }
        }

        level_scores = ease_scores.get(skill_level, {})
        base_score = level_scores.get(material.material_type, 0)

        # Additional penalties/bonuses
        if skill_level == "beginner":
            if material.properties.heated_bed_required:
                base_score -= 3
            if material.properties.enclosure_required:
                base_score -= 5
            if material.compatibility.ventilation_required:
                base_score -= 5

        return base_score

    def _score_cost(self, material: MaterialPreset, requirements: SelectionRequirements) -> float:
        """Score based on cost considerations."""
        if not material.cost_per_kg or not requirements.budget_per_kg:
            return 0.0

        cost_ratio = material.cost_per_kg / requirements.budget_per_kg

        if cost_ratio <= 0.5:
            return 10.0  # Very affordable
        elif cost_ratio <= 0.8:
            return 5.0   # Affordable
        elif cost_ratio <= 1.0:
            return 0.0   # At budget
        else:
            return -15.0  # Over budget (shouldn't happen due to filtering)

    def _score_print_speed(self, material: MaterialPreset, requirements: SelectionRequirements) -> float:
        """Score based on print speed potential."""
        if not requirements.print_speed_priority:
            return 0.0

        speed_priority = requirements.print_speed_priority

        # Fast printing materials
        fast_materials = {MaterialType.THERMOPLASTIC}
        slow_materials = {MaterialType.RESIN}

        if speed_priority == "high":
            if material.material_type in fast_materials:
                if material.properties.warping_tendency == "low":
                    return 10.0
                return 5.0
            elif material.material_type in slow_materials:
                return -10.0

        return 0.0

    def _score_application_fit(self, material: MaterialPreset, application: str) -> float:
        """Score material fit for specific application."""
        application_lower = application.lower()

        # Check if application matches material applications
        for mat_app in material.applications:
            if application_lower in mat_app.lower() or mat_app.lower() in application_lower:
                return 15.0  # Strong match

        # Partial matching
        app_keywords = application_lower.split()
        for keyword in app_keywords:
            for mat_app in material.applications:
                if keyword in mat_app.lower():
                    return 8.0  # Partial match

        return 0.0

    def _score_model_compatibility(
        self,
        material: MaterialPreset,
        validation_result: MeshValidationResult
    ) -> Tuple[float, List[str], List[str]]:
        """Score material compatibility with specific model."""
        score = 0.0
        issues = []
        recommendations = []

        if not validation_result.metrics:
            return score, issues, recommendations

        metrics = validation_result.metrics

        # Check for thin walls
        if hasattr(metrics, 'min_wall_thickness_mm') and metrics.min_wall_thickness_mm:
            min_wall = metrics.min_wall_thickness_mm

            # Minimum printable wall thickness varies by material/printer
            min_printable = 0.4  # Default
            if material.material_type == MaterialType.RESIN:
                min_printable = 0.2
            elif material.material_type == MaterialType.FLEXIBLE:
                min_printable = 0.8

            if min_wall < min_printable:
                score -= 10.0
                issues.append(f"Minimum wall thickness ({min_wall:.2f}mm) may be too thin for {material.name}")
                recommendations.append("Consider thicker nozzle or adjust model")

        # Check for overhangs
        if hasattr(metrics, 'overhang_face_count') and metrics.overhang_face_count:
            overhang_count = metrics.overhang_face_count

            if overhang_count > 0:
                if material.properties.support_required is False:
                    score -= 5.0
                    issues.append(f"Model has overhangs but {material.name} typically doesn't need supports")
                    recommendations.append("Verify support requirements")

        # Check model size compatibility
        if hasattr(metrics, 'bounding_box_mm') and metrics.bounding_box_mm:
            max_dimension = max(metrics.bounding_box_mm)

            # Large parts may have warping issues
            if max_dimension > 150 and material.properties.warping_tendency == "high":
                score -= 8.0
                issues.append(f"Large model ({max_dimension:.0f}mm) may warp with {material.name}")
                recommendations.append("Use heated bed and enclosure")

        return score, issues, recommendations

    def _get_criteria_weights(self, requirements: SelectionRequirements) -> Dict[str, float]:
        """Get weights for different criteria based on requirements."""
        weights = {
            "strength": 1.0,
            "heat_resistance": 1.0,
            "flexibility": 1.0,
            "surface_quality": 0.8,
            "ease_of_printing": 1.2,
            "cost": 1.5,
            "speed": 0.8,
            "application": 1.8,
            "model_compatibility": 1.5
        }

        # Adjust weights based on specific requirements
        if requirements.strength_required == "high":
            weights["strength"] = 2.0

        if requirements.surface_finish in ["high", "ultra_high"]:
            weights["surface_quality"] = 1.5

        if requirements.ease_of_printing == "beginner":
            weights["ease_of_printing"] = 2.0

        if requirements.budget_per_kg and requirements.budget_per_kg < 50:
            weights["cost"] = 2.0

        return weights

    def _add_cost_estimates(
        self,
        scored_materials: List[MaterialScore],
        validation_result: Optional[MeshValidationResult]
    ):
        """Add cost estimates to material scores."""
        if not validation_result or not validation_result.metrics:
            return

        metrics = validation_result.metrics
        if not hasattr(metrics, 'volume_cm3') or not metrics.volume_cm3:
            return

        volume_cm3 = metrics.volume_cm3

        for score in scored_materials:
            material = score.material
            if material.cost_per_kg and material.density_g_cm3:
                # Calculate material cost
                weight_kg = (volume_cm3 * material.density_g_cm3) / 1000

                # Add some waste factor (typically 10-20%)
                waste_factor = 1.15
                weight_with_waste = weight_kg * waste_factor

                material_cost = weight_with_waste * material.cost_per_kg
                score.cost_estimate = round(material_cost, 2)


def create_requirements_from_application(
    application: str,
    printer_type: PrinterType,
    skill_level: str = "intermediate"
) -> SelectionRequirements:
    """Create selection requirements based on common applications."""
    app_lower = application.lower()

    requirements = SelectionRequirements(printer_type=printer_type)

    # Application-specific defaults
    if "prototype" in app_lower:
        requirements.ease_of_printing = "beginner"
        requirements.print_speed_priority = "high"
        requirements.surface_finish = "standard"

    elif "tool" in app_lower or "functional" in app_lower:
        requirements.strength_required = "high"
        requirements.heat_resistance_required = "medium"

    elif "miniature" in app_lower or "model" in app_lower:
        requirements.surface_finish = "high"
        requirements.strength_required = "low"

    elif "automotive" in app_lower:
        requirements.strength_required = "high"
        requirements.heat_resistance_required = "high"
        requirements.chemical_resistance = "good"

    elif "food" in app_lower or "kitchen" in app_lower:
        requirements.food_contact = True
        requirements.chemical_resistance = "good"

    elif "outdoor" in app_lower:
        requirements.heat_resistance_required = "medium"
        requirements.chemical_resistance = "good"

    requirements.ease_of_printing = skill_level
    return requirements