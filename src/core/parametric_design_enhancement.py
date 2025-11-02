"""Enhanced parametric design tools for rule-based 3D modeling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union, Callable
import numpy as np
import trimesh
from enum import Enum
import logging
import math
import copy


class ParametricOperation(Enum):
    """Types of parametric operations."""
    EXTRUDE = "extrude"
    REVOLVE = "revolve"
    LOFT = "loft"
    SWEEP = "sweep"
    FILLET = "fillet"
    CHAMFER = "chamfer"
    PATTERN = "pattern"
    MIRROR = "mirror"
    BOOLEAN_UNION = "boolean_union"
    BOOLEAN_DIFFERENCE = "boolean_difference"
    BOOLEAN_INTERSECTION = "boolean_intersection"
    OFFSET = "offset"
    SHELL = "shell"


class ConstraintType(Enum):
    """Types of geometric constraints."""
    DISTANCE = "distance"
    ANGLE = "angle"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    COINCIDENT = "coincident"
    CONCENTRIC = "concentric"
    EQUAL = "equal"
    SYMMETRIC = "symmetric"


@dataclass
class ParametricParameter:
    """A parameter in the parametric design system."""

    name: str
    value: Union[float, int, str, bool]
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    description: str = ""
    unit: str = ""  # mm, degrees, etc.


@dataclass
class GeometricConstraint:
    """A geometric constraint between design elements."""

    constraint_type: ConstraintType
    elements: List[str]  # Element IDs
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # Higher priority constraints are satisfied first


@dataclass
class ParametricFeature:
    """A parametric feature in the design."""

    id: str
    operation: ParametricOperation
    parameters: Dict[str, ParametricParameter] = field(default_factory=dict)
    base_geometry: Optional[trimesh.Trimesh] = None
    parent_id: Optional[str] = None  # Parent feature ID
    constraints: List[GeometricConstraint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParametricDesign:
    """Complete parametric design with features and constraints."""

    name: str
    features: List[ParametricFeature] = field(default_factory=list)
    global_parameters: Dict[str, ParametricParameter] = field(default_factory=dict)
    constraints: List[GeometricConstraint] = field(default_factory=list)
    design_tree: Dict[str, List[str]] = field(default_factory=dict)  # Parent -> children mapping


class EnhancedParametricDesigner:
    """Enhanced parametric design system with advanced features."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.designs: Dict[str, ParametricDesign] = {}

    def create_design(self, name: str) -> ParametricDesign:
        """Create a new parametric design."""

        design = ParametricDesign(name=name)

        # Add common global parameters
        design.global_parameters = {
            "length": ParametricParameter("length", 100.0, 1.0, 1000.0, 1.0, "Overall length", "mm"),
            "width": ParametricParameter("width", 50.0, 1.0, 500.0, 1.0, "Overall width", "mm"),
            "height": ParametricParameter("height", 30.0, 1.0, 300.0, 1.0, "Overall height", "mm"),
            "wall_thickness": ParametricParameter("wall_thickness", 2.0, 0.5, 10.0, 0.1, "Wall thickness", "mm"),
            "fillet_radius": ParametricParameter("fillet_radius", 3.0, 0.1, 20.0, 0.1, "Fillet radius", "mm"),
        }

        self.designs[name] = design
        return design

    def add_parametric_feature(self, design: ParametricDesign,
                             operation: ParametricOperation,
                             parameters: Dict[str, Any],
                             base_geometry: Optional[trimesh.Trimesh] = None,
                             parent_id: Optional[str] = None) -> ParametricFeature:
        """Add a parametric feature to the design."""

        feature_id = f"{operation.value}_{len(design.features)}"

        # Convert parameters to ParametricParameter objects
        param_objects = {}
        for key, value in parameters.items():
            param_objects[key] = ParametricParameter(
                name=key,
                value=value,
                description=f"Parameter for {operation.value}"
            )

        feature = ParametricFeature(
            id=feature_id,
            operation=operation,
            parameters=param_objects,
            base_geometry=base_geometry,
            parent_id=parent_id
        )

        design.features.append(feature)

        # Update design tree
        if parent_id:
            if parent_id not in design.design_tree:
                design.design_tree[parent_id] = []
            design.design_tree[parent_id].append(feature_id)
        else:
            if "root" not in design.design_tree:
                design.design_tree["root"] = []
            design.design_tree["root"].append(feature_id)

        return feature

    def regenerate_design(self, design: ParametricDesign) -> trimesh.Trimesh:
        """Regenerate the complete 3D model from parametric design."""

        try:
            # Process features in topological order
            processed_features = {}
            result_mesh = None

            # Get root features
            root_features = design.design_tree.get("root", [])

            for feature_id in root_features:
                mesh = self._regenerate_feature(design, feature_id, processed_features)
                if mesh:
                    if result_mesh is None:
                        result_mesh = mesh
                    else:
                        result_mesh = trimesh.boolean.union([result_mesh, mesh])

            # Apply global constraints
            if result_mesh and design.constraints:
                result_mesh = self._apply_constraints(result_mesh, design.constraints)

            return result_mesh if result_mesh else trimesh.Trimesh()

        except Exception as e:
            self.logger.error(f"Error regenerating design: {e}")
            return trimesh.Trimesh()

    def _regenerate_feature(self, design: ParametricDesign,
                          feature_id: str,
                          processed_features: Dict[str, trimesh.Trimesh]) -> Optional[trimesh.Trimesh]:
        """Regenerate a single feature and its children."""

        if feature_id in processed_features:
            return processed_features[feature_id]

        # Find the feature
        feature = None
        for f in design.features:
            if f.id == feature_id:
                feature = f
                break

        if not feature:
            return None

        # Process parent first if it exists
        parent_mesh = None
        if feature.parent_id:
            parent_mesh = self._regenerate_feature(design, feature.parent_id, processed_features)

        # Generate this feature
        mesh = self._generate_feature_mesh(feature, parent_mesh)

        # Process children
        children = design.design_tree.get(feature_id, [])
        for child_id in children:
            child_mesh = self._regenerate_feature(design, child_id, processed_features)
            if child_mesh and mesh:
                # Apply child operation to parent
                mesh = self._apply_child_operation(mesh, child_mesh, feature)

        processed_features[feature_id] = mesh
        return mesh

    def _generate_feature_mesh(self, feature: ParametricFeature,
                             parent_mesh: Optional[trimesh.Trimesh]) -> Optional[trimesh.Trimesh]:
        """Generate mesh for a single feature."""

        try:
            if feature.operation == ParametricOperation.EXTRUDE:
                return self._create_extrusion(feature, parent_mesh)
            elif feature.operation == ParametricOperation.REVOLVE:
                return self._create_revolution(feature, parent_mesh)
            elif feature.operation == ParametricOperation.LOFT:
                return self._create_loft(feature, parent_mesh)
            elif feature.operation == ParametricOperation.FILLET:
                return self._apply_fillet(feature, parent_mesh)
            elif feature.operation == ParametricOperation.CHAMFER:
                return self._apply_chamfer(feature, parent_mesh)
            elif feature.operation == ParametricOperation.PATTERN:
                return self._create_pattern(feature, parent_mesh)
            elif feature.operation == ParametricOperation.BOOLEAN_UNION:
                return self._apply_boolean_union(feature, parent_mesh)
            elif feature.operation == ParametricOperation.BOOLEAN_DIFFERENCE:
                return self._apply_boolean_difference(feature, parent_mesh)
            elif feature.operation == ParametricOperation.SHELL:
                return self._apply_shell(feature, parent_mesh)
            else:
                self.logger.warning(f"Unsupported operation: {feature.operation.value}")
                return parent_mesh

        except Exception as e:
            self.logger.error(f"Error generating feature mesh for {feature.id}: {e}")
            return parent_mesh

    def _create_extrusion(self, feature: ParametricFeature,
                         base_geometry: Optional[trimesh.Trimesh]) -> trimesh.Trimesh:
        """Create an extruded feature."""

        # Get parameters
        profile = feature.parameters.get("profile")
        height = feature.parameters.get("height", ParametricParameter("height", 10.0)).value

        if not profile or not hasattr(profile, 'value'):
            # Create a default rectangular profile
            width = feature.parameters.get("width", ParametricParameter("width", 20.0)).value
            length = feature.parameters.get("length", ParametricParameter("length", 30.0)).value

            # Create rectangular profile
            profile_points = np.array([
                [0, 0, 0],
                [width, 0, 0],
                [width, length, 0],
                [0, length, 0]
            ])
            faces = [[0, 1, 2], [0, 2, 3]]
            profile_mesh = trimesh.Trimesh(vertices=profile_points, faces=faces)
        else:
            profile_mesh = profile.value

        # Extrude the profile
        extruded = profile_mesh.extrude(height)

        return extruded

    def _create_revolution(self, feature: ParametricFeature,
                         base_geometry: Optional[trimesh.Trimesh]) -> trimesh.Trimesh:
        """Create a revolved feature."""

        # Get parameters
        profile = feature.parameters.get("profile")
        angle = feature.parameters.get("angle", ParametricParameter("angle", 360.0)).value

        if not profile or not hasattr(profile, 'value'):
            # Create a default semicircular profile
            radius = feature.parameters.get("radius", ParametricParameter("radius", 10.0)).value
            height = feature.parameters.get("height", ParametricParameter("height", 20.0)).value

            # Create semicircular profile
            theta = np.linspace(0, np.pi, 10)
            x = radius * np.cos(theta)
            y = np.zeros_like(theta)
            z = radius * np.sin(theta) + height/2

            profile_points = np.column_stack([x, y, z])
            profile_mesh = trimesh.Trimesh(vertices=profile_points, faces=[])
        else:
            profile_mesh = profile.value

        # Revolve around Y axis
        revolved = trimesh.creation.revolve(profile_mesh.vertices,
                                          angle=np.radians(angle),
                                          sections=32)

        return revolved

    def _create_loft(self, feature: ParametricFeature,
                   base_geometry: Optional[trimesh.Trimesh]) -> trimesh.Trimesh:
        """Create a lofted feature between multiple profiles."""

        # Simplified loft implementation
        # In practice, this would use multiple cross-sections
        profiles = feature.parameters.get("profiles")

        if not profiles or len(profiles.value) < 2:
            # Create simple tapered shape
            bottom_radius = feature.parameters.get("bottom_radius", ParametricParameter("bottom_radius", 10.0)).value
            top_radius = feature.parameters.get("top_radius", ParametricParameter("top_radius", 5.0)).value
            height = feature.parameters.get("height", ParametricParameter("height", 20.0)).value

            # Create cone
            cone = trimesh.creation.cone(radius=top_radius, height=height)
            return cone

        # Use trimesh loft if available
        try:
            lofted = trimesh.creation.loft(profiles.value)
            return lofted
        except Exception:
            # Fallback to simple shape
            return trimesh.creation.box(extents=[10, 10, 10])

    def _apply_fillet(self, feature: ParametricFeature,
                    base_mesh: Optional[trimesh.Trimesh]) -> Optional[trimesh.Trimesh]:
        """Apply fillet to edges."""

        if not base_mesh:
            return None

        # Simplified fillet implementation
        radius = feature.parameters.get("radius", ParametricParameter("radius", 2.0)).value

        try:
            # Use trimesh's fillet if available, otherwise return original
            filleted = base_mesh.copy()
            # Note: Real fillet implementation would be complex
            return filleted
        except Exception:
            return base_mesh

    def _apply_chamfer(self, feature: ParametricFeature,
                     base_mesh: Optional[trimesh.Trimesh]) -> Optional[trimesh.Trimesh]:
        """Apply chamfer to edges."""

        if not base_mesh:
            return None

        # Simplified chamfer implementation
        distance = feature.parameters.get("distance", ParametricParameter("distance", 2.0)).value

        try:
            # Note: Real chamfer implementation would be complex
            return base_mesh
        except Exception:
            return base_mesh

    def _create_pattern(self, feature: ParametricFeature,
                      base_geometry: Optional[trimesh.Trimesh]) -> Optional[trimesh.Trimesh]:
        """Create a patterned feature."""

        if not base_geometry:
            return None

        # Get pattern parameters
        count_x = feature.parameters.get("count_x", ParametricParameter("count_x", 3)).value
        count_y = feature.parameters.get("count_y", ParametricParameter("count_y", 3)).value
        spacing_x = feature.parameters.get("spacing_x", ParametricParameter("spacing_x", 15.0)).value
        spacing_y = feature.parameters.get("spacing_y", ParametricParameter("spacing_y", 15.0)).value

        try:
            pattern_meshes = []

            for i in range(count_x):
                for j in range(count_y):
                    # Skip center if it's the base geometry
                    if i == count_x // 2 and j == count_y // 2:
                        pattern_meshes.append(base_geometry)
                        continue

                    # Create translated copy
                    translated = base_geometry.copy()
                    translated.apply_translation([
                        (i - count_x // 2) * spacing_x,
                        (j - count_y // 2) * spacing_y,
                        0
                    ])
                    pattern_meshes.append(translated)

            # Combine all instances
            if pattern_meshes:
                combined = trimesh.util.concatenate(pattern_meshes)
                return combined

        except Exception as e:
            self.logger.error(f"Error creating pattern: {e}")

        return base_geometry

    def _apply_boolean_union(self, feature: ParametricFeature,
                           base_mesh: Optional[trimesh.Trimesh]) -> Optional[trimesh.Trimesh]:
        """Apply boolean union operation."""

        tool_mesh = feature.base_geometry
        if not base_mesh or not tool_mesh:
            return base_mesh

        try:
            result = trimesh.boolean.union([base_mesh, tool_mesh])
            return result
        except Exception:
            return base_mesh

    def _apply_boolean_difference(self, feature: ParametricFeature,
                                base_mesh: Optional[trimesh.Trimesh]) -> Optional[trimesh.Trimesh]:
        """Apply boolean difference operation."""

        tool_mesh = feature.base_geometry
        if not base_mesh or not tool_mesh:
            return base_mesh

        try:
            result = trimesh.boolean.difference([base_mesh, tool_mesh])
            return result
        except Exception:
            return base_mesh

    def _apply_shell(self, feature: ParametricFeature,
                   base_mesh: Optional[trimesh.Trimesh]) -> Optional[trimesh.Trimesh]:
        """Apply shell operation to create hollow shape."""

        if not base_mesh:
            return None

        thickness = feature.parameters.get("thickness", ParametricParameter("thickness", 2.0)).value

        try:
            # Create offset surface inward
            offset_distance = -thickness

            # Use trimesh's offset if available
            shelled = base_mesh.copy()
            # Note: Real shell implementation would be complex
            return shelled

        except Exception:
            return base_mesh

    def _apply_child_operation(self, parent_mesh: trimesh.Trimesh,
                             child_mesh: trimesh.Trimesh,
                             parent_feature: ParametricFeature) -> trimesh.Trimesh:
        """Apply child feature operation to parent mesh."""

        try:
            # Default to union for most operations
            result = trimesh.boolean.union([parent_mesh, child_mesh])
            return result
        except Exception:
            return parent_mesh

    def _apply_constraints(self, mesh: trimesh.Trimesh,
                         constraints: List[GeometricConstraint]) -> trimesh.Trimesh:
        """Apply geometric constraints to the mesh."""

        # Constraint application is complex and would require
        # sophisticated geometric constraint solving
        # For now, return the mesh unchanged
        return mesh

    def optimize_parameters(self, design: ParametricDesign,
                          target_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize design parameters based on target criteria."""

        # This would implement parameter optimization algorithms
        # For now, return current parameters

        optimized_params = {}
        for param_name, param in design.global_parameters.items():
            optimized_params[param_name] = param.value

        return optimized_params

    def export_design_to_script(self, design: ParametricDesign, file_path: str) -> bool:
        """Export parametric design to a Python script for reproducibility."""

        try:
            script_lines = [
                "#!/usr/bin/env python3",
                '"""',
                f"Parametric design: {design.name}",
                'Generated by 3D Print CAD Assistant',
                '"""',
                "",
                "from enhanced_parametric_designer import EnhancedParametricDesigner",
                "import trimesh",
                "import numpy as np",
                "",
                "# Create designer instance",
                "designer = EnhancedParametricDesigner()",
                "",
                f"# Create design: {design.name}",
                f"design = designer.create_design('{design.name}')",
                "",
                "# Set global parameters"
            ]

            # Add global parameters
            for param_name, param in design.global_parameters.items():
                script_lines.append(f"design.global_parameters['{param_name}'].value = {param.value}")

            script_lines.append("")
            script_lines.append("# Add features")

            # Add features
            for feature in design.features:
                script_lines.append(f"# Feature: {feature.id}")
                params_str = ", ".join([f"{k}={v.value}" for k, v in feature.parameters.items()])
                script_lines.append(f"designer.add_parametric_feature(design, ParametricOperation.{feature.operation.value}, {{{params_str}}})")

            script_lines.extend([
                "",
                "# Regenerate and export",
                "final_mesh = designer.regenerate_design(design)",
                'final_mesh.export("output.stl")',
                "",
                "print(f\"Design generated with {len(final_mesh.faces)} faces\")"
            ])

            # Write script
            with open(file_path, 'w') as f:
                f.write('\n'.join(script_lines))

            return True

        except Exception as e:
            self.logger.error(f"Error exporting design to script: {e}")
            return False


# Global instance
enhanced_parametric_designer = EnhancedParametricDesigner()


def create_parametric_design(name: str) -> ParametricDesign:
    """Convenience function to create a parametric design."""
    return enhanced_parametric_designer.create_design(name)


def regenerate_parametric_mesh(design: ParametricDesign) -> trimesh.Trimesh:
    """Convenience function to regenerate a parametric design."""
    return enhanced_parametric_designer.regenerate_design(design)
