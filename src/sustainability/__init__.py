"""Environmental impact assessment and sustainability features for 3D printing."""
from .carbon_calculator import CarbonFootprintCalculator, EmissionFactors, SustainabilityMetrics
from .lifecycle_assessment import LifecycleAssessment, EnvironmentalImpact, LCAReport
from .material_sustainability import MaterialSustainabilityAnalyzer, RecyclingAnalyzer
from .energy_optimizer import EnergyOptimizer, PowerConsumptionAnalyzer

__all__ = [
    # Carbon Footprint
    'CarbonFootprintCalculator',
    'EmissionFactors',
    'SustainabilityMetrics',

    # Lifecycle Assessment
    'LifecycleAssessment',
    'EnvironmentalImpact',
    'LCAReport',

    # Material Analysis
    'MaterialSustainabilityAnalyzer',
    'RecyclingAnalyzer',

    # Energy Optimization
    'EnergyOptimizer',
    'PowerConsumptionAnalyzer'
]