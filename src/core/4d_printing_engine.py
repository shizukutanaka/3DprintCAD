"""4D Printing Engine for smart materials and stimulus-responsive designs.

This module enables 4D printing capabilities, allowing designs to transform
over time in response to environmental stimuli like heat, moisture, or light.
"""

from __future__ import annotations

import numpy as np
import trimesh
from typing import Dict, Any, Optional, List, Tuple, Callable
import logging
from dataclasses import dataclass, field
from enum import Enum
import time

class StimulusType(Enum):
    """Types of stimuli for 4D printing transformation."""
    THERMAL = "thermal"          # Heat-induced transformation
    HYDROLOGICAL = "hydrological"  # Moisture/water-induced
    PHOTONIC = "photonic"        # Light-induced
    CHEMICAL = "chemical"        # pH or chemical reaction
    MECHANICAL = "mechanical"    # Pressure or force
    ELECTRICAL = "electrical"    # Electric field
    MAGNETIC = "magnetic"        # Magnetic field

class TransformationType(Enum):
    """Types of shape transformations."""
    BENDING = "bending"
    FOLDING = "folding"
    CURLING = "curling"
    EXPANSION = "expansion"
    CONTRACTION = "contraction"
    TWISTING = "twisting"
    SELF_ASSEMBLY = "self_assembly"

@dataclass
class StimulusResponse:
    """Defines how a material responds to a stimulus."""
    stimulus_type: StimulusType
    trigger_threshold: float  # Temperature, humidity, etc.
    response_magnitude: float  # How much it transforms
    transformation_type: TransformationType
    response_time_seconds: float  # Time to fully transform
    reversible: bool = True

@dataclass
class SmartMaterial:
    """Properties of a smart material for 4D printing."""
    name: str
    base_mesh: trimesh.Trimesh
    responses: List[StimulusResponse] = field(default_factory=list)
    activation_energy: float = 0.0  # Energy required for transformation
    recovery_time_seconds: float = 60.0  # Time to return to original shape

