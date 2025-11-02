"""Ruby-inspired DSL (Domain Specific Language) for 3D CAD operations."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Iterator
from pathlib import Path
import math


class DSLStyle(Enum):
    """DSL styles."""
    DECLARATIVE = "declarative"
    IMPERATIVE = "imperative"
    FUNCTIONAL = "functional"
    FLUENT = "fluent"


class CADPrimitive(Enum):
    """CAD primitives."""
    CUBE = "cube"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    CONE = "cone"
    TORUS = "torus"
    PLANE = "plane"


@dataclass
class DSLContext:
    """DSL execution context."""
    variables: Dict[str, Any] = field(default_factory=dict)
    functions: Dict[str, Callable] = field(default_factory=dict)
    current_object: Optional[Any] = None
    execution_stack: List[str] = field(default_factory=list)

    def define(self, name: str, value: Any) -> None:
        """Define variable in context."""
        self.variables[name] = value

    def lookup(self, name: str) -> Any:
        """Lookup variable in context."""
        return self.variables.get(name)

    def call(self, function_name: str, *args, **kwargs) -> Any:
        """Call function in context."""
        if function_name in self.functions:
            return self.functions[function_name](*args, **kwargs)
        raise NameError(f"Function {function_name} not defined")


class RubyStyleDSL:
    """Ruby-inspired DSL engine."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.contexts: Dict[str, DSLContext] = {}
        self.dsl_scripts: Dict[str, str] = {}
        self.macros: Dict[str, str] = {}

    def create_context(self, context_name: str) -> DSLContext:
        """Create new DSL context."""
        context = DSLContext()
        self.contexts[context_name] = context

        # Add built-in CAD functions
        self._add_builtin_functions(context)

        self.logger.info(f"Created DSL context: {context_name}")
        return context

    def _add_builtin_functions(self, context: DSLContext) -> None:
        """Add built-in CAD functions to context."""

        def cube(size: float = 10.0) -> Dict[str, Any]:
            """Create cube primitive."""
            return {
                "type": "cube",
                "size": size,
                "dimensions": [size, size, size]
            }

        def sphere(radius: float = 5.0) -> Dict[str, Any]:
            """Create sphere primitive."""
            return {
                "type": "sphere",
                "radius": radius,
                "diameter": radius * 2
            }

        def cylinder(radius: float = 5.0, height: float = 10.0) -> Dict[str, Any]:
            """Create cylinder primitive."""
            return {
                "type": "cylinder",
                "radius": radius,
                "height": height,
                "volume": math.pi * radius * radius * height
            }

        def translate(obj: Dict[str, Any], x: float = 0, y: float = 0, z: float = 0) -> Dict[str, Any]:
            """Translate object."""
            result = obj.copy()
            result["transform"] = result.get("transform", {})
            result["transform"].update({"translate": [x, y, z]})
            return result

        def rotate(obj: Dict[str, Any], x: float = 0, y: float = 0, z: float = 0) -> Dict[str, Any]:
            """Rotate object."""
            result = obj.copy()
            result["transform"] = result.get("transform", {})
            result["transform"].update({"rotate": [x, y, z]})
            return result

        def scale(obj: Dict[str, Any], x: float = 1, y: float = 1, z: float = 1) -> Dict[str, Any]:
            """Scale object."""
            result = obj.copy()
            result["transform"] = result.get("transform", {})
            result["transform"].update({"scale": [x, y, z]})
            return result

        def union(*objects: Dict[str, Any]) -> Dict[str, Any]:
            """Union multiple objects."""
            return {
                "type": "union",
                "objects": list(objects),
                "operation": "union"
            }

        def difference(obj1: Dict[str, Any], obj2: Dict[str, Any]) -> Dict[str, Any]:
            """Subtract obj2 from obj1."""
            return {
                "type": "difference",
                "base": obj1,
                "subtract": obj2,
                "operation": "difference"
            }

        def intersection(*objects: Dict[str, Any]) -> Dict[str, Any]:
            """Intersect multiple objects."""
            return {
                "type": "intersection",
                "objects": list(objects),
                "operation": "intersection"
            }

        # Add functions to context
        context.functions.update({
            "cube": cube,
            "sphere": sphere,
            "cylinder": cylinder,
            "translate": translate,
            "rotate": rotate,
            "scale": scale,
            "union": union,
            "difference": difference,
            "intersection": intersection
        })

    def execute_dsl(self, script_name: str, dsl_code: str, context_name: str = "default") -> Dict[str, Any]:
        """Execute DSL script."""
        execution_result = {
            "script_name": script_name,
            "context": context_name,
            "execution_time": 0.0,
            "result": None,
            "success": True,
            "errors": []
        }

        if context_name not in self.contexts:
            self.create_context(context_name)

        context = self.contexts[context_name]

        start_time = time.time()

        try:
            # Execute DSL code (simplified execution)
            result = self._execute_dsl_code(dsl_code, context)
            execution_result["result"] = result

        except Exception as e:
            execution_result["success"] = False
            execution_result["errors"].append(str(e))

        execution_result["execution_time"] = time.time() - start_time

        # Store script
        self.dsl_scripts[script_name] = dsl_code

        return execution_result

    def _execute_dsl_code(self, dsl_code: str, context: DSLContext) -> Any:
        """Execute DSL code (simplified interpreter)."""
        # This is a simplified DSL interpreter
        # In a real implementation, this would parse and execute Ruby-like syntax

        lines = dsl_code.strip().split('\n')
        result = None

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            result = self._execute_dsl_line(line, context)

        return result

    def _execute_dsl_line(self, line: str, context: DSLContext) -> Any:
        """Execute single DSL line."""
        # Simple pattern matching for DSL execution
        line = line.strip()

        # Variable assignment
        if '=' in line and not line.startswith(' '):
            var_name, expression = line.split('=', 1)
            var_name = var_name.strip()
            expression = expression.strip()

            value = self._evaluate_expression(expression, context)
            context.define(var_name, value)
            return value

        # Method call
        elif '.' in line or line.endswith('()'):
            return self._evaluate_method_call(line, context)

        # Function call
        else:
            return self._evaluate_function_call(line, context)

    def _evaluate_expression(self, expression: str, context: DSLContext) -> Any:
        """Evaluate expression."""
        # Simple expression evaluation
        expression = expression.strip()

        # Numeric literal
        try:
            return float(expression)
        except ValueError:
            pass

        # String literal
        if expression.startswith('"') and expression.endswith('"'):
            return expression[1:-1]

        # Variable lookup
        if expression in context.variables:
            return context.variables[expression]

        # Function call
        return self._evaluate_function_call(expression, context)

    def _evaluate_method_call(self, method_call: str, context: DSLContext) -> Any:
        """Evaluate method call (Ruby-style)."""
        parts = method_call.split('.')
        if len(parts) < 2:
            return None

        object_name = parts[0].strip()
        method_chain = parts[1:]

        # Get base object
        base_object = context.lookup(object_name)
        if not base_object:
            return None

        # Execute method chain
        current = base_object
        for method_part in method_chain:
            method_part = method_part.strip()
            if method_part.endswith('()'):
                method_name = method_part[:-2]
                current = self._call_method(current, method_name, context)
            else:
                # Property access
                if isinstance(current, dict) and method_part in current:
                    current = current[method_part]
                else:
                    current = getattr(current, method_part, None)

        return current

    def _evaluate_function_call(self, function_call: str, context: DSLContext) -> Any:
        """Evaluate function call."""
        # Parse function call with arguments
        if '(' in function_call and ')' in function_call:
            func_name = function_call[:function_call.index('(')]
            args_str = function_call[function_call.index('(')+1:function_call.rindex(')')]

            # Parse arguments
            args = []
            kwargs = {}

            if args_str.strip():
                arg_parts = args_str.split(',')
                for arg in arg_parts:
                    arg = arg.strip()
                    if ':' in arg:
                        key, value = arg.split(':', 1)
                        kwargs[key.strip()] = self._evaluate_expression(value.strip(), context)
                    else:
                        args.append(self._evaluate_expression(arg, context))

            return context.call(func_name, *args, **kwargs)

        else:
            # Simple function call
            return context.call(function_call)

    def _call_method(self, obj: Any, method_name: str, context: DSLContext) -> Any:
        """Call method on object."""
        if isinstance(obj, dict) and "type" in obj:
            # CAD object method calls
            if method_name == "translate":
                x = context.variables.get("x", 0)
                y = context.variables.get("y", 0)
                z = context.variables.get("z", 0)
                return context.call("translate", obj, x, y, z)
            elif method_name == "rotate":
                x = context.variables.get("x", 0)
                y = context.variables.get("y", 0)
                z = context.variables.get("z", 0)
                return context.call("rotate", obj, x, y, z)
            elif method_name == "scale":
                x = context.variables.get("x", 1)
                y = context.variables.get("y", 1)
                z = context.variables.get("z", 1)
                return context.call("scale", obj, x, y, z)

        return obj

    def create_dsl_macro(self, macro_name: str, macro_code: str) -> None:
        """Create DSL macro."""
        self.macros[macro_name] = macro_code

    def expand_macro(self, macro_name: str, context: DSLContext) -> str:
        """Expand macro in context."""
        if macro_name in self.macros:
            return self.macros[macro_name]
        return ""

    def get_dsl_statistics(self) -> Dict[str, Any]:
        """Get DSL statistics."""
        return {
            "contexts": len(self.contexts),
            "scripts": len(self.dsl_scripts),
            "macros": len(self.macros),
            "context_names": list(self.contexts.keys()),
            "ruby_features": [
                "method_chaining",
                "blocks_and_iterators",
                "metaprogramming",
                "symbols_and_hashes",
                "fluent_interface",
                "open_classes"
            ]
        }


