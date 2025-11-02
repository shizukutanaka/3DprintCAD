"""Large-scale 3D printing support for construction and aerospace applications.

This module enables printing of large structures with optimized slicing,
path planning, and material handling for industrial-scale projects.
"""

from __future__ import annotations

import numpy as np
import trimesh
from typing import Dict, Any, Optional, List, Tuple
import logging
from dataclasses import dataclass, field
from enum import Enum

class LargeScalePrintMode(Enum):
    """Modes for large-scale printing."""
    CONSTRUCTION = "construction"     # Building and infrastructure
    AEROSPACE = "aerospace"          # Aircraft and spacecraft parts
    AUTOMOTIVE = "automotive"        # Large vehicle components
    MARINE = "marine"               # Ship and boat parts
    INDUSTRIAL = "industrial"       # General industrial applications

class StructuralOptimization(Enum):
    """Optimization strategies for large structures."""
    WEIGHT_REDUCTION = "weight_reduction"
    STRENGTH_MAXIMIZATION = "strength_maximization"
    COST_MINIMIZATION = "cost_minimization"
    PRINT_TIME_OPTIMIZATION = "print_time_optimization"

@dataclass
class LargeScaleConfig:
    """Configuration for large-scale printing."""
    print_mode: LargeScalePrintMode = LargeScalePrintMode.CONSTRUCTION
    max_print_volume: Tuple[float, float, float] = (1000.0, 1000.0, 1000.0)  # mm
    layer_height_mm: float = 10.0  # Larger layers for speed
    infill_percentage: int = 15
    support_density: float = 0.1  # Lower density for large structures
    optimization_strategy: StructuralOptimization = StructuralOptimization.PRINT_TIME_OPTIMIZATION

