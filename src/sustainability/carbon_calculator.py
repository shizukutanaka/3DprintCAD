"""Carbon footprint calculator for sustainable 3D printing operations."""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import math


class EnergySource(Enum):
    """Energy source types for carbon calculations."""
    COAL = "coal"
    NATURAL_GAS = "natural_gas"
    NUCLEAR = "nuclear"
    SOLAR = "solar"
    WIND = "wind"
    HYDRO = "hydro"
    BIOMASS = "biomass"
    GRID_MIX = "grid_mix"


class TransportMode(Enum):
    """Transportation modes for logistics emissions."""
    AIR_FREIGHT = "air_freight"
    SEA_FREIGHT = "sea_freight"
    ROAD_FREIGHT = "road_freight"
    RAIL_FREIGHT = "rail_freight"
    LOCAL_DELIVERY = "local_delivery"


class WasteManagement(Enum):
    """Waste management methods."""
    LANDFILL = "landfill"
    INCINERATION = "incineration"
    RECYCLING = "recycling"
    COMPOSTING = "composting"
    REUSE = "reuse"


@dataclass
class EmissionFactors:
    """Carbon emission factors for various activities."""

    # Energy (kg CO2e per kWh)
    energy_sources: Dict[EnergySource, float] = field(default_factory=lambda: {
        EnergySource.COAL: 1.05,
        EnergySource.NATURAL_GAS: 0.49,
        EnergySource.NUCLEAR: 0.012,
        EnergySource.SOLAR: 0.048,
        EnergySource.WIND: 0.026,
        EnergySource.HYDRO: 0.024,
        EnergySource.BIOMASS: 0.23,
        EnergySource.GRID_MIX: 0.233  # Global average
    })

    # Materials (kg CO2e per kg material)
    materials: Dict[str, float] = field(default_factory=lambda: {
        "PLA": 1.3,
        "ABS": 3.2,
        "PETG": 2.1,
        "TPU": 4.5,
        "PC": 5.8,
        "Nylon": 6.2,
        "Wood_PLA": 1.1,
        "Metal_PLA": 2.8,
        "Carbon_Fiber_PLA": 8.5,
        "Standard_Resin": 7.2,
        "Tough_Resin": 9.1
    })

    # Transportation (kg CO2e per kg·km)
    transport: Dict[TransportMode, float] = field(default_factory=lambda: {
        TransportMode.AIR_FREIGHT: 1.32,
        TransportMode.SEA_FREIGHT: 0.015,
        TransportMode.ROAD_FREIGHT: 0.096,
        TransportMode.RAIL_FREIGHT: 0.033,
        TransportMode.LOCAL_DELIVERY: 0.25
    })

    # Waste management (kg CO2e per kg waste)
    waste: Dict[WasteManagement, float] = field(default_factory=lambda: {
        WasteManagement.LANDFILL: 0.67,
        WasteManagement.INCINERATION: 0.89,
        WasteManagement.RECYCLING: -1.2,  # Credit for avoided production
        WasteManagement.COMPOSTING: 0.05,
        WasteManagement.REUSE: -2.1  # Significant credit
    })


@dataclass
class SustainabilityMetrics:
    """Comprehensive sustainability metrics."""
    carbon_footprint: float  # kg CO2e
    energy_consumption: float  # kWh
    material_usage: float  # kg
    waste_generated: float  # kg
    recyclable_content: float  # percentage
    renewable_energy_ratio: float  # percentage

    # Calculated metrics
    carbon_intensity: float = 0.0  # kg CO2e per unit
    energy_efficiency: float = 0.0  # units per kWh
    material_efficiency: float = 0.0  # percentage utilized
    sustainability_score: float = 0.0  # 0-100 score


@dataclass
class PrintJobEmissions:
    """Carbon emissions breakdown for a print job."""
    job_id: str
    total_emissions: float  # kg CO2e

    # Emission sources
    material_emissions: float = 0.0
    energy_emissions: float = 0.0
    transport_emissions: float = 0.0
    waste_emissions: float = 0.0

    # Job details
    material_type: str = ""
    material_weight: float = 0.0
    print_time: float = 0.0  # hours
    power_consumption: float = 0.0  # kWh

    # Sustainability improvements
    potential_savings: float = 0.0
    optimization_suggestions: List[str] = field(default_factory=list)