class CADDesignDSL:
    """CAD-specific DSL for design creation."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ruby_dsl = RubyStyleDSL()
        self.design_templates: Dict[str, str] = {}
        self.material_library: Dict[str, Dict[str, Any]] = {}

    def initialize_cad_dsl(self) -> bool:
        """Initialize CAD DSL system."""
        try:
            # Create CAD context
            self.ruby_dsl.create_context("cad_design")

            # Setup design templates
            self._setup_design_templates()

            # Setup material library
            self._setup_material_library()

            self.logger.info("CAD DSL system initialized")
            return True

        except Exception as e:
            self.logger.error(f"CAD DSL initialization failed: {e}")
            return False

    def _setup_design_templates(self) -> None:
        """Setup design templates."""
        # Phone case template
        phone_case_template = """
        phone_case = cube(80)
        phone_case = phone_case.translate(0, 0, 6)
        phone_case = phone_case.scale(1, 1.6, 0.12)

        camera_hole = cylinder(7, 3)
        camera_hole = camera_hole.translate(25, 50, 15)

        final_design = difference(phone_case, camera_hole)
        """

        # Gear template
        gear_template = """
        gear_base = cylinder(20, 5)
        gear_teeth = 12

        for i in 0..gear_teeth-1 do
            angle = (360 / gear_teeth) * i
            tooth = cube(3)
            tooth = tooth.translate(18, 0, 0)
            tooth = tooth.rotate(0, 0, angle)
            gear_base = union(gear_base, tooth)
        end

        gear_with_hole = difference(gear_base, cylinder(5, 6))
        """

        # Custom bracket template
        bracket_template = """
        base = cube(50)
        base = base.scale(1, 0.6, 0.2)

        mount_holes = cylinder(2, 10)
        mount_holes = mount_holes.translate(10, 10, 0)
        mount_holes = union(mount_holes, mount_holes.translate(30, 0, 0))

        bracket = difference(base, mount_holes)
        """

        self.design_templates = {
            "phone_case": phone_case_template,
            "gear": gear_template,
            "bracket": bracket_template
        }

    def _setup_material_library(self) -> None:
        """Setup material library."""
        self.material_library = {
            "PLA": {
                "density": 1.24,
                "strength": 50,
                "flexibility": "low",
                "temperature": 200,
                "cost_per_kg": 25.0
            },
            "ABS": {
                "density": 1.04,
                "strength": 40,
                "flexibility": "medium",
                "temperature": 240,
                "cost_per_kg": 30.0
            },
            "PETG": {
                "density": 1.27,
                "strength": 45,
                "flexibility": "medium",
                "temperature": 230,
                "cost_per_kg": 35.0
            },
            "TPU": {
                "density": 1.20,
                "strength": 35,
                "flexibility": "high",
                "temperature": 210,
                "cost_per_kg": 45.0
            }
        }

    def design(self, design_name: str = "custom", **options) -> Dict[str, Any]:
        """Create design using fluent interface."""
        design_result = {
            "design_name": design_name,
            "design_script": "",
            "design_objects": [],
            "material": options.get("material", "PLA"),
            "created_at": time.time(),
            "dsl_style": "fluent"
        }

        # Use fluent interface pattern (Ruby style)
        if options.get("template"):
            template = self.design_templates.get(options["template"])
            if template:
                design_result["design_script"] = template
                # Execute template
                execution = self.ruby_dsl.execute_dsl(design_name, template, "cad_design")
                design_result.update(execution)

        return design_result

    def create_with_dsl(self, design_script: str, design_name: str = "dsl_design") -> Dict[str, Any]:
        """Create design using DSL script."""
        execution_result = self.ruby_dsl.execute_dsl(design_name, design_script, "cad_design")

        # Add CAD-specific metadata
        execution_result.update({
            "design_name": design_name,
            "dsl_script": design_script,
            "cad_specific": True
        })

        return execution_result

    def fluent_design(self) -> 'FluentDesignBuilder':
        """Create fluent design builder."""
        return FluentDesignBuilder(self)

    def get_design_templates(self) -> Dict[str, str]:
        """Get available design templates."""
        return self.design_templates.copy()

    def get_material_properties(self, material: str) -> Dict[str, Any]:
        """Get material properties."""
        return self.material_library.get(material, {})

    def get_dsl_statistics(self) -> Dict[str, Any]:
        """Get DSL statistics."""
        return {
            "ruby_dsl": self.ruby_dsl.get_dsl_statistics(),
            "design_templates": len(self.design_templates),
            "material_library": len(self.material_library),
            "template_names": list(self.design_templates.keys()),
            "available_materials": list(self.material_library.keys()),
            "dsl_features": [
                "fluent_interface",
                "method_chaining",
                "design_templates",
                "material_library",
                "macro_expansion",
                "context_management"
            ]
        }


class FluentDesignBuilder:
    """Fluent design builder (Ruby-style)."""

    def __init__(self, cad_dsl: CADDesignDSL):
        self.cad_dsl = cad_dsl
        self.current_object = None
        self.transform_chain: List[Dict[str, Any]] = []
        self.material = "PLA"

    def cube(self, size: float = 10.0) -> 'FluentDesignBuilder':
        """Create cube and chain."""
        self.current_object = self.cad_dsl.ruby_dsl.contexts["cad_design"].call("cube", size)
        self.transform_chain.append({"operation": "create", "type": "cube", "size": size})
        return self

    def sphere(self, radius: float = 5.0) -> 'FluentDesignBuilder':
        """Create sphere and chain."""
        self.current_object = self.cad_dsl.ruby_dsl.contexts["cad_design"].call("sphere", radius)
        self.transform_chain.append({"operation": "create", "type": "sphere", "radius": radius})
        return self

    def cylinder(self, radius: float = 5.0, height: float = 10.0) -> 'FluentDesignBuilder':
        """Create cylinder and chain."""
        self.current_object = self.cad_dsl.ruby_dsl.contexts["cad_design"].call("cylinder", radius, height)
        self.transform_chain.append({"operation": "create", "type": "cylinder", "radius": radius, "height": height})
        return self

    def translate(self, x: float = 0, y: float = 0, z: float = 0) -> 'FluentDesignBuilder':
        """Translate and chain."""
        if self.current_object:
            self.current_object = self.cad_dsl.ruby_dsl.contexts["cad_design"].call("translate", self.current_object, x, y, z)
            self.transform_chain.append({"operation": "translate", "x": x, "y": y, "z": z})
        return self

    def rotate(self, x: float = 0, y: float = 0, z: float = 0) -> 'FluentDesignBuilder':
        """Rotate and chain."""
        if self.current_object:
            self.current_object = self.cad_dsl.ruby_dsl.contexts["cad_design"].call("rotate", self.current_object, x, y, z)
            self.transform_chain.append({"operation": "rotate", "x": x, "y": y, "z": z})
        return self

    def scale(self, x: float = 1, y: float = 1, z: float = 1) -> 'FluentDesignBuilder':
        """Scale and chain."""
        if self.current_object:
            self.current_object = self.cad_dsl.ruby_dsl.contexts["cad_design"].call("scale", self.current_object, x, y, z)
            self.transform_chain.append({"operation": "scale", "x": x, "y": y, "z": z})
        return self

    def with_material(self, material: str) -> 'FluentDesignBuilder':
        """Set material and chain."""
        self.material = material
        self.transform_chain.append({"operation": "material", "material": material})
        return self

    def union(self, other_builder: 'FluentDesignBuilder') -> 'FluentDesignBuilder':
        """Union with another design."""
        if self.current_object and other_builder.current_object:
            self.current_object = self.cad_dsl.ruby_dsl.contexts["cad_design"].call(
                "union", self.current_object, other_builder.current_object
            )
            self.transform_chain.append({"operation": "union", "with": "another_design"})
        return self

    def subtract(self, other_builder: 'FluentDesignBuilder') -> 'FluentDesignBuilder':
        """Subtract another design."""
        if self.current_object and other_builder.current_object:
            self.current_object = self.cad_dsl.ruby_dsl.contexts["cad_design"].call(
                "difference", self.current_object, other_builder.current_object
            )
            self.transform_chain.append({"operation": "subtract", "from": "another_design"})
        return self

    def build(self) -> Dict[str, Any]:
        """Build final design."""
        result = {
            "design_object": self.current_object,
            "transform_chain": self.transform_chain,
            "material": self.material,
            "fluent_built": True,
            "chain_length": len(self.transform_chain)
        }

        # Add material properties
        material_props = self.cad_dsl.get_material_properties(self.material)
        result["material_properties"] = material_props

        return result

    def preview(self) -> str:
        """Preview design in text format."""
        preview = f"Fluent Design Preview:\n"
        preview += f"Material: {self.material}\n"
        preview += f"Operations: {len(self.transform_chain)}\n"

        for i, transform in enumerate(self.transform_chain, 1):
            preview += f"  {i}. {transform.get('operation', 'unknown')}"
            if 'type' in transform:
                preview += f" ({transform['type']})"
            if 'x' in transform:
                preview += f" [{transform['x']}, {transform['y']}, {transform['z']}]"
            preview += "\n"

        return preview


class CADMaterialDSL:
    """Material-specific DSL for CAD."""

    def __init__(self, cad_dsl: CADDesignDSL):
        self.cad_dsl = cad_dsl
        self.current_material = "PLA"
        self.material_settings: Dict[str, Dict[str, Any]] = {}

    def use(self, material: str) -> 'CADMaterialDSL':
        """Use specific material."""
        if material in self.cad_dsl.material_library:
            self.current_material = material
            self.material_settings[material] = self.cad_dsl.material_library[material]
        return self

    def temperature(self, temp: int) -> 'CADMaterialDSL':
        """Set printing temperature."""
        if self.current_material in self.material_settings:
            self.material_settings[self.current_material]["print_temperature"] = temp
        return self

    def speed(self, speed: float) -> 'CADMaterialDSL':
        """Set printing speed."""
        if self.current_material in self.material_settings:
            self.material_settings[self.current_material]["print_speed"] = speed
        return self

    def layer_height(self, height: float) -> 'CADMaterialDSL':
        """Set layer height."""
        if self.current_material in self.material_settings:
            self.material_settings[self.current_material]["layer_height"] = height
        return self

    def infill(self, percentage: float) -> 'CADMaterialDSL':
        """Set infill percentage."""
        if self.current_material in self.material_settings:
            self.material_settings[self.current_material]["infill"] = percentage
        return self

    def settings(self) -> Dict[str, Any]:
        """Get current material settings."""
        return self.material_settings.get(self.current_material, {})


class CADDesignSystem:
    """Complete CAD design system with Ruby-style DSL."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cad_dsl = CADDesignDSL()
        self.design_history: List[Dict[str, Any]] = []
        self.dsl_scripts: Dict[str, str] = {}

    def initialize_design_system(self) -> bool:
        """Initialize design system."""
        try:
            if not self.cad_dsl.initialize_cad_dsl():
                return False

            # Create sample DSL scripts
            self._create_sample_scripts()

            self.logger.info("CAD design system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Design system initialization failed: {e}")
            return False

    def _create_sample_scripts(self) -> None:
        """Create sample DSL scripts."""

        # Phone case design
        phone_case_script = """
        # Phone Case Design
        case_base = cube(80)
        case_base = case_base.translate(0, 0, 6)
        case_base = case_base.scale(1, 1.6, 0.12)

        # Camera cutout
        camera_hole = cylinder(7, 3)
        camera_hole = camera_hole.translate(25, 50, 15)

        # Button cutouts
        button_hole = cube(8)
        button_hole = button_hole.translate(10, 120, 5)

        # Combine
        phone_case = difference(case_base, camera_hole)
        phone_case = difference(phone_case, button_hole)
        """

        # Mechanical gear
        gear_script = """
        # Mechanical Gear Design
        gear_radius = 20
        gear_thickness = 5
        tooth_count = 12

        # Base gear
        gear = cylinder(gear_radius, gear_thickness)

        # Add teeth
        for i in 0..tooth_count-1
            angle = (360.0 / tooth_count) * i
            tooth = cube(3)
            tooth = tooth.translate(gear_radius - 1, 0, 0)
            tooth = tooth.rotate(0, 0, angle)
            gear = union(gear, tooth)
        end

        # Center hole
        center_hole = cylinder(5, gear_thickness + 1)
        final_gear = difference(gear, center_hole)
        """

        # Custom bracket
        bracket_script = """
        # Custom Bracket Design
        base_length = 50
        base_width = 30
        base_height = 10

        # Base plate
        base = cube(base_length)
        base = base.scale(1, base_width/base_length, base_height/base_length)

        # Mounting holes
        hole_radius = 2
        hole_positions = [10, base_length - 10]

        bracket = base
        for x_pos in hole_positions
            hole = cylinder(hole_radius, base_height + 1)
            hole = hole.translate(x_pos, base_width/2, 0)
            bracket = difference(bracket, hole)
        end
        """

        self.dsl_scripts = {
            "phone_case": phone_case_script,
            "gear": gear_script,
            "bracket": bracket_script
        }

    def create_design_with_dsl(self, script_name: str, custom_script: str = None) -> Dict[str, Any]:
        """Create design using DSL."""
        script = custom_script or self.dsl_scripts.get(script_name, "")

        if not script:
            return {"error": f"Script {script_name} not found"}

        # Execute DSL script
        execution_result = self.cad_dsl.create_with_dsl(script, script_name)

        # Add to history
        self.design_history.append(execution_result)

        return execution_result

    def create_fluent_design(self, design_name: str = "fluent_design") -> Dict[str, Any]:
        """Create design using fluent interface."""
        builder = self.cad_dsl.fluent_design()

        # Example fluent design creation
        design = (builder
                 .cube(50)
                 .translate(0, 0, 25)
                 .with_material("PLA")
                 .build())

        design["design_name"] = design_name
        design["created_with_fluent"] = True

        # Add to history
        self.design_history.append(design)

        return design

    def apply_material_settings(self, material: str, **settings) -> Dict[str, Any]:
        """Apply material settings using DSL."""
        material_dsl = CADMaterialDSL(self.cad_dsl)

        # Apply settings using method chaining
        configured = (material_dsl
                     .use(material)
                     .temperature(settings.get("temperature", 200))
                     .speed(settings.get("speed", 50))
                     .layer_height(settings.get("layer_height", 0.2))
                     .infill(settings.get("infill", 20))
                     .settings())

        return {
            "material": material,
            "settings_applied": configured,
            "dsl_configured": True
        }

    def get_design_summary(self) -> Dict[str, Any]:
        """Get design system summary."""
        return {
            "cad_dsl": self.cad_dsl.get_dsl_statistics(),
            "design_history": len(self.design_history),
            "dsl_scripts": len(self.dsl_scripts),
            "script_names": list(self.dsl_scripts.keys()),
            "design_features": [
                "ruby_style_dsl",
                "fluent_interface",
                "method_chaining",
                "design_templates",
                "material_configuration",
                "macro_system"
            ]
        }


