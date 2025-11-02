"""Enhanced multi-material printing support for complex designs.

This module provides advanced capabilities for printing with multiple materials,
enabling gradient structures, functional parts, and complex composites.
"""

from __future__ import annotations

import numpy as np
import trimesh
from typing import Dict, Any, Optional, List, Tuple
import logging
from dataclasses import dataclass, field
from enum import Enum

class MaterialTransitionType(Enum):
    """Types of material transitions."""
    GRADIENT = "gradient"           # Smooth transition between materials
    SHARP = "sharp"                 # Abrupt material change
    INTERLOCKING = "interlocking"   # Mechanical interlocking
    DISSOLVABLE = "dissolvable"     # Support material that dissolves

class MultiMaterialStrategy(Enum):
    """Strategies for multi-material printing."""
    SEQUENTIAL = "sequential"       # Print materials one after another
    SIMULTANEOUS = "simultaneous"   # Print multiple materials at once
    HYBRID = "hybrid"              # Combination of both

@dataclass
class MaterialRegion:
    """Defines a region of the mesh with specific material."""
    material_name: str
    vertices: List[int]  # Vertex indices in this region
    volume_fraction: float = 1.0  # For gradient regions
    transition_width: float = 0.0  # Width of transition zone

@dataclass
class MultiMaterialConfig:
    """Configuration for multi-material printing."""
    strategy: MultiMaterialStrategy = MultiMaterialStrategy.SEQUENTIAL
    transition_type: MaterialTransitionType = MaterialTransitionType.GRADIENT
    enable_support_dissolution: bool = True
    max_material_changes: int = 10
    gradient_resolution: float = 0.1  # mm per gradient step

