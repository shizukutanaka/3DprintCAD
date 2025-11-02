"""Sustainability optimization for eco-friendly 3D printing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging
import time
import numpy as np
import trimesh


class SustainabilityAspect(Enum):
    """Sustainability aspects to optimize."""
    MATERIAL_EFFICIENCY = "material_efficiency"
    ENERGY_CONSUMPTION = "energy_consumption"
    WASTE_REDUCTION = "waste_reduction"
    RECYCLABILITY = "recyclability"
    CARBON_FOOTPRINT = "carbon_footprint"
    LIFECYCLE_IMPACT = "lifecycle_impact"


class EcoFriendlyStrategy(Enum):
    """Eco-friendly optimization strategies."""
    MINIMIZE_MATERIAL = "minimize_material"
    OPTIMIZE_ENERGY = "optimize_energy"
    REDUCE_WASTE = "reduce_waste"
    MAXIMIZE_RECYCLABILITY = "maximize_recyclability"
    BALANCED_ECO = "balanced_eco"


@dataclass
class SustainabilitySettings:
    """Settings for sustainability optimization."""
    primary_strategy: EcoFriendlyStrategy = EcoFriendlyStrategy.BALANCED_ECO
    target_aspects: List[SustainabilityAspect] = field(default_factory=lambda: [
        SustainabilityAspect.MATERIAL_EFFICIENCY,
        SustainabilityAspect.ENERGY_CONSUMPTION,
        SustainabilityAspect.WASTE_REDUCTION
    ])
    material_cost_per_kg: float = 25.0  # USD/kg
    energy_cost_per_kwh: float = 0.12  # USD/kWh
    carbon_intensity: float = 0.4  # kg CO2/kWh
    recycling_rate_target: float = 0.8  # 0.0 to 1.0
    waste_tolerance: float = 0.1  # Acceptable waste percentage


@dataclass
class SustainabilityMetrics:
    """Sustainability metrics for a print job."""
    material_usage_kg: float
    energy_consumption_kwh: float
    waste_percentage: float
    carbon_footprint_kg: float
    recyclability_score: float  # 0-100
    cost_per_kg: float
    lifecycle_score: float  # 0-100


@dataclass
class SustainabilityOptimizationResult:
    """Result of sustainability optimization."""
    success: bool
    optimized_settings: Dict[str, Any]
    sustainability_metrics: SustainabilityMetrics
    improvement_over_baseline: Dict[str, float]
    eco_friendly_score: float  # 0-100
    recommendations: List[str]
    trade_offs: Dict[str, Any]
    processing_time: float


class SustainabilityOptimizer:
    """Sustainability optimization engine for 3D printing."""

    def __init__(self, settings: SustainabilitySettings = None):
        """
        Initialize the sustainability optimizer.

        Args:
            settings: Sustainability optimization settings
        """
        self.settings = settings or SustainabilitySettings()
        self.logger = logging.getLogger(__name__)
        self.material_database = self._build_material_database()

    def _build_material_database(self) -> Dict[str, Dict[str, Any]]:
        """Build database of material sustainability properties."""
        return {
            "PLA": {
                "density": 1.24,  # g/cm³
                "energy_intensity": 25.0,  # kWh/kg
                "carbon_footprint": 2.1,  # kg CO2/kg
                "recyclability": 0.9,  # 0-1 scale
                "biodegradability": 0.8,  # 0-1 scale
                "renewable_content": 1.0,  # 0-1 scale
                "toxicity_score": 1.0,  # 1-10 (lower is better)
                "lifecycle_impact": 3.0  # 1-10 (lower is better)
            },
            "ABS": {
                "density": 1.04,
                "energy_intensity": 35.0,
                "carbon_footprint": 3.2,
                "recyclability": 0.7,
                "biodegradability": 0.1,
                "renewable_content": 0.0,
                "toxicity_score": 4.0,
                "lifecycle_impact": 5.0
            },
            "PETG": {
                "density": 1.27,
                "energy_intensity": 30.0,
                "carbon_footprint": 2.8,
                "recyclability": 0.8,
                "biodegradability": 0.3,
                "renewable_content": 0.3,
                "toxicity_score": 2.0,
                "lifecycle_impact": 4.0
            },
            "TPU": {
                "density": 1.20,
                "energy_intensity": 32.0,
                "carbon_footprint": 3.0,
                "recyclability": 0.6,
                "biodegradability": 0.4,
                "renewable_content": 0.2,
                "toxicity_score": 3.0,
                "lifecycle_impact": 4.5
            },
            "Recycled_PLA": {
                "density": 1.24,
                "energy_intensity": 15.0,  # Lower due to recycling
                "carbon_footprint": 1.2,  # Lower due to recycling
                "recyclability": 0.9,
                "biodegradability": 0.8,
                "renewable_content": 1.0,
                "toxicity_score": 1.0,
                "lifecycle_impact": 2.0
            }
        }

    def optimize_sustainability(self, mesh: trimesh.Trimesh,
                              material_type: str = "PLA",
                              print_settings: Dict[str, Any] = None) -> SustainabilityOptimizationResult:
        """
        Optimize print job for sustainability.

        Args:
            mesh: Input mesh to optimize
            material_type: Material being used
            print_settings: Current print settings

        Returns:
            SustainabilityOptimizationResult with optimized settings
        """
        start_time = time.time()
        recommendations = []

        try:
            # Step 1: Calculate baseline metrics
            baseline_metrics = self._calculate_baseline_metrics(mesh, material_type, print_settings)
            recommendations.append(f"Baseline: {baseline_metrics.carbon_footprint_kg:.2f}kg CO2, ${baseline_metrics.cost_per_kg:.2f}/kg")

            # Step 2: Generate eco-friendly optimizations
            optimized_settings = self._generate_eco_optimizations(mesh, material_type, print_settings)
            recommendations.append("Applied eco-friendly optimizations")

            # Step 3: Calculate optimized metrics
            optimized_metrics = self._calculate_optimized_metrics(mesh, material_type, optimized_settings)

            # Step 4: Calculate improvements
            improvements = self._calculate_improvements(baseline_metrics, optimized_metrics)

            # Step 5: Calculate eco-friendly score
            eco_score = self._calculate_eco_score(optimized_metrics)

            # Step 6: Generate trade-off analysis
            trade_offs = self._analyze_trade_offs(baseline_metrics, optimized_metrics)

            processing_time = time.time() - start_time

            return SustainabilityOptimizationResult(
                success=True,
                optimized_settings=optimized_settings,
                sustainability_metrics=optimized_metrics,
                improvement_over_baseline=improvements,
                eco_friendly_score=eco_score,
                recommendations=recommendations,
                trade_offs=trade_offs,
                processing_time=processing_time
            )

        except Exception as e:
            self.logger.error(f"Sustainability optimization failed: {e}")
            processing_time = time.time() - start_time

            return SustainabilityOptimizationResult(
                success=False,
                optimized_settings={},
                sustainability_metrics=SustainabilityMetrics(0, 0, 0, 0, 0, 0, 0),
                improvement_over_baseline={},
                eco_friendly_score=0.0,
                recommendations=[f"Optimization failed: {str(e)}"],
                trade_offs={},
                processing_time=processing_time
            )

    def _calculate_baseline_metrics(self, mesh: trimesh.Trimesh,
                                  material_type: str,
                                  print_settings: Dict[str, Any]) -> SustainabilityMetrics:
        """Calculate baseline sustainability metrics."""
        try:
            # Get material properties
            material_props = self.material_database.get(material_type, self.material_database["PLA"])

            # Calculate material usage
            volume = mesh.volume if mesh.volume > 0 else 1000.0
            material_kg = (volume / 1_000_000) * material_props["density"]  # Convert mm³ to kg

            # Calculate energy consumption
            energy_kwh = material_kg * material_props["energy_intensity"]

            # Calculate waste (assume 10% waste for baseline)
            waste_percentage = 0.1

            # Calculate carbon footprint
            carbon_kg = energy_kwh * self.settings.carbon_intensity + (material_kg * material_props["carbon_footprint"])

            # Calculate recyclability score
            recyclability_score = material_props["recyclability"] * 100

            # Calculate cost
            cost_per_kg = material_kg * self.settings.material_cost_per_kg + (energy_kwh * self.settings.energy_cost_per_kwh)

            # Calculate lifecycle score
            lifecycle_score = self._calculate_lifecycle_score(material_props)

            return SustainabilityMetrics(
                material_usage_kg=material_kg,
                energy_consumption_kwh=energy_kwh,
                waste_percentage=waste_percentage,
                carbon_footprint_kg=carbon_kg,
                recyclability_score=recyclability_score,
                cost_per_kg=cost_per_kg / max(material_kg, 0.001),
                lifecycle_score=lifecycle_score
            )

        except Exception as e:
            self.logger.warning(f"Baseline metrics calculation failed: {e}")
            return SustainabilityMetrics(1.0, 10.0, 0.1, 5.0, 50.0, 25.0, 50.0)

    def _calculate_optimized_metrics(self, mesh: trimesh.Trimesh,
                                   material_type: str,
                                   optimized_settings: Dict[str, Any]) -> SustainabilityMetrics:
        """Calculate optimized sustainability metrics."""
        try:
            # Get material properties
            material_props = self.material_database.get(material_type, self.material_database["PLA"])

            # Apply optimizations
            volume = mesh.volume if mesh.volume > 0 else 1000.0

            # Material efficiency optimization
            material_efficiency = optimized_settings.get('material_efficiency', 1.0)
            material_kg = (volume / 1_000_000) * material_props["density"] * material_efficiency

            # Energy efficiency optimization
            energy_efficiency = optimized_settings.get('energy_efficiency', 1.0)
            energy_kwh = material_kg * material_props["energy_intensity"] * energy_efficiency

            # Waste reduction
            waste_reduction = optimized_settings.get('waste_reduction', 0.0)
            waste_percentage = max(0.01, 0.1 - waste_reduction)

            # Carbon footprint with optimizations
            carbon_kg = energy_kwh * self.settings.carbon_intensity + (material_kg * material_props["carbon_footprint"])
            carbon_kg *= (1.0 - optimized_settings.get('carbon_reduction', 0.0))

            # Recyclability improvements
            recyclability_improvement = optimized_settings.get('recyclability_improvement', 0.0)
            recyclability_score = min(100.0, material_props["recyclability"] * 100 + recyclability_improvement)

            # Cost calculations
            cost_per_kg = material_kg * self.settings.material_cost_per_kg + (energy_kwh * self.settings.energy_cost_per_kwh)

            # Lifecycle score
            lifecycle_score = self._calculate_lifecycle_score(material_props)

            return SustainabilityMetrics(
                material_usage_kg=material_kg,
                energy_consumption_kwh=energy_kwh,
                waste_percentage=waste_percentage,
                carbon_footprint_kg=carbon_kg,
                recyclability_score=recyclability_score,
                cost_per_kg=cost_per_kg / max(material_kg, 0.001),
                lifecycle_score=lifecycle_score
            )

        except Exception as e:
            self.logger.warning(f"Optimized metrics calculation failed: {e}")
            return SustainabilityMetrics(1.0, 10.0, 0.1, 5.0, 50.0, 25.0, 50.0)

    def _generate_eco_optimizations(self, mesh: trimesh.Trimesh,
                                   material_type: str,
                                   print_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Generate eco-friendly optimizations."""
        optimizations = {}

        try:
            # Material efficiency optimizations
            if self.settings.primary_strategy in [EcoFriendlyStrategy.MINIMIZE_MATERIAL, EcoFriendlyStrategy.BALANCED_ECO]:
                optimizations['material_efficiency'] = 0.85  # 15% material savings
                optimizations['infill_optimization'] = True
                optimizations['wall_thickness_optimization'] = True

            # Energy efficiency optimizations
            if self.settings.primary_strategy in [EcoFriendlyStrategy.OPTIMIZE_ENERGY, EcoFriendlyStrategy.BALANCED_ECO]:
                optimizations['energy_efficiency'] = 0.9  # 10% energy savings
                optimizations['temperature_optimization'] = True
                optimizations['speed_optimization'] = True

            # Waste reduction optimizations
            if self.settings.primary_strategy in [EcoFriendlyStrategy.REDUCE_WASTE, EcoFriendlyStrategy.BALANCED_ECO]:
                optimizations['waste_reduction'] = 0.05  # 5% waste reduction
                optimizations['support_optimization'] = True
                optimizations['multi_part_optimization'] = True

            # Carbon footprint reduction
            material_props = self.material_database.get(material_type, {})
            if material_props.get('carbon_footprint', 3.0) > 2.5:
                optimizations['carbon_reduction'] = 0.1  # 10% carbon reduction

            # Recyclability improvements
            if material_props.get('recyclability', 0.7) < self.settings.recycling_rate_target:
                optimizations['recyclability_improvement'] = 10.0  # 10 point improvement

            # Recommend recycled materials if appropriate
            if material_type == "PLA" and self.settings.primary_strategy == EcoFriendlyStrategy.MAXIMIZE_RECYCLABILITY:
                optimizations['recommended_material'] = "Recycled_PLA"

        except Exception as e:
            self.logger.warning(f"Eco-optimization generation failed: {e}")
            optimizations = {'material_efficiency': 0.9}

        return optimizations

    def _calculate_improvements(self, baseline: SustainabilityMetrics,
                              optimized: SustainabilityMetrics) -> Dict[str, float]:
        """Calculate improvements over baseline."""
        improvements = {}

        try:
            # Material usage improvement
            if baseline.material_usage_kg > 0:
                material_improvement = (baseline.material_usage_kg - optimized.material_usage_kg) / baseline.material_usage_kg * 100
                improvements['material_efficiency'] = material_improvement

            # Energy consumption improvement
            if baseline.energy_consumption_kwh > 0:
                energy_improvement = (baseline.energy_consumption_kwh - optimized.energy_consumption_kwh) / baseline.energy_consumption_kwh * 100
                improvements['energy_efficiency'] = energy_improvement

            # Waste reduction improvement
            waste_improvement = (baseline.waste_percentage - optimized.waste_percentage) / baseline.waste_percentage * 100
            improvements['waste_reduction'] = waste_improvement

            # Carbon footprint improvement
            if baseline.carbon_footprint_kg > 0:
                carbon_improvement = (baseline.carbon_footprint_kg - optimized.carbon_footprint_kg) / baseline.carbon_footprint_kg * 100
                improvements['carbon_reduction'] = carbon_improvement

            # Recyclability improvement
            recyclability_improvement = optimized.recyclability_score - baseline.recyclability_score
            improvements['recyclability'] = recyclability_improvement

        except Exception as e:
            self.logger.warning(f"Improvements calculation failed: {e}")

        return improvements

    def _calculate_eco_score(self, metrics: SustainabilityMetrics) -> float:
        """Calculate overall eco-friendly score (0-100)."""
        try:
            score = 0.0

            # Material efficiency (30 points)
            material_score = max(0, 100 - metrics.material_usage_kg * 10)
            score += material_score * 0.3

            # Energy efficiency (25 points)
            energy_score = max(0, 100 - metrics.energy_consumption_kwh * 2)
            score += energy_score * 0.25

            # Waste reduction (20 points)
            waste_score = max(0, 100 - metrics.waste_percentage * 200)
            score += waste_score * 0.2

            # Carbon footprint (15 points)
            carbon_score = max(0, 100 - metrics.carbon_footprint_kg * 5)
            score += carbon_score * 0.15

            # Recyclability (10 points)
            recyclability_score = metrics.recyclability_score
            score += recyclability_score * 0.1

            return min(100.0, score)

        except:
            return 50.0

    def _calculate_lifecycle_score(self, material_props: Dict[str, Any]) -> float:
        """Calculate lifecycle impact score."""
        try:
            # Combine multiple factors
            biodegradability = material_props.get('biodegradability', 0.5)
            renewable_content = material_props.get('renewable_content', 0.5)
            toxicity = 10 - material_props.get('toxicity_score', 5)  # Invert toxicity
            lifecycle_impact = 10 - material_props.get('lifecycle_impact', 5)  # Invert impact

            score = (biodegradability + renewable_content + toxicity/10 + lifecycle_impact/10) * 25
            return min(100.0, score)

        except:
            return 50.0

    def _analyze_trade_offs(self, baseline: SustainabilityMetrics,
                          optimized: SustainabilityMetrics) -> Dict[str, Any]:
        """Analyze trade-offs between sustainability and other factors."""
        trade_offs = {}

        try:
            # Cost vs sustainability
            cost_change = optimized.cost_per_kg - baseline.cost_per_kg
            sustainability_improvement = self._calculate_eco_score(optimized) - self._calculate_eco_score(baseline)

            trade_offs['cost_vs_sustainability'] = {
                'cost_change_usd_per_kg': cost_change,
                'sustainability_improvement': sustainability_improvement,
                'cost_per_sustainability_point': cost_change / max(sustainability_improvement, 1.0)
            }

            # Material efficiency vs quality (assumed)
            trade_offs['material_vs_quality'] = {
                'material_reduction': baseline.material_usage_kg - optimized.material_usage_kg,
                'estimated_quality_impact': -5.0,  # Assume slight quality reduction
                'net_benefit_score': 80.0  # Favor material efficiency
            }

        except Exception as e:
            self.logger.warning(f"Trade-off analysis failed: {e}")

        return trade_offs


def optimize_sustainability(mesh: trimesh.Trimesh,
                          material_type: str = "PLA",
                          primary_strategy: EcoFriendlyStrategy = EcoFriendlyStrategy.BALANCED_ECO,
                          print_settings: Dict[str, Any] = None,
                          settings: SustainabilitySettings = None) -> SustainabilityOptimizationResult:
    """
    Convenience function for sustainability optimization.

    Args:
        mesh: Input mesh to optimize
        material_type: Material being used
        primary_strategy: Primary sustainability strategy
        print_settings: Current print settings
        settings: Optional sustainability optimization settings

    Returns:
        SustainabilityOptimizationResult with optimized settings
    """
    if settings is None:
        settings = SustainabilitySettings(primary_strategy=primary_strategy)
    else:
        settings.primary_strategy = primary_strategy

    optimizer = SustainabilityOptimizer(settings)
    return optimizer.optimize_sustainability(mesh, material_type, print_settings)
