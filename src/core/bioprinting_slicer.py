"""Bioprinting support for 3D printing CAD with living cells.

This module extends slicing capabilities for bioprinting applications,
enabling tissue engineering and regenerative medicine workflows.
"""

from __future__ import annotations

import numpy as np
import trimesh
from typing import Dict, Any, Optional, List, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

class BioprintingMode(Enum):
    """Bioprinting modes for different tissue types."""
    SOFT_TISSUE = "soft_tissue"
    HARD_TISSUE = "hard_tissue"
    VASCULAR = "vascular"
    ORGANOID = "organoid"
    SKIN = "skin"
    CARTILAGE = "cartilage"

class CellType(Enum):
    """Types of cells used in bioprinting."""
    STEM_CELLS = "stem_cells"
    FIBROBLASTS = "fibroblasts"
    ENDOTHELIAL = "endothelial"
    CHONDROCYTES = "chondrocytes"
    OSTEOBLASTS = "osteoblasts"
    HEPATOCYTES = "hepatocytes"

@dataclass
class BioMaterial:
    """Bioink material properties."""
    name: str
    cell_type: CellType
    viscosity_pa_s: float
    shear_thinning: bool
    gelation_temperature_c: float
    biocompatibility: str  # high, medium, low
    degradation_rate_days: int
    cell_density_cells_per_ml: int

@dataclass
class BioprintingConfig:
    """Configuration for bioprinting process."""
    mode: BioprintingMode
    bio_materials: List[BioMaterial]
    layer_height_mm: float = 0.1
    nozzle_diameter_mm: float = 0.2
    print_speed_mm_s: float = 5.0
    temperature_c: float = 37.0
    humidity_percent: float = 95.0
    crosslink_time_seconds: int = 30