class LargeScalePrinter:
    """Large-scale 3D printing system."""

    def __init__(self, config: LargeScaleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def prepare_large_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Prepare mesh for large-scale printing."""
        # Scale mesh if necessary
        scaled_mesh = self._scale_for_print_volume(mesh)

        # Optimize for large-scale printing
        optimized_mesh = self._optimize_for_large_scale(scaled_mesh)

        return optimized_mesh

    def _scale_for_print_volume(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Scale mesh to fit within print volume."""
        bounds = mesh.bounds
        dimensions = bounds[1] - bounds[0]

        max_dim = max(dimensions)
        max_print_dim = max(self.config.max_print_volume)

        if max_dim > max_print_dim:
            scale_factor = max_print_dim / max_dim * 0.95  # Leave 5% margin
            scaled_mesh = mesh.apply_scale(scale_factor)
            self.logger.info(f"Scaled mesh by factor {scale_factor:.3f}")
        else:
            scaled_mesh = mesh.copy()

        return scaled_mesh

    def _optimize_for_large_scale(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Optimize mesh for large-scale printing."""
        optimized_mesh = mesh.copy()

        # Add structural reinforcements for large prints
        if self.config.print_mode == LargeScalePrintMode.CONSTRUCTION:
            optimized_mesh = self._add_construction_reinforcements(optimized_mesh)

        # Optimize infill pattern for large structures
        optimized_mesh = self._optimize_infill_for_large_scale(optimized_mesh)

        return optimized_mesh

    def _add_construction_reinforcements(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Add reinforcements for construction-scale prints."""
        # Add internal supports and reinforcements
        reinforced_mesh = mesh.copy()

        # Simple reinforcement: add vertical pillars at regular intervals
        bounds = reinforced_mesh.bounds
        pillar_spacing = 200.0  # mm

        # Calculate number of pillars needed
        length = bounds[1][0] - bounds[0][0]
        width = bounds[1][1] - bounds[0][1]

        num_pillars_x = int(length / pillar_spacing) + 1
        num_pillars_y = int(width / pillar_spacing) + 1

        for i in range(num_pillars_x):
            for j in range(num_pillars_y):
                x = bounds[0][0] + i * pillar_spacing
                y = bounds[0][1] + j * pillar_spacing
                z = bounds[0][2]

                # Create pillar
                pillar = trimesh.creation.cylinder(radius=50.0, height=bounds[1][2] - bounds[0][2])

                # Position pillar
                pillar.apply_translation([x, y, z])

                # Combine with main mesh
                reinforced_mesh = trimesh.util.concatenate([reinforced_mesh, pillar])

        return reinforced_mesh

    def _optimize_infill_for_large_scale(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Optimize infill pattern for large structures."""
        # Use sparse infill for large prints to save material and time
        if self.config.infill_percentage < 20:
            # Add structural infill where needed
            optimized_mesh = self._add_structural_infill(mesh)
        else:
            optimized_mesh = mesh.copy()

        return optimized_mesh

    def _add_structural_infill(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Add structural infill for strength in large prints."""
        # Create internal structure for support
        # Simple honeycomb pattern for demonstration

        bounds = mesh.bounds
        honeycomb_mesh = mesh.copy()

        # Generate honeycomb pattern
        cell_size = 100.0  # mm
        wall_thickness = 10.0  # mm

        # Create honeycomb cells
        for i in range(int((bounds[1][0] - bounds[0][0]) / cell_size)):
            for j in range(int((bounds[1][1] - bounds[0][1]) / cell_size)):
                x = bounds[0][0] + i * cell_size + cell_size / 2
                y = bounds[0][1] + j * cell_size + cell_size / 2

                # Create hexagonal cell
                hex_cell = self._create_hexagonal_cell(cell_size, wall_thickness, [x, y, (bounds[0][2] + bounds[1][2]) / 2])

                # Combine with main mesh
                honeycomb_mesh = trimesh.util.concatenate([honeycomb_mesh, hex_cell])

        return honeycomb_mesh

    def _create_hexagonal_cell(self, cell_size: float, wall_thickness: float, center: List[float]) -> trimesh.Trimesh:
        """Create a hexagonal cell for infill."""
        # Create hexagon outline
        angles = np.linspace(0, 2*np.pi, 7)[:-1]  # 6 points
        outer_points = []

        for angle in angles:
            x = center[0] + (cell_size / 2) * np.cos(angle)
            y = center[1] + (cell_size / 2) * np.sin(angle)
            outer_points.append([x, y, center[2]])

        # Create inner hexagon for wall thickness
        inner_points = []
        inner_radius = cell_size / 2 - wall_thickness

        for angle in angles:
            x = center[0] + inner_radius * np.cos(angle)
            y = center[1] + inner_radius * np.sin(angle)
            inner_points.append([x, y, center[2]])

        # Create mesh from points
        # This is simplified - in practice would create proper 3D mesh
        return trimesh.Trimesh(vertices=outer_points + inner_points)

    def generate_large_scale_gcode(self, mesh: trimesh.Trimesh) -> str:
        """Generate G-code for large-scale printing."""
        gcode_lines = []

        # Header with large-scale parameters
        gcode_lines.append("; Large-Scale Printing G-code")
        gcode_lines.append(f"; Print Mode: {self.config.print_mode.value}")
        gcode_lines.append("G21 ; Set units to millimeters")
        gcode_lines.append("G90 ; Use absolute positioning")

        # Large-scale specific settings
        gcode_lines.append("M203 X1000 Y1000 Z500 ; Set max feedrates")
        gcode_lines.append("M201 X1000 Y1000 Z200 ; Set max acceleration")

        # Slice into large layers
        layers = self._slice_for_large_scale(mesh)

        for layer_idx, layer in enumerate(layers):
            gcode_lines.append(f"; Layer {layer_idx}")
            gcode_lines.append(f"G0 Z{layer_idx * self.config.layer_height_mm}")

            # Print layer with large-scale optimizations
            for path in layer['paths']:
                gcode_lines.append(f"G1 X{path[0]:.1f} Y{path[1]:.1f} F500")  # Slower for large structures

        # Footer
        gcode_lines.append("M107 ; Fan off")
        gcode_lines.append("G28 X Y Z ; Home all axes")

        return "\n".join(gcode_lines)

    def _slice_for_large_scale(self, mesh: trimesh.Trimesh) -> List[Dict[str, Any]]:
        """Slice mesh into layers optimized for large-scale printing."""
        layers = []

        bounds = mesh.bounds
        current_z = bounds[0][2]

        while current_z < bounds[1][2]:
            layer = {
                'z_height': current_z,
                'paths': []
            }

            # Generate simplified paths for large layers
            # In practice, would use advanced slicing algorithms
            section = mesh.section(plane_origin=[0, 0, current_z], plane_normal=[0, 0, 1])

            if section and hasattr(section, 'polygons_full'):
                for polygon in section.polygons_full:
                    if hasattr(polygon, 'exterior'):
                        coords = np.array(polygon.exterior.coords)
                        layer['paths'].append(coords)

            layers.append(layer)
            current_z += self.config.layer_height_mm

        return layers

    def estimate_print_time_and_cost(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Estimate print time and cost for large-scale project."""
        volume = mesh.volume / 1e9  # Convert to liters

        # Estimate time based on volume and layer height
        layers = (mesh.bounds[1][2] - mesh.bounds[0][2]) / self.config.layer_height_mm
        time_per_layer = 30.0  # minutes per layer for large structures
        total_time_hours = layers * time_per_layer / 60.0

        # Estimate cost based on material volume
        material_cost_per_liter = 50.0  # USD per liter (varies by material)
        total_cost = volume * material_cost_per_liter

        return {
            'estimated_time_hours': total_time_hours,
            'estimated_cost_usd': total_cost,
            'material_volume_liters': volume,
            'number_of_layers': layers,
            'recommendations': self._get_large_scale_recommendations(volume, total_time_hours)
        }

    def _get_large_scale_recommendations(self, volume: float, time_hours: float) -> List[str]:
        """Get recommendations for large-scale printing."""
        recommendations = []

        if volume > 100:  # Large volume
            recommendations.append("Consider material optimization to reduce costs")

        if time_hours > 24:  # Long print time
            recommendations.append("Plan for multi-day printing with monitoring")

        return recommendations


class ConstructionScalePrinter:
    """Advanced construction-scale 3D printing with concrete and composite materials."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.concrete_materials = self._initialize_concrete_materials()

    def _initialize_concrete_materials(self) -> Dict[str, Dict[str, Any]]:
        """Initialize concrete and composite materials for construction."""
        return {
            'recycled_concrete': {
                'name': 'Recycled Concrete',
                'compressive_strength': 30,  # MPa
                'tensile_strength': 3.5,     # MPa
                'density': 2.3,             # g/cm³
                'printability': 'high',
                'sustainability_score': 8.5,
                'cost_per_kg': 0.15,
                'curing_time_hours': 24,
                'layer_height_mm': 20
            },
            'fiber_reinforced_concrete': {
                'name': 'Fiber Reinforced Concrete',
                'compressive_strength': 45,
                'tensile_strength': 6.0,
                'density': 2.4,
                'printability': 'medium',
                'sustainability_score': 7.2,
                'cost_per_kg': 0.25,
                'curing_time_hours': 18,
                'layer_height_mm': 15
            },
            'lightweight_concrete': {
                'name': 'Lightweight Concrete',
                'compressive_strength': 20,
                'tensile_strength': 2.5,
                'density': 1.8,
                'printability': 'high',
                'sustainability_score': 9.1,
                'cost_per_kg': 0.20,
                'curing_time_hours': 20,
                'layer_height_mm': 25
            }
        }

    def prepare_construction_mesh(self, mesh: trimesh.Trimesh,
                                material_type: str = 'recycled_concrete') -> Dict[str, Any]:
        """Prepare mesh for construction-scale printing."""
        if material_type not in self.concrete_materials:
            material_type = 'recycled_concrete'

        material = self.concrete_materials[material_type]

        # Analyze structural requirements
        structural_analysis = self._analyze_structural_requirements(mesh)

        # Optimize for construction printing
        optimized_mesh = self._optimize_for_construction(mesh, material, structural_analysis)

        # Generate construction-specific G-code
        construction_gcode = self._generate_construction_gcode(optimized_mesh, material)

        return {
            'optimized_mesh': optimized_mesh,
            'material_properties': material,
            'structural_analysis': structural_analysis,
            'gcode': construction_gcode,
            'print_time_estimate': self._estimate_construction_time(optimized_mesh, material),
            'material_volume_estimate': self._estimate_material_volume(optimized_mesh, material)
        }

    def _analyze_structural_requirements(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Analyze mesh for structural integrity in construction applications."""
        analysis = {
            'load_bearing_capacity': 0.0,
            'required_reinforcements': [],
            'weak_points': [],
            'safety_factor': 1.5
        }

        try:
            # Calculate volume and surface area
            volume = mesh.volume / 1e9  # liters
            surface_area = mesh.area if hasattr(mesh, 'area') else 0

            # Estimate load bearing capacity based on geometry
            if surface_area > 0:
                volume_to_surface_ratio = volume / surface_area
                analysis['load_bearing_capacity'] = volume_to_surface_ratio * 10  # Simplified calculation

            # Identify potential weak points (overhangs, thin sections)
            bounds = mesh.bounds
            height = bounds[1][2] - bounds[0][2]

            # Check for tall structures that need reinforcement
            if height > 3000:  # 3 meters
                analysis['required_reinforcements'].append('vertical_supports')
                analysis['required_reinforcements'].append('foundation_reinforcement')

            # Check for large overhangs
            for face_idx, face in enumerate(mesh.faces):
                normal = mesh.face_normals[face_idx]
                vertical_angle = np.arccos(np.clip(np.dot(normal, [0, 0, 1]), -1, 1))
                if np.degrees(vertical_angle) > 60:  # Steep overhang
                    analysis['weak_points'].append({
                        'face_index': face_idx,
                        'angle': np.degrees(vertical_angle),
                        'recommendation': 'add_support_structure'
                    })

        except Exception as e:
            self.logger.warning(f"Structural analysis failed: {e}")

        return analysis

    def _optimize_for_construction(self, mesh: trimesh.Trimesh, material: Dict[str, Any],
                                 structural_analysis: Dict[str, Any]) -> trimesh.Trimesh:
        """Optimize mesh for construction printing."""
        optimized_mesh = mesh.copy()

        # Apply material-specific optimizations
        layer_height = material['layer_height_mm'] / 1000  # Convert to meters

        # Scale for construction scale if needed
        bounds = optimized_mesh.bounds
        max_dimension = max(bounds[1] - bounds[0])

        if max_dimension < 1000:  # Scale up for construction
            scale_factor = 2000 / max_dimension  # Scale to 2m max dimension
            optimized_mesh.apply_scale(scale_factor)

        # Add reinforcements based on structural analysis
        if 'vertical_supports' in structural_analysis['required_reinforcements']:
            optimized_mesh = self._add_vertical_supports(optimized_mesh, material)

        if 'foundation_reinforcement' in structural_analysis['required_reinforcements']:
            optimized_mesh = self._add_foundation_reinforcement(optimized_mesh, material)

        return optimized_mesh

    def _add_vertical_supports(self, mesh: trimesh.Trimesh, material: Dict[str, Any]) -> trimesh.Trimesh:
        """Add vertical support structures for tall constructions."""
        supported_mesh = mesh.copy()

        bounds = supported_mesh.bounds
        height = bounds[1][2] - bounds[0][2]

        # Add support columns at regular intervals
        support_spacing = min(height / 10, 1000)  # Max 1m spacing

        # Calculate number of supports needed
        base_area = (bounds[1][0] - bounds[0][0]) * (bounds[1][1] - bounds[0][1])
        num_supports = max(4, int(base_area / (support_spacing ** 2)))

        # Distribute supports evenly
        for i in range(int(np.sqrt(num_supports)) + 1):
            for j in range(int(np.sqrt(num_supports)) + 1):
                if i * j < num_supports:
                    x = bounds[0][0] + (bounds[1][0] - bounds[0][0]) * i / max(1, int(np.sqrt(num_supports)))
                    y = bounds[0][1] + (bounds[1][1] - bounds[0][1]) * j / max(1, int(np.sqrt(num_supports)))

                    # Create support column
                    support_column = trimesh.creation.cylinder(
                        radius=150,  # 30cm diameter
                        height=height,
                        sections=8
                    )
                    support_column.apply_translation([x, y, bounds[0][2]])

                    # Combine with main mesh
                    supported_mesh = trimesh.util.concatenate([supported_mesh, support_column])

        return supported_mesh

    def _add_foundation_reinforcement(self, mesh: trimesh.Trimesh, material: Dict[str, Any]) -> trimesh.Trimesh:
        """Add foundation reinforcement for stability."""
        reinforced_mesh = mesh.copy()

        bounds = reinforced_mesh.bounds

        # Create foundation slab
        foundation_thickness = 200  # 20cm thick
        foundation_slab = trimesh.creation.box(
            extents=[bounds[1][0] - bounds[0][0] + 400,
                    bounds[1][1] - bounds[0][1] + 400,
                    foundation_thickness]
        )

        # Position foundation
        foundation_center = [
            (bounds[0][0] + bounds[1][0]) / 2,
            (bounds[0][1] + bounds[1][1]) / 2,
            bounds[0][2] - foundation_thickness / 2
        ]
        foundation_slab.apply_translation(foundation_center)

        # Combine with main mesh
        reinforced_mesh = trimesh.util.concatenate([reinforced_mesh, foundation_slab])

        return reinforced_mesh

    def _generate_construction_gcode(self, mesh: trimesh.Trimesh, material: Dict[str, Any]) -> str:
        """Generate G-code for construction-scale printing."""
        gcode_lines = []

        # Construction-specific header
        gcode_lines.append("; Construction-Scale 3D Printing G-code")
        gcode_lines.append(f"; Material: {material['name']}")
        gcode_lines.append(f"; Layer Height: {material['layer_height_mm']}mm")
        gcode_lines.append("G21 ; Set units to millimeters")
        gcode_lines.append("G90 ; Use absolute positioning")

        # Construction-specific settings
        gcode_lines.append("M203 X500 Y500 Z200 ; Set max feedrates for concrete")
        gcode_lines.append("M201 X200 Y200 Z100 ; Set max acceleration")

        # Slice into construction layers
        layers = self._slice_for_construction(mesh, material)

        for layer_idx, layer in enumerate(layers):
            gcode_lines.append(f"; Layer {layer_idx}")
            gcode_lines.append(f"G0 Z{layer_idx * material['layer_height_mm']}")

            # Construction-specific layer printing
            for path in layer['paths']:
                gcode_lines.append(f"G1 X{path[0]:.1f} Y{path[1]:.1f} F300")  # Slow for concrete

            # Pause for layer curing if needed
            if material['curing_time_hours'] > 0:
                gcode_lines.append(f"; Pause for {material['curing_time_hours']} hours curing")
                gcode_lines.append("M0 ; Stop for manual intervention")

        # Construction footer
        gcode_lines.append("M107 ; Fan off (not used in construction)")
        gcode_lines.append("G28 X Y Z ; Home all axes")

        return "\n".join(gcode_lines)

    def _slice_for_construction(self, mesh: trimesh.Trimesh, material: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Slice mesh into layers for construction printing."""
        layers = []

        bounds = mesh.bounds
        current_z = bounds[0][2]

        while current_z < bounds[1][2]:
            layer = {
                'z_height': current_z,
                'paths': []
            }

            # Generate construction-optimized paths
            section = mesh.section(plane_origin=[0, 0, current_z], plane_normal=[0, 0, 1])

            if section and hasattr(section, 'polygons_full'):
                for polygon in section.polygons_full:
                    if hasattr(polygon, 'exterior'):
                        coords = np.array(polygon.exterior.coords)
                        layer['paths'].append(coords)

            layers.append(layer)
            current_z += material['layer_height_mm']

        return layers

    def _estimate_construction_time(self, mesh: trimesh.Trimesh, material: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate construction time including curing."""
        volume = mesh.volume / 1e9  # liters
        layers = int((mesh.bounds[1][2] - mesh.bounds[0][2]) / material['layer_height_mm'])

        # Base printing time
        time_per_layer_minutes = 45  # 45 minutes per layer for construction
        printing_time_hours = (layers * time_per_layer_minutes) / 60

        # Add curing time
        curing_time_hours = layers * material['curing_time_hours']

        total_time_hours = printing_time_hours + curing_time_hours

        return {
            'printing_time_hours': printing_time_hours,
            'curing_time_hours': curing_time_hours,
            'total_time_hours': total_time_hours,
            'layers': layers
        }

    def _estimate_material_volume(self, mesh: trimesh.Trimesh, material: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate material volume and cost for construction."""
        volume_liters = mesh.volume / 1e9
        density_kg_per_liter = material['density']

        material_mass_kg = volume_liters * density_kg_per_liter
        material_cost = material_mass_kg * material['cost_per_kg']

        return {
            'volume_liters': volume_liters,
            'mass_kg': material_mass_kg,
            'cost_usd': material_cost,
            'material_type': material['name']
        }


class IndustrialScaleOptimizer:
    """Optimization system for industrial-scale 3D printing applications."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.industrial_materials = self._initialize_industrial_materials()

    def _initialize_industrial_materials(self) -> Dict[str, Dict[str, Any]]:
        """Initialize materials for industrial applications."""
        return {
            'carbon_fiber_reinforced': {
                'name': 'Carbon Fiber Reinforced Polymer',
                'strength': 'very_high',
                'weight': 'light',
                'temperature_resistance': 200,
                'cost_per_kg': 150.0,
                'applications': ['aerospace', 'automotive', 'industrial']
            },
            'high_temperature_resistant': {
                'name': 'High Temperature Resistant Composite',
                'strength': 'high',
                'weight': 'medium',
                'temperature_resistance': 300,
                'cost_per_kg': 200.0,
                'applications': ['aerospace', 'energy', 'industrial']
            },
            'conductive_polymer': {
                'name': 'Conductive Polymer Composite',
                'strength': 'medium',
                'weight': 'light',
                'temperature_resistance': 150,
                'cost_per_kg': 120.0,
                'applications': ['electronics', 'automotive', 'industrial']
            }
        }

    def optimize_for_industrial_application(self, mesh: trimesh.Trimesh,
                                          application: str,
                                          production_volume: int) -> Dict[str, Any]:
        """Optimize mesh for specific industrial application."""
        optimization = {
            'optimized_mesh': mesh.copy(),
            'material_recommendations': [],
            'process_optimizations': [],
            'cost_analysis': {},
            'production_plan': {}
        }

        try:
            # Select optimal material for application
            optimal_material = self._select_optimal_material(application)

            # Optimize geometry for production
            optimized_mesh = self._optimize_for_production(mesh, optimal_material, production_volume)

            # Generate production plan
            production_plan = self._generate_production_plan(optimized_mesh, optimal_material, production_volume)

            # Cost analysis
            cost_analysis = self._analyze_production_costs(production_plan, optimal_material)

            optimization.update({
                'optimized_mesh': optimized_mesh,
                'material_recommendations': [optimal_material],
                'process_optimizations': self._get_process_optimizations(application),
                'cost_analysis': cost_analysis,
                'production_plan': production_plan
            })

        except Exception as e:
            self.logger.error(f"Industrial optimization failed: {e}")
            optimization['error'] = str(e)

        return optimization

    def _select_optimal_material(self, application: str) -> Dict[str, Any]:
        """Select optimal material for industrial application."""
        best_material = None
        best_score = 0

        for material_key, material in self.industrial_materials.items():
            score = 0

            # Score based on application match
            if application in material['applications']:
                score += 5

            # Score based on properties
            if material['strength'] == 'very_high':
                score += 3
            elif material['strength'] == 'high':
                score += 2

            if material['weight'] == 'light':
                score += 2

            if material['temperature_resistance'] > 200:
                score += 2

            if score > best_score:
                best_score = score
                best_material = material

        return best_material or self.industrial_materials['carbon_fiber_reinforced']

    def _optimize_for_production(self, mesh: trimesh.Trimesh,
                               material: Dict[str, Any],
                               production_volume: int) -> trimesh.Trimesh:
        """Optimize mesh for production efficiency."""
        optimized_mesh = mesh.copy()

        # Scale for production volume
        if production_volume > 100:
            # Optimize for mass production
            optimized_mesh = self._optimize_for_mass_production(optimized_mesh, material)
        else:
            # Optimize for custom/small batch
            optimized_mesh = self._optimize_for_custom_production(optimized_mesh, material)

        return optimized_mesh

    def _optimize_for_mass_production(self, mesh: trimesh.Trimesh, material: Dict[str, Any]) -> trimesh.Trimesh:
        """Optimize for mass production efficiency."""
        # Add production-oriented features
        # Reduce complexity, optimize for speed
        return mesh.copy()  # Placeholder for actual optimization

    def _optimize_for_custom_production(self, mesh: trimesh.Trimesh, material: Dict[str, Any]) -> trimesh.Trimesh:
        """Optimize for custom/small batch production."""
        # Maintain detail, optimize for quality
        return mesh.copy()  # Placeholder for actual optimization

    def _generate_production_plan(self, mesh: trimesh.Trimesh, material: Dict[str, Any],
                                production_volume: int) -> Dict[str, Any]:
        """Generate production plan for industrial application."""
        volume = mesh.volume / 1e9  # liters

        return {
            'production_volume': production_volume,
            'estimated_time_per_unit_hours': volume * 2,
            'material_per_unit_kg': volume * material.get('density', 1.2),
            'recommended_batch_size': min(production_volume, 50),
            'quality_control_points': ['pre_print', 'post_print', 'final_inspection']
        }

    def _analyze_production_costs(self, production_plan: Dict[str, Any],
                                material: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze production costs."""
        material_cost = production_plan['material_per_unit_kg'] * material['cost_per_kg']
        labor_cost = production_plan['estimated_time_per_unit_hours'] * 50  # $50/hour labor
        overhead_cost = (material_cost + labor_cost) * 0.3  # 30% overhead

        total_cost = material_cost + labor_cost + overhead_cost

        return {
            'material_cost': material_cost,
            'labor_cost': labor_cost,
            'overhead_cost': overhead_cost,
            'total_cost_per_unit': total_cost,
            'cost_breakdown_percent': {
                'material': (material_cost / total_cost) * 100,
                'labor': (labor_cost / total_cost) * 100,
                'overhead': (overhead_cost / total_cost) * 100
            }
        }

    def _get_process_optimizations(self, application: str) -> List[str]:
        """Get process optimizations for specific application."""
        optimizations = {
            'aerospace': [
                'Use certified materials only',
                'Implement strict quality control',
                'Optimize for weight reduction',
                'Include non-destructive testing'
            ],
            'automotive': [
                'Optimize for crash resistance',
                'Use automotive-grade materials',
                'Implement assembly-friendly design',
                'Include surface finish optimization'
            ],
            'industrial': [
                'Optimize for durability',
                'Use cost-effective materials',
                'Implement maintenance-friendly design',
                'Include scalability considerations'
            ]
        }

        return optimizations.get(application, ['General industrial optimizations'])