# Factory functions for Ruby-style DSL
def create_ruby_dsl() -> RubyStyleDSL:
    """Create Ruby-style DSL engine."""
    return RubyStyleDSL()


def create_cad_dsl() -> CADDesignDSL:
    """Create CAD design DSL."""
    return CADDesignDSL()


def create_design_system() -> CADDesignSystem:
    """Create CAD design system."""
    return CADDesignSystem()


# Example usage and DSL patterns
class DSLPatterns:
    """DSL patterns and examples."""

    @staticmethod
    def phone_case_pattern() -> str:
        """Phone case design pattern."""
        return """
        # Natural language-like CAD design
        phone_case = cube(80, 160, 12) do |case_obj|
            case_obj.translate(0, 0, 6)
            case_obj.scale(1, 1, 0.12)

            # Camera cutout
            camera_hole = cylinder(7, 3)
            camera_hole.translate(25, 50, 15)
            case_obj.subtract(camera_hole)

            # Button cutouts
            volume_buttons = cube(8, 4, 3)
            volume_buttons.translate(5, 100, 5)
            case_obj.subtract(volume_buttons)
        end

        phone_case.material = :PLA
        phone_case.infill = 25
        """

    @staticmethod
    def gear_pattern() -> str:
        """Gear design pattern."""
        return """
        # Parametric gear design
        gear(radius: 20, teeth: 12, thickness: 5) do |g|
            # Add spokes for reinforcement
            spoke_count = 6
            spoke_count.times do |i|
                angle = (360.0 / spoke_count) * i
                spoke = cube(2, radius - 2, thickness)
                spoke.rotate(0, 0, angle)
                g.union(spoke)
            end

            # Center hub
            hub = cylinder(8, thickness + 2)
            g.subtract(hub)
        end
        """

    @staticmethod
    def assembly_pattern() -> str:
        """Assembly design pattern."""
        return """
        # Assembly design with constraints
        assembly do
            base = cube(100, 100, 10)

            # Components with relationships
            component(:motor_mount) do
                mount = cylinder(15, 20)
                mount.translate(50, 50, 10)
                base.union(mount)
            end

            component(:support_rod) do
                rod = cylinder(3, 80)
                rod.rotate(90, 0, 0)
                rod.translate(50, 50, 55)
                base.union(rod)
            end

            # Constraints
            constraint(:parallel, :motor_mount, :support_rod)
            constraint(:distance, :motor_mount, :support_rod, 40)
        end
        """