class FourDPrintingEngine:
    """Engine for 4D printing simulation and transformation."""

    def __init__(self):
        self.smart_materials: Dict[str, SmartMaterial] = {}
        self.active_transformations: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def register_smart_material(self, material: SmartMaterial) -> None:
        """Register a smart material for 4D printing."""
        self.smart_materials[material.name] = material
        self.logger.info(f"Registered smart material: {material.name}")

    def simulate_transformation(self,
                               material_name: str,
                               stimulus: Dict[str, float],
                               duration_seconds: float) -> List[trimesh.Trimesh]:
        """Simulate transformation of a smart material over time.

        Args:
            material_name: Name of the registered smart material
            stimulus: Current environmental conditions (e.g., {'temperature': 25, 'humidity': 0.8})
            duration_seconds: Total simulation time

        Returns:
            List of meshes showing transformation over time
        """
        if material_name not in self.smart_materials:
            raise ValueError(f"Smart material '{material_name}' not registered")

        material = self.smart_materials[material_name]
        transformation_steps = []

        # Initial state
        current_mesh = material.base_mesh.copy()
        transformation_steps.append(current_mesh)

        # Simulate over time
        time_steps = int(duration_seconds / 10)  # 10-second intervals
        for step in range(time_steps):
            current_time = (step + 1) * 10

            # Apply transformations based on active stimuli
            transformed_mesh = self._apply_stimuli(current_mesh, material, stimulus, current_time)
            transformation_steps.append(transformed_mesh)
            current_mesh = transformed_mesh

        return transformation_steps

    def _apply_stimuli(self,
                      mesh: trimesh.Trimesh,
                      material: SmartMaterial,
                      stimulus: Dict[str, float],
                      current_time: float) -> trimesh.Trimesh:
        """Apply stimulus effects to mesh."""
        transformed_mesh = mesh.copy()

        for response in material.responses:
            # Check if stimulus threshold is met
            if self._check_stimulus_threshold(response, stimulus):
                # Apply transformation
                transformed_mesh = self._apply_transformation(
                    transformed_mesh, response, current_time
                )

        return transformed_mesh

    def _check_stimulus_threshold(self, response: StimulusResponse, stimulus: Dict[str, float]) -> bool:
        """Check if stimulus meets the threshold for transformation."""
        # Map stimulus types to values
        stimulus_values = {
            StimulusType.THERMAL: stimulus.get('temperature', 0),
            StimulusType.HYDROLOGICAL: stimulus.get('humidity', 0),
            StimulusType.PHOTONIC: stimulus.get('light_intensity', 0),
            StimulusType.CHEMICAL: stimulus.get('ph', 7.0),
            StimulusType.MECHANICAL: stimulus.get('pressure', 0),
            StimulusType.ELECTRICAL: stimulus.get('voltage', 0),
            StimulusType.MAGNETIC: stimulus.get('magnetic_field', 0),
        }

        current_value = stimulus_values.get(response.stimulus_type, 0)
        return current_value >= response.trigger_threshold

    def _apply_transformation(self,
                            mesh: trimesh.Trimesh,
                            response: StimulusResponse,
                            current_time: float) -> trimesh.Trimesh:
        """Apply specific transformation to mesh."""
        vertices = mesh.vertices.copy()

        # Apply different transformations based on type
        if response.transformation_type == TransformationType.BENDING:
            vertices = self._apply_bending(vertices, response.response_magnitude)
        elif response.transformation_type == TransformationType.EXPANSION:
            vertices = self._apply_expansion(vertices, response.response_magnitude)
        elif response.transformation_type == TransformationType.TWISTING:
            vertices = self._apply_twisting(vertices, response.response_magnitude)

        # Create new mesh
        transformed_mesh = mesh.copy()
        transformed_mesh.vertices = vertices

        return transformed_mesh

    def _apply_bending(self, vertices: np.ndarray, magnitude: float) -> np.ndarray:
        """Apply bending transformation to vertices."""
        # Simple bending along Y-axis for demonstration
        center = np.mean(vertices, axis=0)
        for i, vertex in enumerate(vertices):
            # Calculate distance from center
            distance = np.linalg.norm(vertex - center)

            # Apply bending based on Z-coordinate
            bend_factor = (vertex[2] - center[2]) * magnitude * 0.1
            vertices[i, 1] += bend_factor * distance

        return vertices

    def _apply_expansion(self, vertices: np.ndarray, magnitude: float) -> np.ndarray:
        """Apply expansion transformation."""
        center = np.mean(vertices, axis=0)
        for i, vertex in enumerate(vertices):
            direction = vertex - center
            distance = np.linalg.norm(direction)

            if distance > 0:
                # Expand outward from center
                expansion = direction / distance * magnitude * 0.01
                vertices[i] += expansion

        return vertices

    def _apply_twisting(self, vertices: np.ndarray, magnitude: float) -> np.ndarray:
        """Apply twisting transformation."""
        center = np.mean(vertices, axis=0)

        for i, vertex in enumerate(vertices):
            # Calculate angle for twisting
            dx = vertex[0] - center[0]
            dy = vertex[1] - center[1]
            angle = np.arctan2(dy, dx)

            # Apply twist based on Z-coordinate
            twist_angle = (vertex[2] - center[2]) * magnitude * 0.1
            new_angle = angle + twist_angle

            radius = np.sqrt(dx**2 + dy**2)
            vertices[i, 0] = center[0] + radius * np.cos(new_angle)
            vertices[i, 1] = center[1] + radius * np.sin(new_angle)

        return vertices

    def generate_4d_gcode(self,
                         material_name: str,
                         stimulus_sequence: List[Dict[str, float]]) -> str:
        """Generate G-code for 4D printing with stimulus control."""
        if material_name not in self.smart_materials:
            raise ValueError(f"Smart material '{material_name}' not registered")

        gcode_lines = []

        # Header
        gcode_lines.append("; 4D Printing G-code")
        gcode_lines.append(f"; Material: {material_name}")
        gcode_lines.append("G21 ; Set units to millimeters")
        gcode_lines.append("G90 ; Use absolute positioning")

        # Print base structure
        gcode_lines.append("; Print base structure")
        gcode_lines.append("M106 S255 ; Fan on for cooling")

        # Apply stimuli in sequence
        for i, stimulus in enumerate(stimulus_sequence):
            gcode_lines.append(f"; Applying stimulus {i+1}")
            self._add_stimulus_commands(gcode_lines, stimulus)

            # Wait for transformation
            wait_time = 30  # seconds
            gcode_lines.append(f"G4 P{wait_time * 1000} ; Wait for transformation")

        # Footer
        gcode_lines.append("M107 ; Fan off")
        gcode_lines.append("G28 X Y Z ; Home all axes")

        return "\n".join(gcode_lines)

    def _add_stimulus_commands(self, gcode_lines: List[str], stimulus: Dict[str, float]):
        """Add G-code commands for applying stimuli."""
        if 'temperature' in stimulus:
            gcode_lines.append(f"M104 S{stimulus['temperature']} ; Set extruder temperature")

        if 'humidity' in stimulus:
            # Simplified humidity control (would need specialized hardware)
            gcode_lines.append(f"; Set humidity to {stimulus['humidity']*100:.0f}%")

        if 'light_intensity' in stimulus:
            # Simplified light control
            intensity = min(255, int(stimulus['light_intensity'] * 255))
            gcode_lines.append(f"M106 S{intensity} ; Set light intensity")

    def validate_4d_design(self, material_name: str) -> Dict[str, Any]:
        """Validate 4D design for printability and transformation feasibility."""
        if material_name not in self.smart_materials:
            return {"valid": False, "error": "Material not registered"}

        material = self.smart_materials[material_name]

        validation = {
            "valid": True,
            "warnings": [],
            "recommendations": []
        }

        # Check mesh properties
        if material.base_mesh.volume <= 0:
            validation["valid"] = False
            validation["error"] = "Mesh must be watertight for 4D printing"

        # Check transformation feasibility
        for response in material.responses:
            if response.response_time_seconds > 300:  # 5 minutes
                validation["warnings"].append(
                    f"Long response time ({response.response_time_seconds}s) may affect print quality"
                )

        # Recommendations
        if len(material.responses) > 3:
            validation["recommendations"].append(
                "Consider simplifying stimulus responses for better predictability"
            )

        return validation