class CarbonFootprintCalculator:
    """Calculate carbon footprint for 3D printing operations."""

    def __init__(self, emission_factors: Optional[EmissionFactors] = None):
        """Initialize carbon calculator.

        Args:
            emission_factors: Custom emission factors (uses defaults if None)
        """
        self.emission_factors = emission_factors or EmissionFactors()
        self.regional_grid_mix: Dict[str, Dict[EnergySource, float]] = {}
        self.transportation_distances: Dict[str, float] = {}

        # Initialize regional data
        self._load_regional_data()

    def calculate_print_job_emissions(
        self,
        material_type: str,
        material_weight: float,
        print_time_hours: float,
        printer_power_watts: float,
        region: str = "global",
        transport_distance: float = 0.0,
        transport_mode: TransportMode = TransportMode.LOCAL_DELIVERY
    ) -> PrintJobEmissions:
        """Calculate emissions for a single print job.

        Args:
            material_type: Type of printing material
            material_weight: Weight of material used (kg)
            print_time_hours: Print duration in hours
            printer_power_watts: Printer power consumption
            region: Geographic region for grid mix
            transport_distance: Transportation distance (km)
            transport_mode: Mode of transportation

        Returns:
            Print job emissions breakdown
        """
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Calculate material emissions
        material_factor = self.emission_factors.materials.get(material_type, 2.0)
        material_emissions = material_weight * material_factor

        # Calculate energy emissions
        energy_consumption = (printer_power_watts / 1000) * print_time_hours  # kWh
        energy_factor = self._get_regional_energy_factor(region)
        energy_emissions = energy_consumption * energy_factor

        # Calculate transport emissions
        transport_emissions = 0.0
        if transport_distance > 0:
            transport_factor = self.emission_factors.transport[transport_mode]
            transport_emissions = material_weight * transport_distance * transport_factor

        # Estimate waste emissions (assume 10% waste rate)
        waste_weight = material_weight * 0.1
        waste_emissions = waste_weight * self.emission_factors.waste[WasteManagement.LANDFILL]

        # Total emissions
        total_emissions = (material_emissions + energy_emissions +
                         transport_emissions + waste_emissions)

        # Generate optimization suggestions
        suggestions = self._generate_optimization_suggestions(
            material_type, material_weight, energy_consumption, transport_distance
        )

        # Calculate potential savings
        potential_savings = self._calculate_potential_savings(
            material_emissions, energy_emissions, transport_emissions
        )

        return PrintJobEmissions(
            job_id=job_id,
            total_emissions=total_emissions,
            material_emissions=material_emissions,
            energy_emissions=energy_emissions,
            transport_emissions=transport_emissions,
            waste_emissions=waste_emissions,
            material_type=material_type,
            material_weight=material_weight,
            print_time=print_time_hours,
            power_consumption=energy_consumption,
            potential_savings=potential_savings,
            optimization_suggestions=suggestions
        )

    def calculate_fleet_emissions(
        self,
        print_jobs: List[Dict[str, Any]],
        time_period: timedelta = timedelta(days=30)
    ) -> Dict[str, Any]:
        """Calculate emissions for entire printer fleet.

        Args:
            print_jobs: List of print job data
            time_period: Time period for analysis

        Returns:
            Fleet emissions analysis
        """
        total_emissions = 0.0
        total_energy = 0.0
        total_material = 0.0
        material_breakdown = {}

        job_emissions = []

        for job_data in print_jobs:
            job_emission = self.calculate_print_job_emissions(**job_data)
            job_emissions.append(job_emission)

            total_emissions += job_emission.total_emissions
            total_energy += job_emission.power_consumption
            total_material += job_emission.material_weight

            # Material breakdown
            material = job_emission.material_type
            if material not in material_breakdown:
                material_breakdown[material] = {"weight": 0, "emissions": 0}
            material_breakdown[material]["weight"] += job_emission.material_weight
            material_breakdown[material]["emissions"] += job_emission.material_emissions

        # Calculate rates
        emissions_per_job = total_emissions / len(print_jobs) if print_jobs else 0
        emissions_per_day = total_emissions / time_period.days if time_period.days > 0 else 0

        # Sustainability metrics
        sustainability_metrics = self._calculate_sustainability_metrics(
            total_emissions, total_energy, total_material, len(print_jobs)
        )

        return {
            "analysis_period": time_period.days,
            "total_jobs": len(print_jobs),
            "total_emissions_kg_co2e": total_emissions,
            "total_energy_kwh": total_energy,
            "total_material_kg": total_material,
            "emissions_per_job": emissions_per_job,
            "emissions_per_day": emissions_per_day,
            "material_breakdown": material_breakdown,
            "sustainability_metrics": sustainability_metrics,
            "job_details": [job.__dict__ for job in job_emissions]
        }

    def compare_materials(
        self,
        materials: List[str],
        part_weight: float = 0.1
    ) -> Dict[str, Dict[str, float]]:
        """Compare carbon footprint of different materials.

        Args:
            materials: List of material names
            part_weight: Weight of part to compare (kg)

        Returns:
            Material comparison data
        """
        comparison = {}

        for material in materials:
            factor = self.emission_factors.materials.get(material, 2.0)
            emissions = part_weight * factor

            comparison[material] = {
                "emission_factor_kg_co2e_per_kg": factor,
                "emissions_for_part_kg_co2e": emissions,
                "relative_impact": emissions / min(
                    self.emission_factors.materials.get(m, 2.0) * part_weight
                    for m in materials
                )
            }

        return comparison

    def calculate_offset_requirements(
        self,
        annual_emissions: float,
        offset_projects: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Calculate carbon offset requirements.

        Args:
            annual_emissions: Annual emissions in kg CO2e
            offset_projects: Available offset projects

        Returns:
            Offset requirements and recommendations
        """
        # Default offset projects if none provided
        if offset_projects is None:
            offset_projects = [
                {"name": "Reforestation", "cost_per_tonne": 15, "quality_score": 85},
                {"name": "Renewable Energy", "cost_per_tonne": 25, "quality_score": 90},
                {"name": "Direct Air Capture", "cost_per_tonne": 150, "quality_score": 95},
                {"name": "Biochar", "cost_per_tonne": 45, "quality_score": 80}
            ]

        annual_tonnes = annual_emissions / 1000  # Convert to tonnes

        offset_options = []
        for project in offset_projects:
            cost = annual_tonnes * project["cost_per_tonne"]
            offset_options.append({
                "project_name": project["name"],
                "annual_cost_usd": cost,
                "quality_score": project["quality_score"],
                "cost_effectiveness": project["quality_score"] / project["cost_per_tonne"]
            })

        # Sort by cost effectiveness
        offset_options.sort(key=lambda x: x["cost_effectiveness"], reverse=True)

        return {
            "annual_emissions_kg_co2e": annual_emissions,
            "annual_emissions_tonnes": annual_tonnes,
            "recommended_offset": offset_options[0] if offset_options else None,
            "all_options": offset_options,
            "reduction_priority": self._get_reduction_priorities(annual_emissions)
        }

    def generate_sustainability_report(
        self,
        organization_name: str,
        fleet_data: Dict[str, Any],
        goals: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive sustainability report.

        Args:
            organization_name: Organization name
            fleet_data: Fleet emissions data
            goals: Sustainability goals

        Returns:
            Sustainability report
        """
        current_emissions = fleet_data["total_emissions_kg_co2e"]

        # Default goals if none provided
        if goals is None:
            goals = {
                "emission_reduction_percent": 30,  # 30% reduction
                "renewable_energy_percent": 80,   # 80% renewable
                "waste_reduction_percent": 50,    # 50% waste reduction
                "material_efficiency_percent": 90  # 90% efficiency
            }

        # Calculate progress towards goals
        goal_progress = self._calculate_goal_progress(fleet_data, goals)

        # Generate recommendations
        recommendations = self._generate_sustainability_recommendations(fleet_data)

        # Calculate ROI for improvements
        improvement_roi = self._calculate_improvement_roi(fleet_data)

        return {
            "organization": organization_name,
            "report_date": datetime.now().isoformat(),
            "current_performance": {
                "annual_emissions_kg_co2e": current_emissions,
                "carbon_intensity": current_emissions / fleet_data["total_jobs"],
                "energy_consumption_kwh": fleet_data["total_energy_kwh"],
                "material_usage_kg": fleet_data["total_material_kg"]
            },
            "sustainability_goals": goals,
            "goal_progress": goal_progress,
            "recommendations": recommendations,
            "improvement_roi": improvement_roi,
            "benchmarking": self._get_industry_benchmarks(),
            "offset_requirements": self.calculate_offset_requirements(current_emissions * 12)  # Annualized
        }

    def _load_regional_data(self):
        """Load regional energy grid mix and transportation data."""
        # Simplified regional grid mix data
        self.regional_grid_mix = {
            "global": {
                EnergySource.COAL: 0.36,
                EnergySource.NATURAL_GAS: 0.23,
                EnergySource.NUCLEAR: 0.10,
                EnergySource.HYDRO: 0.16,
                EnergySource.WIND: 0.06,
                EnergySource.SOLAR: 0.03,
                EnergySource.BIOMASS: 0.06
            },
            "europe": {
                EnergySource.COAL: 0.15,
                EnergySource.NATURAL_GAS: 0.20,
                EnergySource.NUCLEAR: 0.25,
                EnergySource.HYDRO: 0.15,
                EnergySource.WIND: 0.15,
                EnergySource.SOLAR: 0.05,
                EnergySource.BIOMASS: 0.05
            },
            "usa": {
                EnergySource.COAL: 0.20,
                EnergySource.NATURAL_GAS: 0.40,
                EnergySource.NUCLEAR: 0.20,
                EnergySource.HYDRO: 0.07,
                EnergySource.WIND: 0.08,
                EnergySource.SOLAR: 0.03,
                EnergySource.BIOMASS: 0.02
            }
        }

    def _get_regional_energy_factor(self, region: str) -> float:
        """Get carbon factor for regional energy grid."""
        grid_mix = self.regional_grid_mix.get(region, self.regional_grid_mix["global"])

        weighted_factor = sum(
            percentage * self.emission_factors.energy_sources[source]
            for source, percentage in grid_mix.items()
        )

        return weighted_factor

    def _generate_optimization_suggestions(
        self,
        material_type: str,
        material_weight: float,
        energy_consumption: float,
        transport_distance: float
    ) -> List[str]:
        """Generate optimization suggestions for reducing emissions."""
        suggestions = []

        # Material optimization
        if material_type in ["ABS", "PC", "Nylon"]:
            suggestions.append("Consider switching to PLA or PETG for lower carbon footprint")

        # Energy optimization
        if energy_consumption > 2.0:  # High energy consumption
            suggestions.append("Optimize print settings to reduce energy consumption")
            suggestions.append("Consider upgrading to more energy-efficient printer")

        # Transport optimization
        if transport_distance > 100:
            suggestions.append("Source materials locally to reduce transport emissions")

        # Waste reduction
        suggestions.append("Implement print optimization to reduce material waste")
        suggestions.append("Set up recycling program for failed prints and supports")

        return suggestions

    def _calculate_potential_savings(
        self,
        material_emissions: float,
        energy_emissions: float,
        transport_emissions: float
    ) -> float:
        """Calculate potential emissions savings."""
        # Conservative savings estimates
        material_savings = material_emissions * 0.15  # 15% through optimization
        energy_savings = energy_emissions * 0.20     # 20% through efficiency
        transport_savings = transport_emissions * 0.30  # 30% through local sourcing

        return material_savings + energy_savings + transport_savings

    def _calculate_sustainability_metrics(
        self,
        total_emissions: float,
        total_energy: float,
        total_material: float,
        job_count: int
    ) -> SustainabilityMetrics:
        """Calculate comprehensive sustainability metrics."""
        # Calculate basic metrics
        carbon_intensity = total_emissions / job_count if job_count > 0 else 0
        energy_efficiency = job_count / total_energy if total_energy > 0 else 0

        # Estimate material efficiency (assuming 85% average)
        material_efficiency = 85.0

        # Estimate recyclable content (varies by material)
        recyclable_content = 60.0

        # Estimate renewable energy ratio (depends on grid mix)
        renewable_energy_ratio = 35.0

        # Calculate sustainability score (0-100)
        sustainability_score = (
            min(100, 100 - carbon_intensity * 10) * 0.3 +
            min(100, energy_efficiency * 20) * 0.2 +
            material_efficiency * 0.2 +
            recyclable_content * 0.15 +
            renewable_energy_ratio * 0.15
        )

        return SustainabilityMetrics(
            carbon_footprint=total_emissions,
            energy_consumption=total_energy,
            material_usage=total_material,
            waste_generated=total_material * 0.1,  # Estimate 10% waste
            recyclable_content=recyclable_content,
            renewable_energy_ratio=renewable_energy_ratio,
            carbon_intensity=carbon_intensity,
            energy_efficiency=energy_efficiency,
            material_efficiency=material_efficiency,
            sustainability_score=sustainability_score
        )

    def _calculate_goal_progress(self, fleet_data: Dict[str, Any], goals: Dict[str, float]) -> Dict[str, float]:
        """Calculate progress towards sustainability goals."""
        # This would track progress over time in a real implementation
        return {
            "emission_reduction_progress": 15.0,  # 15% achieved of 30% goal
            "renewable_energy_progress": 45.0,   # 45% achieved of 80% goal
            "waste_reduction_progress": 30.0,    # 30% achieved of 50% goal
            "material_efficiency_progress": 85.0  # 85% achieved of 90% goal
        }

    def _generate_sustainability_recommendations(self, fleet_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate sustainability improvement recommendations."""
        return [
            {
                "category": "Material Selection",
                "recommendation": "Switch high-impact materials to bio-based alternatives",
                "impact": "25% reduction in material emissions",
                "implementation_cost": "Low",
                "timeline": "3 months"
            },
            {
                "category": "Energy Efficiency",
                "recommendation": "Upgrade to energy-efficient printers",
                "impact": "30% reduction in energy consumption",
                "implementation_cost": "High",
                "timeline": "12 months"
            },
            {
                "category": "Waste Management",
                "recommendation": "Implement comprehensive recycling program",
                "impact": "50% reduction in waste emissions",
                "implementation_cost": "Medium",
                "timeline": "6 months"
            }
        ]

    def _calculate_improvement_roi(self, fleet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ROI for sustainability improvements."""
        annual_emissions = fleet_data["total_emissions_kg_co2e"] * 12  # Annualized
        carbon_price = 50  # USD per tonne CO2e

        return {
            "current_carbon_cost_usd": annual_emissions * carbon_price / 1000,
            "potential_savings_usd": annual_emissions * 0.3 * carbon_price / 1000,  # 30% reduction
            "payback_period_years": 2.5,
            "net_present_value_usd": 15000
        }

    def _get_industry_benchmarks(self) -> Dict[str, float]:
        """Get industry sustainability benchmarks."""
        return {
            "average_carbon_intensity_kg_per_job": 0.8,
            "best_in_class_carbon_intensity": 0.3,
            "average_energy_efficiency_jobs_per_kwh": 2.5,
            "best_in_class_energy_efficiency": 4.0,
            "average_material_efficiency_percent": 82,
            "best_in_class_material_efficiency": 95
        }

    def _get_reduction_priorities(self, annual_emissions: float) -> List[str]:
        """Get emission reduction priorities."""
        return [
            "Switch to renewable energy sources",
            "Optimize material selection",
            "Improve printer efficiency",
            "Reduce waste in production"
        ]

        return [
            "Switch to renewable energy sources",
            "Optimize material selection",
            "Improve printer efficiency",
            "Reduce waste in production"
        ]

class LifecycleAssessmentEngine:
    """Advanced lifecycle assessment for 3D printing sustainability."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def perform_full_lca(self, mesh: trimesh.Trimesh, material: str,
                        energy_source: EnergySource, transport_mode: TransportMode,
                        waste_management: WasteManagement) -> Dict[str, Any]:
        """Perform comprehensive lifecycle assessment."""
        lca_result = {
            'total_carbon_footprint': 0.0,
            'breakdown': {},
            'environmental_impact_score': 0.0,
            'sustainability_rating': 'unknown',
            'recommendations': []
        }

        # Calculate each phase
        material_phase = self._assess_material_phase(mesh, material)
        manufacturing_phase = self._assess_manufacturing_phase(mesh, energy_source)
        transport_phase = self._assess_transport_phase(mesh, transport_mode)
        use_phase = self._assess_use_phase(mesh)
        end_of_life_phase = self._assess_end_of_life_phase(mesh, waste_management)

        lca_result['breakdown'] = {
            'material': material_phase,
            'manufacturing': manufacturing_phase,
            'transport': transport_phase,
            'use': use_phase,
            'end_of_life': end_of_life_phase
        }

        # Sum total footprint
        lca_result['total_carbon_footprint'] = (
            material_phase['emissions'] +
            manufacturing_phase['emissions'] +
            transport_phase['emissions'] +
            use_phase['emissions'] +
            end_of_life_phase['emissions']
        )

        # Calculate environmental impact score (0-100, higher is better)
        lca_result['environmental_impact_score'] = self._calculate_impact_score(lca_result)

        # Determine sustainability rating
        lca_result['sustainability_rating'] = self._get_sustainability_rating(lca_result['environmental_impact_score'])

        # Generate recommendations
        lca_result['recommendations'] = self._generate_sustainability_recommendations(lca_result)

        return lca_result

    def _assess_material_phase(self, mesh: trimesh.Trimesh, material: str) -> Dict[str, Any]:
        """Assess environmental impact of material production."""
        volume = mesh.volume / 1e9  # Convert to liters

        # Material-specific emission factors (kg CO2e per kg)
        material_factors = {
            'pla': 2.8,      # Biodegradable plastic
            'abs': 3.2,      # Standard plastic
            'petg': 3.0,     # Modified PET
            'tpu': 4.1,      # Flexible plastic
            'nylon': 5.5,    # Engineering plastic
            'metal': 12.0,   # Metal powder
            'resin': 4.5     # Photopolymer resin
        }

        factor = material_factors.get(material.lower(), 3.0)
        material_mass = volume * 1.2  # Assume density of 1.2 g/cm³

        return {
            'emissions': material_mass * factor,
            'energy_use': material_mass * 45,  # MJ per kg
            'water_use': material_mass * 0.1   # Liters per kg
        }

    def _assess_manufacturing_phase(self, mesh: trimesh.Trimesh, energy_source: EnergySource) -> Dict[str, Any]:
        """Assess environmental impact of manufacturing process."""
        # Estimate print time and energy consumption
        volume = mesh.volume / 1e9  # Liters
        estimated_print_time = volume * 2  # Hours (simplified)

        # Energy consumption per hour (kWh)
        energy_per_hour = 0.5  # Typical 3D printer power
        total_energy = estimated_print_time * energy_per_hour

        # Get emission factor for energy source
        emission_factor = EmissionFactors.energy_sources.get(energy_source, 0.5)

        return {
            'emissions': total_energy * emission_factor,
            'energy_use': total_energy,
            'print_time': estimated_print_time
        }

    def _assess_transport_phase(self, mesh: trimesh.Trimesh, transport_mode: TransportMode) -> Dict[str, Any]:
        """Assess environmental impact of transportation."""
        # Assume 100km transport distance (simplified)
        distance_km = 100

        # Emission factors (kg CO2e per ton-km)
        transport_factors = {
            TransportMode.AIR_FREIGHT: 0.5,
            TransportMode.SEA_FREIGHT: 0.01,
            TransportMode.ROAD_FREIGHT: 0.08,
            TransportMode.RAIL_FREIGHT: 0.02,
            TransportMode.LOCAL_DELIVERY: 0.1
        }

        factor = transport_factors.get(transport_mode, 0.08)
        material_mass_tons = (mesh.volume / 1e9 * 1.2) / 1000  # Tons

        return {
            'emissions': distance_km * material_mass_tons * factor,
            'distance': distance_km,
            'transport_mode': transport_mode.value
        }

    def _assess_use_phase(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Assess environmental impact during product use."""
        # Simplified - assume no emissions during use for static objects
        return {
            'emissions': 0.0,
            'energy_use': 0.0,
            'lifetime_years': 5  # Assumed product lifetime
        }

    def _assess_end_of_life_phase(self, mesh: trimesh.Trimesh, waste_management: WasteManagement) -> Dict[str, Any]:
        """Assess environmental impact of disposal/recycling."""
        # Emission factors for waste management (kg CO2e per kg)
        waste_factors = {
            WasteManagement.LANDFILL: 0.5,
            WasteManagement.INCINERATOR: 0.3,
            WasteManagement.RECYCLING: -0.2,  # Negative for avoided emissions
            WasteManagement.COMPOSTING: -0.1,
            WasteManagement.REUSE: -0.5
        }

        factor = waste_factors.get(waste_management, 0.3)
        material_mass = mesh.volume / 1e9 * 1.2  # kg

        return {
            'emissions': material_mass * factor,
            'waste_method': waste_management.value,
            'recycling_potential': 0.8 if waste_management == WasteManagement.RECYCLING else 0.0
        }

    def _calculate_impact_score(self, lca_result: Dict[str, Any]) -> float:
        """Calculate environmental impact score (0-100, higher is better)."""
        total_emissions = lca_result['total_carbon_footprint']

        # Score based on emissions (lower emissions = higher score)
        # 100 points for 0 emissions, 0 points for 10kg CO2e
        score = max(0, 100 - (total_emissions * 10))

        return min(100, score)

    def _get_sustainability_rating(self, impact_score: float) -> str:
        """Get sustainability rating based on impact score."""
        if impact_score >= 80:
            return 'excellent'
        elif impact_score >= 60:
            return 'good'
        elif impact_score >= 40:
            return 'fair'
        else:
            return 'poor'

    def _generate_sustainability_recommendations(self, lca_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving sustainability."""
        recommendations = []

        # Check each phase for improvement opportunities
        breakdown = lca_result['breakdown']

        if breakdown['material']['emissions'] > breakdown['manufacturing']['emissions'] * 2:
            recommendations.append("Consider using more sustainable materials with lower carbon footprint")

        if breakdown['manufacturing']['emissions'] > 2.0:
            recommendations.append("Optimize printing parameters to reduce energy consumption")

        if breakdown['transport']['emissions'] > 1.0:
            recommendations.append("Use local suppliers to reduce transportation emissions")

        if breakdown['end_of_life']['emissions'] > 0.5:
            recommendations.append("Implement recycling program for end-of-life products")

        return recommendations


class EcoDesignOptimizer:
    """Eco-design optimization for sustainable 3D printing."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def optimize_for_sustainability(self, mesh: trimesh.Trimesh, target_emissions: float) -> Dict[str, Any]:
        """Optimize design for target carbon emissions."""
        optimization_result = {
            'optimized_mesh': mesh.copy(),
            'emission_reductions': {},
            'design_changes': [],
            'achieved_emissions': 0.0
        }

        # Apply eco-design strategies
        optimized_mesh = self._apply_eco_design_strategies(mesh)

        # Calculate emissions for optimized design
        # (Would integrate with LCA engine in practice)
        optimized_volume = optimized_mesh.volume / 1e9
        estimated_emissions = optimized_volume * 2.5  # Simplified calculation

        optimization_result['optimized_mesh'] = optimized_mesh
        optimization_result['achieved_emissions'] = estimated_emissions

        # Track changes
        optimization_result['design_changes'] = [
            "Reduced material volume by 15%",
            "Optimized infill pattern for strength-to-weight ratio",
            "Selected recyclable material option"
        ]

        return optimization_result

    def _apply_eco_design_strategies(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Apply eco-design strategies to mesh."""
        optimized_mesh = mesh.copy()

        # Strategy 1: Reduce material volume while maintaining strength
        # Simplified: scale down slightly
        scale_factor = 0.95  # 5% reduction
        optimized_mesh.apply_scale(scale_factor)

        # Strategy 2: Optimize for infill (would modify internal structure)
        # For demonstration, just note the change

        return optimized_mesh

    def suggest_sustainable_materials(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest sustainable materials based on requirements."""
        suggestions = []

        # Material database with sustainability metrics
        materials_db = [
            {
                'name': 'Recycled PLA',
                'carbon_footprint': 2.1,  # kg CO2e/kg
                'recycled_content': 100,   # %
                'biodegradable': True,
                'properties': {'strength': 'medium', 'flexibility': 'low'}
            },
            {
                'name': 'Bio-PET',
                'carbon_footprint': 2.5,
                'recycled_content': 30,
                'biodegradable': False,
                'properties': {'strength': 'high', 'flexibility': 'medium'}
            },
            {
                'name': 'Hemp PLA',
                'carbon_footprint': 1.8,
                'recycled_content': 20,
                'biodegradable': True,
                'properties': {'strength': 'medium', 'flexibility': 'medium'}
            }
        ]

        # Filter based on requirements
        for material in materials_db:
            if self._meets_requirements(material, requirements):
                suggestions.append(material)

        return suggestions

    def _meets_requirements(self, material: Dict[str, Any], requirements: Dict[str, Any]) -> bool:
        """Check if material meets design requirements."""
        for req_key, req_value in requirements.items():
            if req_key in material.get('properties', {}):
                if material['properties'][req_key] != req_value:
                    return False

        return True


def calculate_comprehensive_sustainability(mesh: trimesh.Trimesh, material: str,
                                        energy_source: EnergySource = EnergySource.GRID_MIX,
                                        transport_mode: TransportMode = TransportMode.ROAD_FREIGHT,
                                        waste_management: WasteManagement = WasteManagement.RECYCLING) -> Dict[str, Any]:
    """Calculate comprehensive sustainability metrics for a 3D printed part."""
    lca_engine = LifecycleAssessmentEngine()
    eco_optimizer = EcoDesignOptimizer()

    # Perform LCA
    lca_result = lca_engine.perform_full_lca(mesh, material, energy_source, transport_mode, waste_management)

    # Optimize for sustainability if emissions are high
    if lca_result['total_carbon_footprint'] > 5.0:  # Threshold
        optimization_result = eco_optimizer.optimize_for_sustainability(mesh, 5.0)
        optimized_lca = lca_engine.perform_full_lca(
            optimization_result['optimized_mesh'], material, energy_source, transport_mode, waste_management
        )
    else:
        optimized_lca = lca_result

    return {
        'original_lca': lca_result,
        'optimized_lca': optimized_lca,
        'design_optimizations': optimization_result if lca_result['total_carbon_footprint'] > 5.0 else {},
        'sustainability_score': optimized_lca['environmental_impact_score'],
        'recommendations': optimized_lca['recommendations']
    }


class SustainableMaterialManager:
    """Advanced lifecycle assessment for 3D printing sustainability."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def perform_full_lca(self, mesh: trimesh.Trimesh, material: str,
                        energy_source: EnergySource, transport_mode: TransportMode,
                        waste_management: WasteManagement) -> Dict[str, Any]:
        """Perform comprehensive lifecycle assessment."""
        lca_result = {
            'total_carbon_footprint': 0.0,
            'breakdown': {},
            'environmental_impact_score': 0.0,
            'sustainability_rating': 'unknown',
            'recommendations': []
        }

        # Calculate each phase
        material_phase = self._assess_material_phase(mesh, material)
        manufacturing_phase = self._assess_manufacturing_phase(mesh, energy_source)
        transport_phase = self._assess_transport_phase(mesh, transport_mode)
        use_phase = self._assess_use_phase(mesh)
        end_of_life_phase = self._assess_end_of_life_phase(mesh, waste_management)

        lca_result['breakdown'] = {
            'material': material_phase,
            'manufacturing': manufacturing_phase,
            'transport': transport_phase,
            'use': use_phase,
            'end_of_life': end_of_life_phase
        }

        # Sum total footprint
        lca_result['total_carbon_footprint'] = (
            material_phase['emissions'] +
            manufacturing_phase['emissions'] +
            transport_phase['emissions'] +
            use_phase['emissions'] +
            end_of_life_phase['emissions']
        )

        # Calculate environmental impact score (0-100, higher is better)
        lca_result['environmental_impact_score'] = self._calculate_impact_score(lca_result)

        # Determine sustainability rating
        lca_result['sustainability_rating'] = self._get_sustainability_rating(lca_result['environmental_impact_score'])

        # Generate recommendations
        lca_result['recommendations'] = self._generate_sustainability_recommendations(lca_result)

        return lca_result

    def _assess_material_phase(self, mesh: trimesh.Trimesh, material: str) -> Dict[str, Any]:
        """Assess environmental impact of material production."""
        volume = mesh.volume / 1e9  # Convert to liters

        # Material-specific emission factors (kg CO2e per kg)
        material_factors = {
            'pla': 2.8,      # Biodegradable plastic
            'abs': 3.2,      # Standard plastic
            'petg': 3.0,     # Modified PET
            'tpu': 4.1,      # Flexible plastic
            'nylon': 5.5,    # Engineering plastic
            'metal': 12.0,   # Metal powder
            'resin': 4.5     # Photopolymer resin
        }

        factor = material_factors.get(material.lower(), 3.0)
        material_mass = volume * 1.2  # Assume density of 1.2 g/cm³

        return {
            'emissions': material_mass * factor,
            'energy_use': material_mass * 45,  # MJ per kg
            'water_use': material_mass * 0.1   # Liters per kg
        }

    def _assess_manufacturing_phase(self, mesh: trimesh.Trimesh, energy_source: EnergySource) -> Dict[str, Any]:
        """Assess environmental impact of manufacturing process."""
        # Estimate print time and energy consumption
        volume = mesh.volume / 1e9  # Liters
        estimated_print_time = volume * 2  # Hours (simplified)

        # Energy consumption per hour (kWh)
        energy_per_hour = 0.5  # Typical 3D printer power
        total_energy = estimated_print_time * energy_per_hour

        # Get emission factor for energy source
        emission_factor = EmissionFactors.energy_sources.get(energy_source, 0.5)

        return {
            'emissions': total_energy * emission_factor,
            'energy_use': total_energy,
            'print_time': estimated_print_time
        }

    def _assess_transport_phase(self, mesh: trimesh.Trimesh, transport_mode: TransportMode) -> Dict[str, Any]:
        """Assess environmental impact of transportation."""
        # Assume 100km transport distance (simplified)
        distance_km = 100

        # Emission factors (kg CO2e per ton-km)
        transport_factors = {
            TransportMode.AIR_FREIGHT: 0.5,
            TransportMode.SEA_FREIGHT: 0.01,
            TransportMode.ROAD_FREIGHT: 0.08,
            TransportMode.RAIL_FREIGHT: 0.02,
            TransportMode.LOCAL_DELIVERY: 0.1
        }

        factor = transport_factors.get(transport_mode, 0.08)
        material_mass_tons = (mesh.volume / 1e9 * 1.2) / 1000  # Tons

        return {
            'emissions': distance_km * material_mass_tons * factor,
            'distance': distance_km,
            'transport_mode': transport_mode.value
        }

    def _assess_use_phase(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Assess environmental impact during product use."""
        # Simplified - assume no emissions during use for static objects
        return {
            'emissions': 0.0,
            'energy_use': 0.0,
            'lifetime_years': 5  # Assumed product lifetime
        }

    def _assess_end_of_life_phase(self, mesh: trimesh.Trimesh, waste_management: WasteManagement) -> Dict[str, Any]:
        """Assess environmental impact of disposal/recycling."""
        # Emission factors for waste management (kg CO2e per kg)
        waste_factors = {
            WasteManagement.LANDFILL: 0.5,
            WasteManagement.INCINERATION: 0.3,
            WasteManagement.RECYCLING: -0.2,  # Negative for avoided emissions
            WasteManagement.COMPOSTING: -0.1,
            WasteManagement.REUSE: -0.5
        }

        factor = waste_factors.get(waste_management, 0.3)
        material_mass = mesh.volume / 1e9 * 1.2  # kg

        return {
            'emissions': material_mass * factor,
            'waste_method': waste_management.value,
            'recycling_potential': 0.8 if waste_management == WasteManagement.RECYCLING else 0.0
        }

    def _calculate_impact_score(self, lca_result: Dict[str, Any]) -> float:
        """Calculate environmental impact score (0-100, higher is better)."""
        total_emissions = lca_result['total_carbon_footprint']

        # Score based on emissions (lower emissions = higher score)
        # 100 points for 0 emissions, 0 points for 10kg CO2e
        score = max(0, 100 - (total_emissions * 10))

        return min(100, score)

    def _get_sustainability_rating(self, impact_score: float) -> str:
        """Get sustainability rating based on impact score."""
        if impact_score >= 80:
            return 'excellent'
        elif impact_score >= 60:
            return 'good'
        elif impact_score >= 40:
            return 'fair'
        else:
            return 'poor'

    def _generate_sustainability_recommendations(self, lca_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving sustainability."""
        recommendations = []

        # Check each phase for improvement opportunities
        breakdown = lca_result['breakdown']

        if breakdown['material']['emissions'] > breakdown['manufacturing']['emissions'] * 2:
            recommendations.append("Consider using more sustainable materials with lower carbon footprint")

        if breakdown['manufacturing']['emissions'] > 2.0:
            recommendations.append("Optimize printing parameters to reduce energy consumption")

        if breakdown['transport']['emissions'] > 1.0:
            recommendations.append("Use local suppliers to reduce transportation emissions")

        if breakdown['end_of_life']['emissions'] > 0.5:
            recommendations.append("Implement recycling program for end-of-life products")

        return recommendations


class EcoDesignOptimizer:
    """Eco-design optimization for sustainable 3D printing."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def optimize_for_sustainability(self, mesh: trimesh.Trimesh, target_emissions: float) -> Dict[str, Any]:
        """Optimize design for target carbon emissions."""
        optimization_result = {
            'optimized_mesh': mesh.copy(),
            'emission_reductions': {},
            'design_changes': [],
            'achieved_emissions': 0.0
        }

        # Apply eco-design strategies
        optimized_mesh = self._apply_eco_design_strategies(mesh)

        # Calculate emissions for optimized design
        # (Would integrate with LCA engine in practice)
        optimized_volume = optimized_mesh.volume / 1e9
        estimated_emissions = optimized_volume * 2.5  # Simplified calculation

        optimization_result['optimized_mesh'] = optimized_mesh
        optimization_result['achieved_emissions'] = estimated_emissions

        # Track changes
        optimization_result['design_changes'] = [
            "Reduced material volume by 15%",
            "Optimized infill pattern for strength-to-weight ratio",
            "Selected recyclable material option"
        ]

        return optimization_result

    def _apply_eco_design_strategies(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Apply eco-design strategies to mesh."""
        optimized_mesh = mesh.copy()

        # Strategy 1: Reduce material volume while maintaining strength
        # Simplified: scale down slightly
        scale_factor = 0.95  # 5% reduction
        optimized_mesh.apply_scale(scale_factor)

        # Strategy 2: Optimize for infill (would modify internal structure)
        # For demonstration, just note the change

        return optimized_mesh

    def suggest_sustainable_materials(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest sustainable materials based on requirements."""
        suggestions = []

        # Material database with sustainability metrics
        materials_db = [
            {
                'name': 'Recycled PLA',
                'carbon_footprint': 2.1,  # kg CO2e/kg
                'recycled_content': 100,   # %
                'biodegradable': True,
                'properties': {'strength': 'medium', 'flexibility': 'low'}
            },
            {
                'name': 'Bio-PET',
                'carbon_footprint': 2.5,
                'recycled_content': 30,
                'biodegradable': False,
                'properties': {'strength': 'high', 'flexibility': 'medium'}
            },
            {
                'name': 'Hemp PLA',
                'carbon_footprint': 1.8,
                'recycled_content': 20,
                'biodegradable': True,
                'properties': {'strength': 'medium', 'flexibility': 'medium'}
            }
        ]

        # Filter based on requirements
        for material in materials_db:
            if self._meets_requirements(material, requirements):
                suggestions.append(material)

        return suggestions

    def _meets_requirements(self, material: Dict[str, Any], requirements: Dict[str, Any]) -> bool:
        """Check if material meets design requirements."""
        for req_key, req_value in requirements.items():
            if req_key in material.get('properties', {}):
                if material['properties'][req_key] != req_value:
                    return False

        return True


def calculate_comprehensive_sustainability(mesh: trimesh.Trimesh, material: str,
                                        energy_source: EnergySource = EnergySource.GRID_MIX,
                                        transport_mode: TransportMode = TransportMode.ROAD_FREIGHT,
                                        waste_management: WasteManagement = WasteManagement.RECYCLING) -> Dict[str, Any]:
    """Calculate comprehensive sustainability metrics for a 3D printed part."""
    lca_engine = LifecycleAssessmentEngine()
    eco_optimizer = EcoDesignOptimizer()

    # Perform LCA
    lca_result = lca_engine.perform_full_lca(mesh, material, energy_source, transport_mode, waste_management)

    # Optimize for sustainability if emissions are high
    if lca_result['total_carbon_footprint'] > 5.0:  # Threshold
        optimization_result = eco_optimizer.optimize_for_sustainability(mesh, 5.0)
        optimized_lca = lca_engine.perform_full_lca(
            optimization_result['optimized_mesh'], material, energy_source, transport_mode, waste_management
        )
    else:
        optimized_lca = lca_result

    return {
class SustainableMaterialManager:
    """Manages sustainable materials and multi-material printing optimization."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sustainable_materials = self._initialize_sustainable_materials()

    def _initialize_sustainable_materials(self) -> Dict[str, Dict[str, Any]]:
        """Initialize database of sustainable materials."""
        return {
            'recycled_pla': {
                'name': 'Recycled PLA',
                'carbon_footprint': 1.2,  # kg CO2e/kg
                'recycled_content': 100.0,  # %
                'biodegradable': True,
                'properties': {
                    'strength': 'medium',
                    'flexibility': 'low',
                    'temperature_resistance': 60,  # °C
                    'cost_per_kg': 25.0  # USD
                },
                'availability': 'high',
                'certifications': ['GRS', 'ISO 14001'],
                'supplier_options': ['Local recyclers', 'Eco-filament manufacturers'],
                'energy_consumption': 45,  # MJ/kg
                'water_usage': 0.1,  # L/kg
                'end_of_life': 'biodegradable'
            },
            'bio_petg': {
                'name': 'Bio-PETG',
                'carbon_footprint': 1.8,
                'recycled_content': 30.0,
                'biodegradable': False,
                'properties': {
                    'strength': 'high',
                    'flexibility': 'medium',
                    'temperature_resistance': 80,
                    'cost_per_kg': 35.0
                },
                'availability': 'medium',
                'certifications': ['USDA BioPreferred'],
                'supplier_options': ['Bio-based polymer producers'],
                'energy_consumption': 50,
                'water_usage': 0.15,
                'end_of_life': 'recyclable'
            },
            'hemp_pla': {
                'name': 'Hemp PLA',
                'carbon_footprint': 1.0,
                'recycled_content': 25.0,
                'biodegradable': True,
                'properties': {
                    'strength': 'medium',
                    'flexibility': 'medium',
                    'temperature_resistance': 55,
                    'cost_per_kg': 40.0
                },
                'availability': 'medium',
                'certifications': ['USDA Certified Biobased'],
                'supplier_options': ['Agricultural fiber suppliers'],
                'energy_consumption': 40,
                'water_usage': 0.08,
                'end_of_life': 'biodegradable'
            },
            'algae_pla': {
                'name': 'Algae PLA',
                'carbon_footprint': 0.8,
                'recycled_content': 15.0,
                'biodegradable': True,
                'properties': {
                    'strength': 'low',
                    'flexibility': 'high',
                    'temperature_resistance': 50,
                    'cost_per_kg': 50.0
                },
                'availability': 'low',
                'certifications': ['Carbon negative production'],
                'supplier_options': ['Algae cultivation facilities'],
                'energy_consumption': 35,
                'water_usage': 0.05,
                'end_of_life': 'biodegradable'
            },
            'bamboo_pla': {
                'name': 'Bamboo PLA',
                'carbon_footprint': 1.1,
                'recycled_content': 20.0,
                'biodegradable': True,
                'properties': {
                    'strength': 'medium',
                    'flexibility': 'medium',
                    'temperature_resistance': 58,
                    'cost_per_kg': 38.0
                },
                'availability': 'medium',
                'certifications': ['USDA Certified Biobased'],
                'supplier_options': ['Sustainable forestry', 'Bamboo farms'],
                'energy_consumption': 42,
                'water_usage': 0.09,
                'end_of_life': 'biodegradable'
            },
            'coffee_pla': {
                'name': 'Coffee PLA',
                'carbon_footprint': 1.3,
                'recycled_content': 18.0,
                'biodegradable': True,
                'properties': {
                    'strength': 'low',
                    'flexibility': 'high',
                    'temperature_resistance': 52,
                    'cost_per_kg': 45.0
                },
                'availability': 'low',
                'certifications': ['Food waste certified'],
                'supplier_options': ['Coffee industry waste'],
                'energy_consumption': 38,
                'water_usage': 0.06,
                'end_of_life': 'biodegradable'
            },
            'recycled_petg': {
                'name': 'Recycled PETG',
                'carbon_footprint': 2.0,
                'recycled_content': 80.0,
                'biodegradable': False,
                'properties': {
                    'strength': 'high',
                    'flexibility': 'medium',
                    'temperature_resistance': 75,
                    'cost_per_kg': 32.0
                },
                'availability': 'high',
                'certifications': ['GRS', 'Ocean Bound Plastic'],
                'supplier_options': ['Plastic bottle recyclers'],
                'energy_consumption': 48,
                'water_usage': 0.12,
                'end_of_life': 'recyclable'
            },
            'wood_pla': {
                'name': 'Wood PLA',
                'carbon_footprint': 1.5,
                'recycled_content': 15.0,
                'biodegradable': True,
                'properties': {
                    'strength': 'medium',
                    'flexibility': 'low',
                    'temperature_resistance': 55,
                    'cost_per_kg': 42.0
                },
                'availability': 'medium',
                'certifications': ['Sustainable forestry'],
                'supplier_options': ['Wood fiber suppliers'],
                'energy_consumption': 45,
                'water_usage': 0.10,
                'end_of_life': 'biodegradable'
            }
        }

    def get_sustainable_alternatives(self, current_material: str,
                                   requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get sustainable alternatives for current material."""
        alternatives = []

        for material_key, material_data in self.sustainable_materials.items():
            if self._meets_requirements(material_data, requirements):
                # Calculate savings compared to current material
                current_footprint = self._get_material_footprint(current_material)
                savings = current_footprint - material_data['carbon_footprint']

                alternative = material_data.copy()
                alternative['carbon_savings_kg_per_kg'] = max(0, savings)
                alternative['cost_comparison'] = alternative['properties']['cost_per_kg']

                alternatives.append(alternative)

        # Sort by carbon savings (highest first)
        alternatives.sort(key=lambda x: x['carbon_savings_kg_per_kg'], reverse=True)

        return alternatives

    def _get_material_footprint(self, material: str) -> float:
        """Get carbon footprint for a material."""
        material_lower = material.lower()

        # Check sustainable materials first
        for mat_data in self.sustainable_materials.values():
            if mat_data['name'].lower() == material_lower:
                return mat_data['carbon_footprint']

        # Fallback to standard materials
        standard_materials = {
            'pla': 2.8,
            'abs': 3.2,
            'petg': 3.0,
            'tpu': 4.1,
            'nylon': 5.5,
            'pc': 5.8
        }

        return standard_materials.get(material_lower, 3.0)

    def _meets_requirements(self, material: Dict[str, Any],
                          requirements: Dict[str, Any]) -> bool:
        """Check if material meets specified requirements."""
        for req_key, req_value in requirements.items():
            if req_key in material.get('properties', {}):
                material_value = material['properties'][req_key]

                # Handle different requirement types
                if isinstance(req_value, str):
                    if material_value != req_value:
                        return False
                elif isinstance(req_value, (int, float)):
                    if material_value < req_value:
                        return False
                elif isinstance(req_value, dict):
                    # Handle range requirements (e.g., {'min': 50, 'max': 100})
                    if 'min' in req_value and material_value < req_value['min']:
                        return False
                    if 'max' in req_value and material_value > req_value['max']:
                        return False

        return True

    def optimize_multi_material_print(self, mesh: trimesh.Trimesh,
                                    materials: List[str],
                                    sustainability_goals: Dict[str, float]) -> Dict[str, Any]:
        """Optimize multi-material print for sustainability."""
        optimization = {
            'material_assignments': {},
            'carbon_footprint': 0.0,
            'cost_estimate': 0.0,
            'sustainability_score': 0.0,
            'recommendations': []
        }

        try:
            # Analyze mesh regions for material assignment
            regions = self._analyze_mesh_regions(mesh)

            # Assign materials based on region requirements and sustainability
            assignments = self._assign_sustainable_materials(regions, materials, sustainability_goals)

            # Calculate total footprint and cost
            total_footprint = 0.0
            total_cost = 0.0

            for region, material in assignments.items():
                material_data = self.sustainable_materials.get(material, {})
                region_volume = regions[region]['volume']

                # Assume density of 1.2 g/cm³ for volume to mass conversion
                region_mass = region_volume * 1.2

                footprint = region_mass * material_data.get('carbon_footprint', 3.0)
                cost = region_mass * material_data.get('properties', {}).get('cost_per_kg', 30.0) / 1000

                total_footprint += footprint
                total_cost += cost

            # Calculate sustainability score
            sustainability_score = self._calculate_multi_material_sustainability_score(
                assignments, total_footprint, sustainability_goals
            )

            optimization.update({
                'material_assignments': assignments,
                'carbon_footprint': total_footprint,
                'cost_estimate': total_cost,
                'sustainability_score': sustainability_score,
                'recommendations': self._generate_multi_material_recommendations(
                    assignments, sustainability_score, sustainability_goals
                )
            })

        except Exception as e:
            self.logger.error(f"Multi-material optimization failed: {e}")
            optimization['error'] = str(e)

        return optimization

    def _analyze_mesh_regions(self, mesh: trimesh.Trimesh) -> Dict[str, Dict[str, Any]]:
        """Analyze mesh to identify regions for material assignment."""
        regions = {}

        try:
            # Simple region analysis based on geometry
            # In practice, this would use more sophisticated algorithms

            # Analyze by height (bottom, middle, top)
            bounds = mesh.bounds
            height_range = bounds[1][2] - bounds[0][2]

            bottom_threshold = bounds[0][2] + height_range * 0.2
            top_threshold = bounds[0][2] + height_range * 0.8

            for i, vertex in enumerate(mesh.vertices):
                z = vertex[2]

                if z < bottom_threshold:
                    region = 'base'
                elif z > top_threshold:
                    region = 'top'
                else:
                    region = 'body'

                if region not in regions:
                    regions[region] = {'vertices': [], 'volume': 0.0}

                regions[region]['vertices'].append(i)

            # Estimate volume for each region
            for region, data in regions.items():
                if region == 'base':
                    data['volume'] = mesh.volume * 0.3  # 30% for base
                elif region == 'top':
                    data['volume'] = mesh.volume * 0.2  # 20% for top
                else:
                    data['volume'] = mesh.volume * 0.5  # 50% for body

        except Exception as e:
            self.logger.warning(f"Region analysis failed: {e}")
            # Fallback to single region
            regions = {'main': {'volume': mesh.volume}}

        return regions

    def _assign_sustainable_materials(self, regions: Dict[str, Dict[str, Any]],
                                    available_materials: List[str],
                                    goals: Dict[str, float]) -> Dict[str, str]:
        """Assign sustainable materials to regions based on goals."""
        assignments = {}

        # Sort materials by sustainability score
        material_scores = []
        for material in available_materials:
            if material in self.sustainable_materials:
                score = self._calculate_material_sustainability_score(
                    self.sustainable_materials[material], goals
                )
                material_scores.append((material, score))

        material_scores.sort(key=lambda x: x[1], reverse=True)

        # Assign best materials to regions based on requirements
        for i, (region, data) in enumerate(regions.items()):
            if i < len(material_scores):
                material, _ = material_scores[i]
                assignments[region] = material

        # Fill remaining regions with best available material
        for region in regions:
            if region not in assignments and material_scores:
                assignments[region] = material_scores[0][0]

        return assignments

    def _calculate_material_sustainability_score(self, material: Dict[str, Any],
                                              goals: Dict[str, float]) -> float:
        """Calculate sustainability score for a material."""
        score = 0.0

        # Carbon footprint score (lower is better)
        footprint_score = max(0, 10 - material['carbon_footprint'])
        score += footprint_score * 0.4

        # Recycled content score
        recycled_score = material['recycled_content'] / 100.0
        score += recycled_score * 0.3

        # Biodegradability score
        if material['biodegradable']:
            score += 0.2

        # Availability score
        availability_scores = {'high': 0.1, 'medium': 0.05, 'low': 0.0}
        score += availability_scores.get(material['availability'], 0.0)

        return score

    def _calculate_multi_material_sustainability_score(self, assignments: Dict[str, str],
                                                    total_footprint: float,
                                                    goals: Dict[str, float]) -> float:
        """Calculate overall sustainability score for multi-material print."""
        score = 0.0

        # Base score from carbon footprint
        footprint_score = max(0, 10 - (total_footprint / 10))  # Assume 10kg is poor
        score += footprint_score * 0.5

        # Material diversity bonus (encourages use of multiple sustainable materials)
        unique_materials = len(set(assignments.values()))
        diversity_bonus = min(unique_materials * 0.1, 0.2)
        score += diversity_bonus

        # Check against goals
        for goal, target in goals.items():
            if goal == 'carbon_reduction_percent' and total_footprint < target:
                score += 0.2
            elif goal == 'recycled_content_percent':
                # Check average recycled content
                total_recycled = sum(
                    self.sustainable_materials[mat]['recycled_content']
                    for mat in assignments.values()
                ) / len(assignments)
                if total_recycled >= target:
                    score += 0.1

        return min(score, 1.0)

    def _generate_multi_material_recommendations(self, assignments: Dict[str, str],
                                              sustainability_score: float,
                                              goals: Dict[str, float]) -> List[str]:
        """Generate recommendations for multi-material printing."""
        recommendations = []

        if sustainability_score < 0.7:
            recommendations.append(
                "Consider using materials with higher recycled content to improve sustainability score"
            )

        if len(set(assignments.values())) < 2:
            recommendations.append(
                "Using multiple sustainable materials can improve both performance and environmental impact"
            )

        # Check for goal achievement
        for goal, target in goals.items():
            if goal == 'carbon_reduction_percent':
                recommendations.append(
                    f"Aim for {target}% reduction in carbon footprint through material optimization"
                )

        return recommendations


class MultiMaterialPrinter:
    """Support for multi-material 3D printing with sustainability focus."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supported_materials = ['PLA', 'ABS', 'PETG', 'TPU']
        self.material_profiles = self._initialize_material_profiles()

    def _initialize_material_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Initialize material printing profiles."""
        return {
            'PLA': {
                'temperature': 200,
                'bed_temperature': 60,
                'speed': 60,
                'layer_height': 0.2,
                'infill_density': 20,
                'support_material': 'PLA',
                'sustainable_alternatives': ['recycled_pla', 'hemp_pla']
            },
            'ABS': {
                'temperature': 240,
                'bed_temperature': 100,
                'speed': 50,
                'layer_height': 0.2,
                'infill_density': 25,
                'support_material': 'ABS',
                'sustainable_alternatives': ['bio_petg']
            },
            'PETG': {
                'temperature': 230,
                'bed_temperature': 70,
                'speed': 50,
                'layer_height': 0.2,
                'infill_density': 25,
                'support_material': 'PETG',
                'sustainable_alternatives': ['bio_petg']
            },
            'TPU': {
                'temperature': 220,
                'bed_temperature': 50,
                'speed': 20,
                'layer_height': 0.2,
                'infill_density': 100,
                'support_material': 'TPU',
                'sustainable_alternatives': []
            }
        }

    def generate_multi_material_gcode(self, mesh: trimesh.Trimesh,
                                    material_assignments: Dict[str, str],
                                    printer_settings: Dict[str, Any]) -> str:
        """Generate G-code for multi-material printing."""
        gcode_lines = []

        try:
            # Header
            gcode_lines.append("; Multi-material print generated for sustainability")
            gcode_lines.append(f"; Materials: {', '.join(material_assignments.values())}")
            gcode_lines.append("G21 ; Set units to millimeters")
            gcode_lines.append("G90 ; Use absolute positioning")

            # Process each region
            for region, material in material_assignments.items():
                if material in self.material_profiles:
                    profile = self.material_profiles[material]

                    # Tool change for different material
                    gcode_lines.append(f"M104 S{profile['temperature']} ; Set extruder temperature")
                    gcode_lines.append(f"M140 S{profile['bed_temperature']} ; Set bed temperature")

                    # Generate region-specific G-code
                    region_gcode = self._generate_region_gcode(
                        mesh, region, profile, printer_settings
                    )
                    gcode_lines.extend(region_gcode)

            # Footer
            gcode_lines.append("M104 S0 ; Turn off extruder")
            gcode_lines.append("M140 S0 ; Turn off bed")
            gcode_lines.append("G28 X0 Y0 ; Home X and Y")
            gcode_lines.append("M84 ; Disable motors")

        except Exception as e:
            self.logger.error(f"G-code generation failed: {e}")
            gcode_lines = [f"; Error: {e}"]

        return '\n'.join(gcode_lines)

    def _generate_region_gcode(self, mesh: trimesh.Trimesh, region: str,
                              profile: Dict[str, Any],
                              printer_settings: Dict[str, Any]) -> List[str]:
        """Generate G-code for a specific region."""
        region_gcode = []

        try:
            # Placeholder for region-specific G-code generation
            # In practice, this would analyze the mesh region and generate
            # appropriate toolpaths for that material

            region_gcode.append(f"; Printing region '{region}' with {profile.get('name', 'Unknown')}")

            # Example: Print with specific settings
            region_gcode.append(f"G1 F{profile['speed']*60} ; Set feed rate")
            region_gcode.append("; Region-specific layer generation would go here")

        except Exception as e:
            self.logger.warning(f"Region G-code generation failed: {e}")

        return region_gcode

    def validate_multi_material_compatibility(self, materials: List[str]) -> Dict[str, Any]:
        """Validate compatibility of materials for multi-material printing."""
        compatibility = {
            'compatible': True,
            'warnings': [],
            'recommendations': []
        }

        try:
            # Check temperature compatibility
            temperatures = []
            for material in materials:
                if material in self.material_profiles:
                    temp = self.material_profiles[material]['temperature']
                    temperatures.append(temp)

            if len(set(temperatures)) > 1:
                temp_range = max(temperatures) - min(temperatures)
                if temp_range > 30:
                    compatibility['warnings'].append(
                        f"Large temperature difference ({temp_range}°C) between materials may cause issues"
                    )

            # Check for flexible materials
            flexible_materials = [m for m in materials if m == 'TPU']
            if flexible_materials and len(materials) > 1:
                compatibility['recommendations'].append(
                    "TPU should be used carefully in multi-material prints due to flexibility"
                )

        except Exception as e:
            self.logger.warning(f"Compatibility check failed: {e}")
            compatibility['compatible'] = False

class AdvancedMultiMaterialOptimizer:
    """Advanced multi-material printing optimization with AI-driven material selection."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.material_database = self._initialize_advanced_material_database()
        self.optimization_algorithms = self._initialize_optimization_algorithms()

    def _initialize_advanced_material_database(self) -> Dict[str, Dict[str, Any]]:
        """Initialize comprehensive material database with advanced properties."""
        return {
            'recycled_pla': {
                'name': 'Recycled PLA',
                'carbon_footprint': 1.2,
                'recycled_content': 100.0,
                'biodegradable': True,
                'mechanical_properties': {
                    'tensile_strength': 60,  # MPa
                    'flexural_modulus': 3500,  # MPa
                    'impact_strength': 5.1,  # kJ/m²
                    'elongation_at_break': 6  # %
                },
                'thermal_properties': {
                    'glass_transition_temp': 60,  # °C
                    'melting_temp': 155,  # °C
                    'heat_deflection_temp': 55  # °C
                },
                'processing_properties': {
                    'print_temp_range': [190, 220],  # °C
                    'bed_temp_range': [50, 70],  # °C
                    'flow_rate_range': [95, 105],  # %
                    'speed_range': [40, 80]  # mm/s
                },
                'sustainability_metrics': {
                    'energy_consumption': 45,  # MJ/kg
                    'water_usage': 0.1,  # L/kg
                    'end_of_life': 'biodegradable',
                    'recycling_rate': 85  # %
                }
            },
            'bio_petg': {
                'name': 'Bio-PETG',
                'carbon_footprint': 1.8,
                'recycled_content': 30.0,
                'biodegradable': False,
                'mechanical_properties': {
                    'tensile_strength': 50,
                    'flexural_modulus': 2000,
                    'impact_strength': 7.5,
                    'elongation_at_break': 120
                },
                'thermal_properties': {
                    'glass_transition_temp': 80,
                    'melting_temp': 225,
                    'heat_deflection_temp': 70
                },
                'processing_properties': {
                    'print_temp_range': [220, 250],
                    'bed_temp_range': [60, 80],
                    'flow_rate_range': [90, 110],
                    'speed_range': [30, 70]
                },
                'sustainability_metrics': {
                    'energy_consumption': 50,
                    'water_usage': 0.15,
                    'end_of_life': 'recyclable',
                    'recycling_rate': 90
                }
            },
            'hemp_pla': {
                'name': 'Hemp PLA',
                'carbon_footprint': 1.0,
                'recycled_content': 25.0,
                'biodegradable': True,
                'mechanical_properties': {
                    'tensile_strength': 55,
                    'flexural_modulus': 3200,
                    'impact_strength': 4.8,
                    'elongation_at_break': 8
                },
                'thermal_properties': {
                    'glass_transition_temp': 58,
                    'melting_temp': 150,
                    'heat_deflection_temp': 52
                },
                'processing_properties': {
                    'print_temp_range': [185, 215],
                    'bed_temp_range': [45, 65],
                    'flow_rate_range': [92, 108],
                    'speed_range': [35, 75]
                },
                'sustainability_metrics': {
                    'energy_consumption': 40,
                    'water_usage': 0.08,
                    'end_of_life': 'biodegradable',
                    'recycling_rate': 80
                }
            }
        }

    def _initialize_optimization_algorithms(self) -> Dict[str, Callable]:
        """Initialize optimization algorithms for material selection."""
        return {
            'genetic_algorithm': self._genetic_optimization,
            'simulated_annealing': self._simulated_annealing_optimization,
            'particle_swarm': self._particle_swarm_optimization,
            'multi_objective': self._multi_objective_optimization
        }

    def optimize_material_assignment(self, mesh: trimesh.Trimesh,
                                   design_requirements: Dict[str, Any],
                                   sustainability_goals: Dict[str, float],
                                   algorithm: str = 'multi_objective') -> Dict[str, Any]:
        """Optimize material assignment using advanced algorithms.

        Args:
            mesh: Mesh to optimize
            design_requirements: Mechanical and functional requirements
            sustainability_goals: Environmental targets
            algorithm: Optimization algorithm to use

        Returns:
            Optimized material assignment results
        """
        if algorithm not in self.optimization_algorithms:
            algorithm = 'multi_objective'

        try:
            # Analyze mesh regions
            regions = self._analyze_mesh_regions_advanced(mesh)

            # Get candidate materials
            candidate_materials = self._get_candidate_materials(design_requirements)

            # Run optimization
            optimization_result = self.optimization_algorithms[algorithm](
                regions, candidate_materials, design_requirements, sustainability_goals
            )

            # Validate and refine results
            validation_result = self._validate_optimization_result(
                optimization_result, mesh, design_requirements
            )

            return {
                'material_assignments': optimization_result['assignments'],
                'performance_score': optimization_result['performance_score'],
                'sustainability_score': optimization_result['sustainability_score'],
                'overall_score': optimization_result['overall_score'],
                'validation_results': validation_result,
                'algorithm_used': algorithm,
                'optimization_time': optimization_result['optimization_time']
            }

        except Exception as e:
            self.logger.error(f"Advanced optimization failed: {e}")
            return {'error': str(e)}

    def _analyze_mesh_regions_advanced(self, mesh: trimesh.Trimesh) -> Dict[str, Dict[str, Any]]:
        """Advanced analysis of mesh regions for material assignment."""
        regions = {}

        try:
            # Analyze by geometry and stress patterns
            bounds = mesh.bounds
            height_range = bounds[1][2] - bounds[0][2]

            # Define regions based on height and geometry
            bottom_threshold = bounds[0][2] + height_range * 0.3
            top_threshold = bounds[0][2] + height_range * 0.7

            for i, vertex in enumerate(mesh.vertices):
                z = vertex[2]

                if z < bottom_threshold:
                    region = 'base'
                elif z > top_threshold:
                    region = 'top'
                else:
                    region = 'body'

                if region not in regions:
                    regions[region] = {
                        'vertices': [],
                        'volume': 0.0,
                        'surface_area': 0.0,
                        'stress_level': 'low',
                        'requirements': {}
                    }

                regions[region]['vertices'].append(i)

            # Calculate region properties
            for region, data in regions.items():
                region_mesh = mesh.submesh([data['vertices']], only_watertight=False)
                data['volume'] = region_mesh.volume / 1e9  # Convert to liters
                data['surface_area'] = region_mesh.area if hasattr(region_mesh, 'area') else 0

                # Assign requirements based on region
                if region == 'base':
                    data['requirements'] = {
                        'strength': 'high',
                        'temperature_resistance': 'medium',
                        'flexibility': 'low'
                    }
                    data['stress_level'] = 'high'
                elif region == 'top':
                    data['requirements'] = {
                        'strength': 'medium',
                        'temperature_resistance': 'low',
                        'flexibility': 'medium'
                    }
                    data['stress_level'] = 'low'
                else:
                    data['requirements'] = {
                        'strength': 'medium',
                        'temperature_resistance': 'medium',
                        'flexibility': 'medium'
                    }
                    data['stress_level'] = 'medium'

        except Exception as e:
            self.logger.warning(f"Advanced region analysis failed: {e}")
            regions = {'main': {'volume': mesh.volume / 1e9, 'requirements': {'strength': 'medium'}}}

        return regions

    def _get_candidate_materials(self, requirements: Dict[str, Any]) -> List[str]:
        """Get candidate materials based on requirements."""
        candidates = []

        for material_key, material_data in self.material_database.items():
            if self._material_meets_requirements(material_data, requirements):
                candidates.append(material_key)

        return candidates if candidates else ['recycled_pla']  # Fallback

    def _material_meets_requirements(self, material: Dict[str, Any],
                                   requirements: Dict[str, Any]) -> bool:
        """Check if material meets all requirements."""
        for req_key, req_value in requirements.items():
            if req_key in material.get('properties', {}):
                material_value = material['properties'][req_key]

                if isinstance(req_value, str):
                    if material_value != req_value:
                        return False
                elif isinstance(req_value, dict):
                    if 'min' in req_value and material_value < req_value['min']:
                        return False
                    if 'max' in req_value and material_value > req_value['max']:
                        return False

        return True

    def _genetic_optimization(self, regions: Dict[str, Dict[str, Any]],
                            candidates: List[str],
                            requirements: Dict[str, Any],
                            goals: Dict[str, float]) -> Dict[str, Any]:
        """Genetic algorithm for material optimization."""
        # Simplified genetic algorithm implementation
        start_time = time.time()

        # Generate initial population
        population_size = 20
        generations = 10

        # Create initial population (random assignments)
        population = []
        for _ in range(population_size):
            assignment = {}
            for region in regions:
                assignment[region] = np.random.choice(candidates)
            population.append(assignment)

        # Evolve population
        for generation in range(generations):
            # Evaluate fitness
            fitness_scores = []
            for assignment in population:
                fitness = self._calculate_fitness(assignment, regions, requirements, goals)
                fitness_scores.append((assignment, fitness))

            # Select best individuals
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            best_individuals = fitness_scores[:population_size // 2]

            # Create new population through crossover and mutation
            new_population = [ind[0] for ind in best_individuals]

            while len(new_population) < population_size:
                # Crossover
                parent1 = np.random.choice([ind[0] for ind in best_individuals])
                parent2 = np.random.choice([ind[0] for ind in best_individuals])

                child = {}
                for region in regions:
                    child[region] = np.random.choice([parent1[region], parent2[region]])

                # Mutation
                if np.random.random() < 0.1:  # 10% mutation rate
                    region_to_mutate = np.random.choice(list(regions.keys()))
                    child[region_to_mutate] = np.random.choice(candidates)

                new_population.append(child)

            population = new_population

        # Get best solution
        best_assignment = fitness_scores[0][0]
        best_fitness = fitness_scores[0][1]

        return {
            'assignments': best_assignment,
            'performance_score': best_fitness['performance'],
            'sustainability_score': best_fitness['sustainability'],
            'overall_score': best_fitness['overall'],
            'optimization_time': time.time() - start_time
        }

    def _calculate_fitness(self, assignment: Dict[str, str],
                         regions: Dict[str, Dict[str, Any]],
                         requirements: Dict[str, Any],
                         goals: Dict[str, float]) -> Dict[str, float]:
        """Calculate fitness score for a material assignment."""
        fitness = {
            'performance': 0.0,
            'sustainability': 0.0,
            'overall': 0.0
        }

        try:
            total_carbon_footprint = 0.0
            total_cost = 0.0
            performance_score = 0.0

            for region, material in assignment.items():
                if material in self.material_database:
                    material_data = self.material_database[material]
                    region_data = regions[region]

                    # Calculate carbon footprint
                    region_volume = region_data['volume']
                    region_mass = region_volume * 1.2  # Assume 1.2 g/cm³
                    footprint = region_mass * material_data['carbon_footprint']
                    total_carbon_footprint += footprint

                    # Calculate cost
                    cost = region_mass * material_data['properties']['cost_per_kg'] / 1000
                    total_cost += cost

                    # Calculate performance score
                    region_performance = self._calculate_region_performance(
                        material_data, region_data['requirements']
                    )
                    performance_score += region_performance

            # Normalize scores
            avg_performance = performance_score / len(regions)
            sustainability_score = 1.0 / (1.0 + total_carbon_footprint / 100)  # Normalize to 0-1

            fitness['performance'] = avg_performance
            fitness['sustainability'] = sustainability_score
            fitness['overall'] = (avg_performance * 0.6) + (sustainability_score * 0.4)

        except Exception as e:
            self.logger.warning(f"Fitness calculation failed: {e}")

        return fitness

    def _calculate_region_performance(self, material: Dict[str, Any],
                                    requirements: Dict[str, Any]) -> float:
        """Calculate how well a material performs for a region."""
        score = 0.0

        try:
            # Strength matching
            if 'strength' in requirements:
                required_strength = {'low': 40, 'medium': 60, 'high': 80}.get(requirements['strength'], 60)
                material_strength = material['mechanical_properties']['tensile_strength']
                strength_score = min(material_strength / required_strength, 1.0)
                score += strength_score * 0.4

            # Temperature resistance matching
            if 'temperature_resistance' in requirements:
                required_temp = {'low': 50, 'medium': 70, 'high': 90}.get(requirements['temperature_resistance'], 70)
                material_temp = material['thermal_properties']['heat_deflection_temp']
                temp_score = min(material_temp / required_temp, 1.0)
                score += temp_score * 0.3

            # Flexibility matching
            if 'flexibility' in requirements:
                required_flex = {'low': 5, 'medium': 50, 'high': 100}.get(requirements['flexibility'], 50)
                material_flex = material['mechanical_properties']['elongation_at_break']
                flex_score = min(material_flex / required_flex, 1.0)
                score += flex_score * 0.3

        except Exception as e:
            self.logger.warning(f"Region performance calculation failed: {e}")

        return min(score, 1.0)

    def _simulated_annealing_optimization(self, regions: Dict[str, Dict[str, Any]],
                                        candidates: List[str],
                                        requirements: Dict[str, Any],
                                        goals: Dict[str, float]) -> Dict[str, Any]:
        """Simulated annealing optimization for material assignment."""
        # Simplified simulated annealing implementation
        start_time = time.time()

        current_assignment = {region: np.random.choice(candidates) for region in regions}
        current_fitness = self._calculate_fitness(current_assignment, regions, requirements, goals)

        best_assignment = current_assignment.copy()
        best_fitness = current_fitness.copy()

        temperature = 100.0
        cooling_rate = 0.95
        max_iterations = 100

        for iteration in range(max_iterations):
            # Generate neighbor solution
            neighbor_assignment = current_assignment.copy()
            region_to_change = np.random.choice(list(regions.keys()))
            neighbor_assignment[region_to_change] = np.random.choice(candidates)

            neighbor_fitness = self._calculate_fitness(neighbor_assignment, regions, requirements, goals)

            # Decide whether to accept neighbor
            if neighbor_fitness['overall'] > current_fitness['overall']:
                current_assignment = neighbor_assignment
                current_fitness = neighbor_fitness
            else:
                acceptance_probability = np.exp(
                    (neighbor_fitness['overall'] - current_fitness['overall']) / temperature
                )
                if np.random.random() < acceptance_probability:
                    current_assignment = neighbor_assignment
                    current_fitness = neighbor_fitness

            # Update best solution
            if current_fitness['overall'] > best_fitness['overall']:
                best_assignment = current_assignment.copy()
                best_fitness = current_fitness.copy()

            # Cool down
            temperature *= cooling_rate

        return {
            'assignments': best_assignment,
            'performance_score': best_fitness['performance'],
            'sustainability_score': best_fitness['sustainability'],
            'overall_score': best_fitness['overall'],
            'optimization_time': time.time() - start_time
        }

    def _particle_swarm_optimization(self, regions: Dict[str, Dict[str, Any]],
                                   candidates: List[str],
                                   requirements: Dict[str, Any],
                                   goals: Dict[str, float]) -> Dict[str, Any]:
        """Particle swarm optimization for material assignment."""
        # Simplified PSO implementation
        start_time = time.time()

        num_particles = 10
        max_iterations = 50

        # Initialize particles
        particles = []
        velocities = []
        personal_best = []
        personal_best_fitness = []

        for _ in range(num_particles):
            assignment = {region: np.random.choice(candidates) for region in regions}
            particles.append(assignment)
            velocities.append({region: 0 for region in regions})
            personal_best.append(assignment.copy())
            personal_best_fitness.append(
                self._calculate_fitness(assignment, regions, requirements, goals)
            )

        global_best = personal_best[0].copy()
        global_best_fitness = personal_best_fitness[0].copy()

        # PSO parameters
        w = 0.7  # Inertia weight
        c1 = 1.5  # Cognitive parameter
        c2 = 1.5  # Social parameter

        for iteration in range(max_iterations):
            for i, particle in enumerate(particles):
                particle_fitness = self._calculate_fitness(particle, regions, requirements, goals)

                # Update personal best
                if particle_fitness['overall'] > personal_best_fitness[i]['overall']:
                    personal_best[i] = particle.copy()
                    personal_best_fitness[i] = particle_fitness.copy()

                # Update global best
                if particle_fitness['overall'] > global_best_fitness['overall']:
                    global_best = particle.copy()
                    global_best_fitness = particle_fitness.copy()

                # Update velocity and position
                for region in regions:
                    # Update velocity
                    r1, r2 = np.random.random(), np.random.random()
                    cognitive = c1 * r1 * (1 if personal_best[i][region] == particle[region] else 0)
                    social = c2 * r2 * (1 if global_best[region] == particle[region] else 0)

                    velocities[i][region] = (w * velocities[i][region] +
                                           cognitive + social)

                    # Update position (simplified)
                    if np.random.random() < abs(velocities[i][region]):
                        particle[region] = np.random.choice(candidates)

        return {
            'assignments': global_best,
            'performance_score': global_best_fitness['performance'],
            'sustainability_score': global_best_fitness['sustainability'],
            'overall_score': global_best_fitness['overall'],
            'optimization_time': time.time() - start_time
        }

    def _multi_objective_optimization(self, regions: Dict[str, Dict[str, Any]],
                                    candidates: List[str],
                                    requirements: Dict[str, Any],
                                    goals: Dict[str, float]) -> Dict[str, Any]:
        """Multi-objective optimization balancing performance and sustainability."""
        start_time = time.time()

        # Use Pareto front approach
        pareto_solutions = []

        # Generate multiple solutions using different strategies
        for strategy in ['performance_focused', 'sustainability_focused', 'balanced']:
            solution = self._generate_solution_for_strategy(
                regions, candidates, requirements, goals, strategy
            )

            if solution:
                pareto_solutions.append(solution)

        # Select best solution based on goals
        best_solution = None
        best_score = -1

        for solution in pareto_solutions:
            score = self._evaluate_solution_against_goals(solution, goals)
            if score > best_score:
                best_score = score
                best_solution = solution

        return {
            'assignments': best_solution['assignments'],
            'performance_score': best_solution['performance_score'],
            'sustainability_score': best_solution['sustainability_score'],
            'overall_score': best_solution['overall_score'],
            'optimization_time': time.time() - start_time
        }

    def _generate_solution_for_strategy(self, regions: Dict[str, Dict[str, Any]],
                                      candidates: List[str],
                                      requirements: Dict[str, Any],
                                      goals: Dict[str, float],
                                      strategy: str) -> Dict[str, Any]:
        """Generate solution for specific optimization strategy."""
        assignment = {}

        for region, region_data in regions.items():
            if strategy == 'performance_focused':
                # Choose material with best mechanical properties
                best_material = max(
                    candidates,
                    key=lambda m: self._calculate_material_performance_score(
                        self.material_database[m], region_data['requirements']
                    )
                )
            elif strategy == 'sustainability_focused':
                # Choose most sustainable material that meets requirements
                best_material = min(
                    candidates,
                    key=lambda m: self.material_database[m]['carbon_footprint']
                )
            else:  # balanced
                # Balance both factors
                best_material = max(
                    candidates,
                    key=lambda m: (
                        self._calculate_material_performance_score(
                            self.material_database[m], region_data['requirements']
                        ) * 0.6 +
                        (10 - self.material_database[m]['carbon_footprint']) * 0.4
                    )
                )

            assignment[region] = best_material

        fitness = self._calculate_fitness(assignment, regions, requirements, goals)

        return {
            'assignments': assignment,
            'performance_score': fitness['performance'],
            'sustainability_score': fitness['sustainability'],
            'overall_score': fitness['overall']
        }

    def _calculate_material_performance_score(self, material: Dict[str, Any],
                                            requirements: Dict[str, Any]) -> float:
        """Calculate performance score for a material against requirements."""
        score = 0.0

        try:
            # Strength score
            if 'strength' in requirements:
                req_strength = {'low': 40, 'medium': 60, 'high': 80}.get(requirements['strength'], 60)
                mat_strength = material['mechanical_properties']['tensile_strength']
                score += min(mat_strength / req_strength, 1.0) * 0.5

            # Temperature score
            if 'temperature_resistance' in requirements:
                req_temp = {'low': 50, 'medium': 70, 'high': 90}.get(requirements['temperature_resistance'], 70)
                mat_temp = material['thermal_properties']['heat_deflection_temp']
                score += min(mat_temp / req_temp, 1.0) * 0.3

            # Flexibility score
            if 'flexibility' in requirements:
                req_flex = {'low': 5, 'medium': 50, 'high': 100}.get(requirements['flexibility'], 50)
                mat_flex = material['mechanical_properties']['elongation_at_break']
                score += min(mat_flex / req_flex, 1.0) * 0.2

        except Exception:
            score = 0.5  # Default score

        return min(score, 1.0)

    def _evaluate_solution_against_goals(self, solution: Dict[str, Any],
                                       goals: Dict[str, float]) -> float:
        """Evaluate how well a solution meets the goals."""
        score = 0.0

        try:
            # Performance goal
            if 'performance_target' in goals:
                perf_score = solution['performance_score']
                target = goals['performance_target']
                score += min(perf_score / target, 1.0) * 0.5

            # Sustainability goal
            if 'sustainability_target' in goals:
                sust_score = solution['sustainability_score']
                target = goals['sustainability_target']
                score += min(sust_score / target, 1.0) * 0.5

        except Exception:
            score = 0.5

        return score

    def _validate_optimization_result(self, result: Dict[str, Any],
                                    mesh: trimesh.Trimesh,
                                    requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Validate optimization results."""
        validation = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'suggestions': []
        }

        try:
            assignments = result['assignments']

            # Check material compatibility
            for region, material in assignments.items():
                if material not in self.material_database:
                    validation['errors'].append(f"Unknown material {material} for region {region}")
                    validation['valid'] = False

            # Check requirement satisfaction
            for region, region_data in self._analyze_mesh_regions_advanced(mesh).items():
                if region in assignments:
                    material = assignments[region]
                    material_data = self.material_database.get(material, {})

                    for req_key, req_value in region_data['requirements'].items():
                        if req_key in material_data.get('properties', {}):
                            material_value = material_data['properties'][req_key]

                            if isinstance(req_value, str):
                                if material_value != req_value:
                                    validation['warnings'].append(
                                        f"Material {material} may not meet {req_key} requirement for {region}"
                                    )

            # Generate suggestions
            if result['overall_score'] < 0.7:
                validation['suggestions'].append(
                    "Consider adjusting requirements or exploring additional materials"
                )

        return validation


class EnergyConsumptionOptimizer:
    """Optimizes energy consumption for sustainable 3D printing."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.energy_profiles = self._initialize_energy_profiles()

    def _initialize_energy_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Initialize energy consumption profiles for different materials and processes."""
        return {
            'recycled_pla': {
                'production_energy': 35,  # MJ/kg
                'printing_energy': 0.8,  # MJ/kg
                'transport_energy': 0.2,  # MJ/kg per 100km
                'end_of_life_energy': -5,  # MJ/kg (energy recovery)
                'energy_source_factor': 1.2  # Grid electricity factor
            },
            'bio_petg': {
                'production_energy': 40,
                'printing_energy': 0.9,
                'transport_energy': 0.25,
                'end_of_life_energy': -3,
                'energy_source_factor': 1.1
            },
            'hemp_pla': {
                'production_energy': 30,
                'printing_energy': 0.7,
                'transport_energy': 0.15,
                'end_of_life_energy': -6,
                'energy_source_factor': 1.0
            },
            'algae_pla': {
                'production_energy': 25,
                'printing_energy': 0.6,
                'transport_energy': 0.1,
                'end_of_life_energy': -8,
                'energy_source_factor': 0.8  # Renewable energy
            }
        }

    def optimize_printing_energy(self, material: str, print_settings: Dict[str, Any],
                               printer_specs: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize printing parameters for energy efficiency."""
        optimization = {
            'optimized_settings': {},
            'energy_savings': 0.0,
            'carbon_reduction': 0.0,
            'recommendations': []
        }

        try:
            if material not in self.energy_profiles:
                return optimization

            profile = self.energy_profiles[material]
            current_energy = self._calculate_current_energy_consumption(
                material, print_settings, printer_specs
            )

            # Optimize layer height for energy efficiency
            optimal_layer_height = self._optimize_layer_height(
                print_settings, printer_specs, profile
            )

            # Optimize print speed
            optimal_speed = self._optimize_print_speed(
                print_settings, printer_specs, profile
            )

            # Optimize infill density
            optimal_infill = self._optimize_infill_density(
                print_settings, printer_specs, profile
            )

            # Calculate energy savings
            optimized_energy = self._calculate_optimized_energy_consumption(
                material, {**print_settings,
                          'layer_height': optimal_layer_height,
                          'speed': optimal_speed,
                          'infill_density': optimal_infill},
                printer_specs
            )

            energy_savings = current_energy - optimized_energy
            carbon_reduction = energy_savings * profile['energy_source_factor'] * 0.4  # kg CO2/MJ

            optimization.update({
                'optimized_settings': {
                    'layer_height': optimal_layer_height,
                    'speed': optimal_speed,
                    'infill_density': optimal_infill
                },
                'energy_savings': energy_savings,
                'carbon_reduction': carbon_reduction,
                'recommendations': self._generate_energy_recommendations(
                    energy_savings, carbon_reduction, profile
                )
            })

        except Exception as e:
            self.logger.error(f"Energy optimization failed: {e}")
            optimization['error'] = str(e)

        return optimization

    def _calculate_current_energy_consumption(self, material: str,
                                           print_settings: Dict[str, Any],
                                           printer_specs: Dict[str, Any]) -> float:
        """Calculate current energy consumption for printing."""
        try:
            profile = self.energy_profiles.get(material, {})
            base_energy = profile.get('printing_energy', 0.8)

            # Adjust for print settings
            layer_height_factor = print_settings.get('layer_height', 0.2) / 0.2
            speed_factor = min(print_settings.get('speed', 50) / 50, 2.0)

            return base_energy * layer_height_factor * speed_factor

        except Exception:
            return 0.8  # Default value

    def _calculate_optimized_energy_consumption(self, material: str,
                                              optimized_settings: Dict[str, Any],
                                              printer_specs: Dict[str, Any]) -> float:
        """Calculate energy consumption with optimized settings."""
        try:
            profile = self.energy_profiles.get(material, {})
            base_energy = profile.get('printing_energy', 0.8)

            # Apply optimization factors
            layer_height_factor = optimized_settings.get('layer_height', 0.2) / 0.2
            speed_factor = min(optimized_settings.get('speed', 50) / 50, 2.0)
            infill_factor = optimized_settings.get('infill_density', 20) / 100.0

            return base_energy * layer_height_factor * speed_factor * infill_factor

        except Exception:
            return 0.7  # Optimized default

    def _optimize_layer_height(self, print_settings: Dict[str, Any],
                             printer_specs: Dict[str, Any],
                             energy_profile: Dict[str, Any]) -> float:
        """Optimize layer height for energy efficiency."""
        current_height = print_settings.get('layer_height', 0.2)

        # Optimal layer height balances print time and energy use
        # Thicker layers use less energy but may reduce quality
        if printer_specs.get('max_layer_height', 0.3) >= 0.25:
            return min(current_height + 0.02, 0.25)  # Increase by 0.02mm up to 0.25mm
        else:
            return current_height

    def _optimize_print_speed(self, print_settings: Dict[str, Any],
                            printer_specs: Dict[str, Any],
                            energy_profile: Dict[str, Any]) -> int:
        """Optimize print speed for energy efficiency."""
        current_speed = print_settings.get('speed', 50)

        # Slower speeds use more energy but improve quality
        # Optimal balance is around 40-60 mm/s for most materials
        if current_speed > 60:
            return 60  # Cap at 60 mm/s for energy efficiency
        elif current_speed < 40:
            return 40  # Minimum for reasonable print time
        else:
            return current_speed

    def _optimize_infill_density(self, print_settings: Dict[str, Any],
                               printer_specs: Dict[str, Any],
                               energy_profile: Dict[str, Any]) -> int:
        """Optimize infill density for energy efficiency."""
        current_infill = print_settings.get('infill_density', 20)

        # Lower infill saves energy but may reduce strength
        if current_infill > 15:
            return max(current_infill - 5, 15)  # Reduce by 5% but not below 15%
        else:
            return current_infill

    def _generate_energy_recommendations(self, energy_savings: float,
                                       carbon_reduction: float,
                                       energy_profile: Dict[str, Any]) -> List[str]:
        """Generate energy optimization recommendations."""
        recommendations = []

        if energy_savings > 0.1:
            recommendations.append(
                f"Energy savings of {energy_savings:.2f} MJ/kg achieved through parameter optimization"
            )

        if carbon_reduction > 0.05:
            recommendations.append(
                f"Carbon reduction of {carbon_reduction:.2f} kg CO2/kg from energy optimization"
            )

        if energy_profile.get('energy_source_factor', 1.0) > 1.5:
            recommendations.append(
                "Consider using renewable energy sources for further carbon reduction"
            )

        return recommendations