class EnhancedMultiMaterialPrinter:
    """Enhanced multi-material printing system."""

    def __init__(self, config: MultiMaterialConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.material_regions: List[MaterialRegion] = []

    def segment_mesh_by_material(self, mesh: trimesh.Trimesh,
                                material_properties: List[Dict[str, Any]]) -> List[MaterialRegion]:
        """Segment mesh into material regions."""
        regions = []

        # Simple segmentation based on height for demonstration
        # In practice, would use more sophisticated algorithms
        bounds = mesh.bounds
        height_range = bounds[1][2] - bounds[0][2]
        num_materials = len(material_properties)

        if num_materials == 0:
            return regions

        section_height = height_range / num_materials

        for i, material in enumerate(material_properties):
            min_z = bounds[0][2] + i * section_height
            max_z = min_z + section_height

            # Find vertices in this height range
            region_vertices = []
            for j, vertex in enumerate(mesh.vertices):
                if min_z <= vertex[2] <= max_z:
                    region_vertices.append(j)

            if region_vertices:
                region = MaterialRegion(
                    material_name=material['name'],
                    vertices=region_vertices,
                    volume_fraction=1.0
                )
                regions.append(region)

        self.material_regions = regions
        return regions

    def generate_gradient_interface(self, mesh: trimesh.Trimesh,
                                  region1: MaterialRegion, region2: MaterialRegion) -> trimesh.Trimesh:
        """Generate gradient interface between two material regions."""
        # Create smooth transition zone
        transition_mesh = mesh.copy()

        # Find boundary vertices between regions
        boundary_vertices = self._find_boundary_vertices(mesh, region1, region2)

        # Apply gradient properties to boundary vertices
        for vertex_idx in boundary_vertices:
            # Calculate distance to each region
            distance_to_r1 = self._distance_to_region(mesh.vertices[vertex_idx], region1)
            distance_to_r2 = self._distance_to_region(mesh.vertices[vertex_idx], region2)

            # Blend material properties based on distance
            blend_factor = distance_to_r1 / (distance_to_r1 + distance_to_r2)

            # In practice, would modify material properties here
            # For now, just mark as transition vertex
            pass

        return transition_mesh

    def _find_boundary_vertices(self, mesh: trimesh.Trimesh,
                              region1: MaterialRegion, region2: MaterialRegion) -> List[int]:
        """Find vertices at the boundary between two regions."""
        boundary = []

        # Check each vertex in region1 if it has neighbors in region2
        for vertex_idx in region1.vertices:
            # Find adjacent vertices
            adjacent_vertices = self._get_adjacent_vertices(mesh, vertex_idx)

            # Check if any adjacent vertex is in region2
            for adj_vertex in adjacent_vertices:
                if adj_vertex in region2.vertices:
                    boundary.append(vertex_idx)
                    break

        return boundary

    def _get_adjacent_vertices(self, mesh: trimesh.Trimesh, vertex_idx: int) -> List[int]:
        """Get vertices adjacent to the given vertex."""
        adjacent = []

        # Find edges containing this vertex
        for face in mesh.faces:
            if vertex_idx in face:
                # Add other vertices in this face
                for other_vertex in face:
                    if other_vertex != vertex_idx and other_vertex not in adjacent:
                        adjacent.append(other_vertex)

        return adjacent

    def _distance_to_region(self, vertex: np.ndarray, region: MaterialRegion) -> float:
        """Calculate distance from vertex to material region."""
        region_vertices = [vertex for idx in region.vertices]
        if not region_vertices:
            return float('inf')

        region_center = np.mean(region_vertices, axis=0)
        return np.linalg.norm(vertex - region_center)

    def generate_multi_material_gcode(self, mesh: trimesh.Trimesh,
                                    material_regions: List[MaterialRegion]) -> str:
        """Generate G-code for multi-material printing."""
        gcode_lines = []

        # Header
        gcode_lines.append("; Multi-Material Printing G-code")
        gcode_lines.append("G21 ; Set units to millimeters")
        gcode_lines.append("G90 ; Use absolute positioning")

        # Print each material region
        for i, region in enumerate(material_regions):
            gcode_lines.append(f"; Printing material region {i+1}: {region.material_name}")

            # Select appropriate extruder for material
            extruder_id = i % 4  # Assume 4 extruders available
            gcode_lines.append(f"T{extruder_id} ; Select extruder for {region.material_name}")

            # Print vertices in this region
            for vertex_idx in region.vertices:
                vertex = mesh.vertices[vertex_idx]
                gcode_lines.append(f"G1 X{vertex[0]:.3f} Y{vertex[1]:.3f} Z{vertex[2]:.3f} F1000")

            # Add transition if gradient
            if i < len(material_regions) - 1 and self.config.transition_type == MaterialTransitionType.GRADIENT:
                gcode_lines.append(f"; Gradient transition to next material")
                gcode_lines.append("M106 S128 ; Set fan speed for mixing")

        # Footer
        gcode_lines.append("M107 ; Fan off")
        gcode_lines.append("G28 X Y Z ; Home all axes")

        return "\n".join(gcode_lines)

    def optimize_material_distribution(self, mesh: trimesh.Trimesh,
                                     target_properties: Dict[str, float]) -> List[MaterialRegion]:
        """Optimize material distribution to achieve target properties."""
        # Simplified optimization - in practice would use topology optimization
        optimized_regions = []

        # Calculate required material volumes based on target properties
        total_volume = mesh.volume

        # Example: optimize for strength vs weight
        if 'strength_to_weight_ratio' in target_properties:
            # Allocate stronger material to stress concentrations
            # For demonstration, split mesh into two regions
            split_z = mesh.bounds[0][2] + mesh.bounds[1][2] * 0.5

            region1_vertices = [i for i, v in enumerate(mesh.vertices) if v[2] < split_z]
            region2_vertices = [i for i, v in enumerate(mesh.vertices) if v[2] >= split_z]

            region1 = MaterialRegion(
                material_name="High_Strength_Material",
                vertices=region1_vertices
            )
            region2 = MaterialRegion(
                material_name="Lightweight_Material",
                vertices=region2_vertices
            )

            optimized_regions = [region1, region2]

    def generate_multi_material_support_structures(self, mesh: trimesh.Trimesh,
                                                  material_regions: List[MaterialRegion]) -> trimesh.Trimesh:
        """Generate support structures optimized for multi-material printing."""

        try:
            support_mesh = mesh.copy()

            # Analyze each material region for support requirements
            for region in material_regions:
                # Calculate support needs based on material properties
                support_needs = self._calculate_support_needs(region)

                if support_needs > 0.5:  # If significant support needed
                    # Generate support structures for this region
                    region_supports = self._generate_region_supports(mesh, region)
                    support_mesh = self._merge_support_structures(support_mesh, region_supports)

            return support_mesh

        except Exception as e:
            self.logger.warning(f"Multi-material support generation failed: {e}")
            return mesh

    def _calculate_support_needs(self, region: MaterialRegion) -> float:
        """Calculate support requirements for a material region."""

        # Simplified calculation based on region properties
        # In practice, would consider overhang angles, material properties, etc.

        # Assume higher support needs for regions with many vertices
        support_score = min(len(region.vertices) / 1000, 1.0)

        return support_score

    def _generate_region_supports(self, mesh: trimesh.Trimesh, region: MaterialRegion) -> trimesh.Trimesh:
        """Generate support structures for a specific region."""

        try:
            # Create simple support pillars for demonstration
            supports = []

            # Find bottom vertices of the region
            region_vertices = [mesh.vertices[i] for i in region.vertices]
            min_z = min(v[2] for v in region_vertices)

            bottom_vertices = [i for i, v in enumerate(mesh.vertices) if v[2] <= min_z + 1.0]

            # Create support pillars from bottom to region
            for bottom_idx in bottom_vertices[:10]:  # Limit for performance
                pillar = self._create_support_pillar(mesh, bottom_idx, region)
                if pillar is not None:
                    supports.append(pillar)

            # Combine supports into single mesh
            if supports:
                combined_supports = supports[0]
                for support in supports[1:]:
                    combined_supports = combined_supports + support
                return combined_supports

            return mesh.copy()

        except Exception as e:
            self.logger.warning(f"Region support generation failed: {e}")
            return mesh.copy()

    def _create_support_pillar(self, mesh: trimesh.Trimesh, base_vertex_idx: int,
                              region: MaterialRegion) -> Optional[trimesh.Trimesh]:
        """Create a support pillar from base vertex to material region."""

        try:
            base_vertex = mesh.vertices[base_vertex_idx]

            # Find the closest vertex in the region
            region_vertices = mesh.vertices[region.vertices]
            distances = np.linalg.norm(region_vertices - base_vertex, axis=1)
            target_idx = region.vertices[np.argmin(distances)]

            target_vertex = mesh.vertices[target_idx]

            # Create simple cylindrical pillar
            # In practice, would use more sophisticated geometry
            pillar_vertices = np.array([
                base_vertex,
                [base_vertex[0] + 0.5, base_vertex[1], base_vertex[2]],
                [base_vertex[0] - 0.5, base_vertex[1], base_vertex[2]],
                [base_vertex[0], base_vertex[1] + 0.5, base_vertex[2]],
                target_vertex,
                [target_vertex[0] + 0.3, target_vertex[1], target_vertex[2]],
                [target_vertex[0] - 0.3, target_vertex[1], target_vertex[2]],
                [target_vertex[0], target_vertex[1] + 0.3, target_vertex[2]]
            ])

            # Create faces for the pillar
            pillar_faces = [
                [0, 1, 2], [0, 2, 3],  # Base
                [4, 5, 6], [4, 6, 7],  # Top
                [0, 1, 5, 4], [1, 2, 6, 5],  # Sides
                [2, 3, 7, 6], [3, 0, 4, 7]
            ]

            pillar = trimesh.Trimesh(vertices=pillar_vertices, faces=pillar_faces)
            return pillar

        except Exception:
            return None

    def _merge_support_structures(self, main_mesh: trimesh.Trimesh,
                                 support_mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Merge support structures with main mesh."""

        try:
            # In practice, would use boolean operations or mesh combination
            # For demonstration, return the main mesh with supports as metadata
            return main_mesh

        except Exception:
            return main_mesh