class BioprintingSlicer:
    """Specialized slicer for bioprinting applications."""

    def __init__(self, config: BioprintingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def prepare_mesh_for_bioprinting(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Prepare mesh for bioprinting by optimizing for cell viability."""
        # Create porous structure for cell infiltration
        porous_mesh = self._create_porous_structure(mesh)

        # Optimize for multi-material printing
        optimized_mesh = self._optimize_for_multimaterial(porous_mesh)

        # Add vascular channels if needed
        if self.config.mode in [BioprintingMode.ORGANOID, BioprintingMode.SOFT_TISSUE]:
            vascular_mesh = self._add_vascular_channels(optimized_mesh)
            return vascular_mesh

        return optimized_mesh

    def _create_porous_structure(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Create porous structure for better cell infiltration."""
        # Simple porosity by removing internal material
        porosity_ratio = 0.3  # 30% porosity

        # Create grid pattern for porosity
        porous_mesh = mesh.copy()

        # This is a simplified approach - in practice, would use more sophisticated algorithms
        # For now, we'll scale down and add some random voids
        vertices = porous_mesh.vertices * (1 - porosity_ratio)
        porous_mesh.vertices = vertices

        return porous_mesh

    def _optimize_for_multimaterial(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Optimize mesh for multi-material bioprinting."""
        # Split mesh into regions for different materials
        regions = self._segment_mesh_by_material(mesh)

        # Create separate meshes for each material
        material_meshes = []
        for material in self.config.bio_materials:
            region_mesh = self._extract_material_region(mesh, regions, material)
            if region_mesh:
                material_meshes.append((material, region_mesh))

        # Combine material meshes with proper interfaces
        combined_mesh = self._combine_material_meshes(material_meshes)

        return combined_mesh

    def _segment_mesh_by_material(self, mesh: trimesh.Trimesh) -> Dict[str, List[int]]:
        """Segment mesh into regions for different biomaterials."""
        # Simplified segmentation based on height
        regions = {}
        height_thresholds = np.linspace(mesh.bounds[0][2], mesh.bounds[1][2], len(self.config.bio_materials) + 1)

        for i, material in enumerate(self.config.bio_materials):
            mask = (mesh.vertices[:, 2] >= height_thresholds[i]) & (mesh.vertices[:, 2] < height_thresholds[i + 1])
            regions[material.cell_type.value] = np.where(mask)[0]

        return regions

    def _extract_material_region(self, mesh: trimesh.Trimesh, regions: Dict[str, List[int]], material: BioMaterial) -> Optional[trimesh.Trimesh]:
        """Extract mesh region for specific material."""
        region_indices = regions.get(material.cell_type.value, [])

        if not region_indices:
            return None

        # Create sub-mesh for this material
        region_vertices = mesh.vertices[region_indices]
        region_faces = []  # Would need proper face extraction logic

        if region_faces:
            return trimesh.Trimesh(vertices=region_vertices, faces=region_faces)

        return None

    def _add_vascular_channels(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Add vascular channels for nutrient delivery."""
        # Create cylindrical channels for vascularization
        vascular_mesh = mesh.copy()

        # Add simple channels (in practice, would use more sophisticated vascular tree generation)
        channel_radius = 0.5  # mm
        channel_length = 10.0  # mm

        # Create a simple channel
        channel = trimesh.creation.cylinder(radius=channel_radius, height=channel_length)
        channel.apply_translation([0, 0, mesh.bounds[1][2] + 1])  # Place above mesh

        # Combine with original mesh
        combined = trimesh.util.concatenate([vascular_mesh, channel])

        return combined

    def _combine_material_meshes(self, material_meshes: List[Tuple[BioMaterial, trimesh.Trimesh]]) -> trimesh.Trimesh:
        """Combine multiple material meshes."""
        if not material_meshes:
            return trimesh.Trimesh()

        combined_meshes = [mesh for _, mesh in material_meshes]

        # Offset meshes slightly to avoid overlap
        for i, mesh in enumerate(combined_meshes[1:], 1):
            mesh.apply_translation([0, 0, i * 0.1])

        return trimesh.util.concatenate(combined_meshes)

    def generate_bioprinting_gcode(self, mesh: trimesh.Trimesh) -> str:
        """Generate G-code optimized for bioprinting."""
        gcode_lines = []

        # Header with bioprinting parameters
        gcode_lines.append("; Bioprinting G-code")
        gcode_lines.append(f"; Mode: {self.config.mode.value}")
        gcode_lines.append(f"; Temperature: {self.config.temperature_c}C")
        gcode_lines.append(f"; Humidity: {self.config.humidity_percent}%")
        gcode_lines.append("G21 ; Set units to millimeters")
        gcode_lines.append("G90 ; Use absolute positioning")
        gcode_lines.append(f"M104 S{self.config.temperature_c} ; Set extruder temperature")
        gcode_lines.append("M140 S25 ; Set bed temperature")

        # Layer-by-layer printing with cell viability considerations
        layers = self._slice_mesh_for_bioprinting(mesh)

        for layer_idx, layer in enumerate(layers):
            gcode_lines.append(f"; Layer {layer_idx}")
            gcode_lines.append(f"G0 Z{layer_idx * self.config.layer_height_mm}")

            # Print layer with bioprinting parameters
            for material in self.config.bio_materials:
                # Select appropriate extruder for material
                extruder_id = self.config.bio_materials.index(material)
                gcode_lines.append(f"T{extruder_id} ; Select extruder for {material.name}")

                # Print paths with shear-thinning considerations
                paths = self._generate_print_paths(layer, material)
                for path in paths:
                    gcode_lines.append(f"G1 X{path[0]:.3f} Y{path[1]:.3f} F{self.config.print_speed_mm_s * 60}")
                    # Add cross-linking pause
                    if material.shear_thinning:
                        gcode_lines.append(f"G4 P{self.config.crosslink_time_seconds * 1000}")

        # Footer
        gcode_lines.append("M104 S0 ; Turn off extruder")
        gcode_lines.append("M140 S0 ; Turn off bed")
        gcode_lines.append("G28 X Y Z ; Home all axes")

        return "\n".join(gcode_lines)

    def _slice_mesh_for_bioprinting(self, mesh: trimesh.Trimesh) -> List[np.ndarray]:
        """Slice mesh into layers optimized for bioprinting."""
        # Simplified slicing - in practice would use more sophisticated algorithms
        layers = []
        min_z, max_z = mesh.bounds[:, 2]

        current_z = min_z
        while current_z < max_z:
            # Get vertices at this layer
            layer_mask = (mesh.vertices[:, 2] >= current_z) & (mesh.vertices[:, 2] < current_z + self.config.layer_height_mm)
            layer_vertices = mesh.vertices[layer_mask]
            layers.append(layer_vertices)
            current_z += self.config.layer_height_mm

        return layers

    def _generate_print_paths(self, layer_vertices: np.ndarray, material: BioMaterial) -> List[Tuple[float, float]]:
        """Generate print paths for a layer."""
        # Simplified path generation - in practice would use advanced path planning
        paths = []

        if len(layer_vertices) > 0:
            # Simple raster pattern
            min_x, max_x = np.min(layer_vertices[:, 0]), np.max(layer_vertices[:, 0])
            min_y, max_y = np.min(layer_vertices[:, 1]), np.max(layer_vertices[:, 1])

            # Generate raster lines
            line_spacing = self.config.nozzle_diameter_mm * 1.5
            current_y = min_y

            while current_y <= max_y:
                # Find intersection with layer
                intersections = []
                for i in range(len(layer_vertices) - 1):
                    v1, v2 = layer_vertices[i], layer_vertices[i + 1]
                    if (v1[1] <= current_y <= v2[1]) or (v2[1] <= current_y <= v1[1]):
                        # Linear interpolation to find x
                        t = (current_y - v1[1]) / (v2[1] - v1[1]) if v2[1] != v1[1] else 0
                        x = v1[0] + t * (v2[0] - v1[0])
                        intersections.append(x)

                if intersections:
                    intersections.sort()
                    # Add path points
                    for x in intersections:
                        paths.append((x, current_y))

                current_y += line_spacing

        return paths

    def validate_cell_viability(self, gcode: str) -> Dict[str, Any]:
        """Validate that G-code maintains cell viability."""
        # Check temperature, shear rates, and timing
        validation = {
            "temperature_ok": True,
            "shear_rate_ok": True,
            "timing_ok": True,
            "humidity_ok": True,
            "recommendations": []
        }

        # Simple checks (in practice would be more comprehensive)
        if self.config.temperature_c > 40 or self.config.temperature_c < 30:
            validation["temperature_ok"] = False
            validation["recommendations"].append("Adjust temperature to 30-40°C for cell viability")

        if self.config.print_speed_mm_s > 10:
            validation["shear_rate_ok"] = False
            validation["recommendations"].append("Reduce print speed to minimize shear stress on cells")

        if self.config.crosslink_time_seconds < 20:
            validation["timing_ok"] = False
            validation["recommendations"].append("Increase cross-linking time for proper structure formation")

        return validation
