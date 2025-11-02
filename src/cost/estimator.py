"""Cost estimation for 3D printing projects."""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import math
from datetime import timedelta

from .materials import MaterialDatabase, Material


@dataclass
class PrintCostBreakdown:
    """Detailed cost breakdown for a print job."""
    material_cost: float
    labor_cost: float
    machine_cost: float
    power_cost: float
    overhead_cost: float
    total_cost: float

    # Material details
    material_volume: float  # cm³
    material_weight: float  # grams
    material_price_per_kg: float

    # Time details
    print_time: timedelta
    prep_time: timedelta
    post_process_time: timedelta
    total_time: timedelta

    # Machine details
    machine_hourly_rate: float
    power_consumption: float  # kWh
    power_rate: float  # $/kWh

    # Additional costs
    support_material_cost: float = 0.0
    waste_factor: float = 1.1  # 10% waste
    failure_rate: float = 0.05  # 5% failure rate

    currency: str = "USD"


class CostEstimator:
    """Estimate printing costs for 3D models."""

    def __init__(self, material_db: Optional[MaterialDatabase] = None):
        """Initialize cost estimator.

        Args:
            material_db: Material database for pricing
        """
        self.material_db = material_db or MaterialDatabase()

        # Default rates (can be configured)
        self.default_rates = {
            'labor_rate': 25.0,  # $/hour
            'machine_rate': 10.0,  # $/hour
            'power_rate': 0.12,  # $/kWh
            'overhead_rate': 0.3,  # 30% overhead
        }

    def estimate_cost(
        self,
        mesh_volume: float,  # cm³
        print_time: float,  # seconds
        material_name: str = "PLA",
        infill_density: float = 20.0,  # %
        support_volume: float = 0.0,  # cm³
        printer_config: Optional[Dict[str, Any]] = None,
        pricing_config: Optional[Dict[str, Any]] = None
    ) -> PrintCostBreakdown:
        """Estimate total cost for printing a model.

        Args:
            mesh_volume: Volume of the mesh in cm³
            print_time: Print time in seconds
            material_name: Material type
            infill_density: Infill percentage
            support_volume: Volume of support material in cm³
            printer_config: Printer configuration
            pricing_config: Pricing configuration

        Returns:
            Detailed cost breakdown
        """
        # Get material properties
        material = self.material_db.get_material(material_name)
        if not material:
            material = self.material_db.get_default_material()

        # Merge configurations
        rates = {**self.default_rates, **(pricing_config or {})}
        printer = {
            'power_consumption': 200.0,  # watts
            'nozzle_diameter': 0.4,
            'layer_height': 0.2,
            **(printer_config or {})
        }

        # Calculate material usage
        material_volume = self._calculate_material_volume(
            mesh_volume, infill_density, support_volume
        )
        material_weight = material_volume * material.density  # grams

        # Calculate material cost
        material_cost = (material_weight / 1000) * material.price_per_kg

        # Support material cost
        support_material_cost = 0.0
        if support_volume > 0:
            support_weight = support_volume * material.density
            support_material_cost = (support_weight / 1000) * material.price_per_kg

        # Apply waste factor
        total_material_cost = (material_cost + support_material_cost) * rates.get('waste_factor', 1.1)

        # Calculate time costs
        print_time_hours = print_time / 3600
        prep_time = timedelta(minutes=max(5, print_time_hours * 60 * 0.1))  # 10% of print time, min 5 min
        post_process_time = timedelta(minutes=max(2, print_time_hours * 60 * 0.05))  # 5% of print time, min 2 min
        total_time_hours = print_time_hours + (prep_time.total_seconds() + post_process_time.total_seconds()) / 3600

        # Labor cost
        labor_cost = total_time_hours * rates['labor_rate']

        # Machine cost
        machine_cost = print_time_hours * rates['machine_rate']

        # Power cost
        power_consumption_kwh = (printer['power_consumption'] / 1000) * print_time_hours
        power_cost = power_consumption_kwh * rates['power_rate']

        # Calculate base cost
        base_cost = total_material_cost + labor_cost + machine_cost + power_cost

        # Overhead cost
        overhead_cost = base_cost * rates['overhead_rate']

        # Account for failure rate
        failure_factor = 1 / (1 - rates.get('failure_rate', 0.05))

        # Total cost
        total_cost = (base_cost + overhead_cost) * failure_factor

        return PrintCostBreakdown(
            material_cost=total_material_cost,
            labor_cost=labor_cost,
            machine_cost=machine_cost,
            power_cost=power_cost,
            overhead_cost=overhead_cost,
            total_cost=total_cost,

            material_volume=material_volume,
            material_weight=material_weight,
            material_price_per_kg=material.price_per_kg,

            print_time=timedelta(seconds=print_time),
            prep_time=prep_time,
            post_process_time=post_process_time,
            total_time=timedelta(seconds=total_time_hours * 3600),

            machine_hourly_rate=rates['machine_rate'],
            power_consumption=power_consumption_kwh,
            power_rate=rates['power_rate'],

            support_material_cost=support_material_cost,
            waste_factor=rates.get('waste_factor', 1.1),
            failure_rate=rates.get('failure_rate', 0.05)
        )

    def _calculate_material_volume(
        self,
        mesh_volume: float,
        infill_density: float,
        support_volume: float
    ) -> float:
        """Calculate actual material volume needed.

        Args:
            mesh_volume: Solid mesh volume
            infill_density: Infill percentage
            support_volume: Support volume

        Returns:
            Actual material volume in cm³
        """
        # Estimate shell volume (assume 2 perimeters, 0.4mm nozzle)
        perimeter_thickness = 0.8  # 2 * 0.4mm
        shell_ratio = min(1.0, perimeter_thickness / (mesh_volume ** (1/3)))

        # Calculate shell and infill volumes
        shell_volume = mesh_volume * shell_ratio
        infill_volume = (mesh_volume - shell_volume) * (infill_density / 100)

        # Total material volume
        total_volume = shell_volume + infill_volume + support_volume

        return total_volume

    def estimate_batch_cost(
        self,
        print_jobs: List[Dict[str, Any]],
        batch_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Estimate cost for batch printing.

        Args:
            print_jobs: List of print job specifications
            batch_config: Batch-specific configuration

        Returns:
            Batch cost analysis
        """
        individual_costs = []
        total_cost = 0.0
        total_time = 0.0
        total_material = 0.0

        for job in print_jobs:
            cost_breakdown = self.estimate_cost(**job)
            individual_costs.append(cost_breakdown)
            total_cost += cost_breakdown.total_cost
            total_time += cost_breakdown.print_time.total_seconds()
            total_material += cost_breakdown.material_weight

        # Batch efficiency factors
        batch_discount = batch_config.get('batch_discount', 0.0) if batch_config else 0.0
        setup_overhead = batch_config.get('setup_overhead', 0.0) if batch_config else 0.0

        # Apply batch adjustments
        adjusted_cost = total_cost * (1 - batch_discount) + setup_overhead

        return {
            'individual_costs': individual_costs,
            'total_cost': adjusted_cost,
            'base_cost': total_cost,
            'batch_discount': batch_discount,
            'setup_overhead': setup_overhead,
            'total_time_hours': total_time / 3600,
            'total_material_kg': total_material / 1000,
            'average_cost_per_job': adjusted_cost / len(print_jobs) if print_jobs else 0,
            'cost_per_gram': adjusted_cost / total_material if total_material > 0 else 0
        }

    def calculate_pricing_tiers(
        self,
        base_cost: float,
        profit_margins: Optional[List[float]] = None
    ) -> Dict[str, float]:
        """Calculate different pricing tiers.

        Args:
            base_cost: Base cost of production
            profit_margins: List of profit margin percentages

        Returns:
            Dictionary of pricing tiers
        """
        if profit_margins is None:
            profit_margins = [15, 25, 40, 60]  # Basic, Standard, Premium, Express

        tiers = {}
        tier_names = ['basic', 'standard', 'premium', 'express']

        for i, margin in enumerate(profit_margins):
            tier_name = tier_names[i] if i < len(tier_names) else f'tier_{i+1}'
            price = base_cost * (1 + margin / 100)
            tiers[tier_name] = round(price, 2)

        return tiers

    def optimize_for_cost(
        self,
        mesh_volume: float,
        target_cost: float,
        material_name: str = "PLA",
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Optimize print settings to meet target cost.

        Args:
            mesh_volume: Volume of mesh
            target_cost: Target cost to achieve
            material_name: Material type
            constraints: Optimization constraints

        Returns:
            Optimized settings and cost breakdown
        """
        constraints = constraints or {}

        # Define parameter ranges
        infill_range = constraints.get('infill_range', [10, 50])
        layer_height_range = constraints.get('layer_height_range', [0.15, 0.3])

        best_settings = None
        best_cost = float('inf')
        best_breakdown = None

        # Grid search optimization (simple approach)
        for infill in range(infill_range[0], infill_range[1] + 1, 5):
            for layer_height in [0.15, 0.2, 0.25, 0.3]:
                if layer_height < layer_height_range[0] or layer_height > layer_height_range[1]:
                    continue

                # Estimate print time (simplified)
                estimated_time = self._estimate_print_time(mesh_volume, layer_height, infill)

                # Calculate cost
                breakdown = self.estimate_cost(
                    mesh_volume=mesh_volume,
                    print_time=estimated_time,
                    material_name=material_name,
                    infill_density=infill
                )

                # Check if this is better and meets target
                cost_diff = abs(breakdown.total_cost - target_cost)
                if cost_diff < abs(best_cost - target_cost):
                    best_cost = breakdown.total_cost
                    best_settings = {
                        'infill_density': infill,
                        'layer_height': layer_height
                    }
                    best_breakdown = breakdown

        return {
            'optimal_settings': best_settings,
            'achieved_cost': best_cost,
            'target_cost': target_cost,
            'cost_difference': best_cost - target_cost,
            'cost_breakdown': best_breakdown
        }

    def _estimate_print_time(
        self,
        volume: float,
        layer_height: float,
        infill_density: float
    ) -> float:
        """Rough estimation of print time.

        Args:
            volume: Print volume
            layer_height: Layer height
            infill_density: Infill percentage

        Returns:
            Estimated print time in seconds
        """
        # Very simplified time estimation
        # In practice, this would use proper slicing simulation

        base_time = volume * 10  # 10 seconds per cm³ baseline

        # Layer height factor
        layer_factor = 0.2 / layer_height  # Thinner layers = longer time

        # Infill factor
        infill_factor = 0.5 + (infill_density / 100) * 0.5

        estimated_time = base_time * layer_factor * infill_factor

        return estimated_time

    def compare_materials(
        self,
        mesh_volume: float,
        print_time: float,
        materials: List[str],
        infill_density: float = 20.0
    ) -> Dict[str, PrintCostBreakdown]:
        """Compare costs across different materials.

        Args:
            mesh_volume: Volume of mesh
            print_time: Print time
            materials: List of material names
            infill_density: Infill percentage

        Returns:
            Dictionary of material costs
        """
        comparisons = {}

        for material in materials:
            breakdown = self.estimate_cost(
                mesh_volume=mesh_volume,
                print_time=print_time,
                material_name=material,
                infill_density=infill_density
            )
            comparisons[material] = breakdown

        return comparisons

    def generate_cost_report(
        self,
        breakdown: PrintCostBreakdown,
        include_details: bool = True
    ) -> Dict[str, Any]:
        """Generate detailed cost report.

        Args:
            breakdown: Cost breakdown
            include_details: Include detailed breakdown

        Returns:
            Cost report dictionary
        """
        report = {
            'summary': {
                'total_cost': round(breakdown.total_cost, 2),
                'material_cost': round(breakdown.material_cost, 2),
                'labor_cost': round(breakdown.labor_cost, 2),
                'machine_cost': round(breakdown.machine_cost, 2),
                'currency': breakdown.currency
            },
            'material': {
                'volume_cm3': round(breakdown.material_volume, 2),
                'weight_grams': round(breakdown.material_weight, 2),
                'price_per_kg': breakdown.material_price_per_kg
            },
            'time': {
                'print_time': str(breakdown.print_time),
                'prep_time': str(breakdown.prep_time),
                'post_process_time': str(breakdown.post_process_time),
                'total_time': str(breakdown.total_time)
            }
        }

        if include_details:
            report['detailed_breakdown'] = {
                'material_cost': round(breakdown.material_cost, 2),
                'support_material_cost': round(breakdown.support_material_cost, 2),
                'labor_cost': round(breakdown.labor_cost, 2),
                'machine_cost': round(breakdown.machine_cost, 2),
                'power_cost': round(breakdown.power_cost, 2),
                'overhead_cost': round(breakdown.overhead_cost, 2),
                'waste_factor': breakdown.waste_factor,
                'failure_rate': breakdown.failure_rate
            }

        return report