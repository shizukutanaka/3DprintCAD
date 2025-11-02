"""Ruby/Lua/R-inspired DSL and metaprogramming for 3D CAD operations."""

from __future__ import annotations

import ast
import logging
import math
import operator
import re
import time
import types
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Type, TypeVar
from pathlib import Path
import weakref


T = TypeVar('T')


class DSLParadigm(Enum):
    """DSL paradigms inspired by different languages."""
    RUBY_BLOCKS = "ruby_blocks"      # Ruby-style blocks and DSL
    LUA_TABLES = "lua_tables"        # Lua-style table-based configuration
    R_FORMULAS = "r_formulas"        # R-style statistical formulas
    DOMAIN_SPECIFIC = "domain_specific"  # CAD-specific DSL


class MetaprogrammingEngine:
    """Ruby/Lua-inspired metaprogramming engine."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.dynamic_classes: Dict[str, Type] = {}
        self.monkey_patches: Dict[str, Dict[str, Any]] = {}
        self.dsl_registry: Dict[str, Callable] = {}

    def create_dynamic_class(self, name: str, base_classes: List[Type] = None,
                           attributes: Dict[str, Any] = None) -> Type:
        """Create dynamic class (Ruby metaclass equivalent)."""
        if base_classes is None:
            base_classes = [object]
        if attributes is None:
            attributes = {}

        # Create class dynamically
        dynamic_class = type(name, tuple(base_classes), attributes)

        # Register in module namespace (monkey patching)
        globals()[name] = dynamic_class
        self.dynamic_classes[name] = dynamic_class

        self.logger.info(f"Created dynamic class: {name}")
        return dynamic_class

    def monkey_patch_class(self, target_class: Type, method_name: str,
                          new_method: Callable) -> bool:
        """Monkey patch class method (Ruby monkey patching equivalent)."""
        try:
            # Store original method
            if hasattr(target_class, method_name):
                original_method = getattr(target_class, method_name)
                self.monkey_patches[target_class.__name__] = self.monkey_patches.get(target_class.__name__, {})
                self.monkey_patches[target_class.__name__][method_name] = original_method

            # Apply patch
            setattr(target_class, method_name, new_method)

            self.logger.info(f"Monkey patched {target_class.__name__}.{method_name}")
            return True

        except Exception as e:
            self.logger.error(f"Monkey patching failed: {e}")
            return False

    def restore_patches(self, target_class: Type) -> bool:
        """Restore original methods (reverse monkey patching)."""
        class_name = target_class.__name__

        if class_name in self.monkey_patches:
            for method_name, original_method in self.monkey_patches[class_name].items():
                setattr(target_class, method_name, original_method)

            del self.monkey_patches[class_name]
            self.logger.info(f"Restored patches for {class_name}")
            return True

        return False

    def generate_code_at_runtime(self, template: str, variables: Dict[str, Any]) -> str:
        """Generate code at runtime (Ruby ERB equivalent)."""
        # Simple template substitution
        generated_code = template

        for var_name, var_value in variables.items():
            generated_code = generated_code.replace(f"{{{{{var_name}}}}}", str(var_value))

        return generated_code

    def register_dsl_function(self, name: str, function: Callable,
                            paradigm: DSLParadigm = DSLParadigm.DOMAIN_SPECIFIC) -> None:
        """Register DSL function."""
        self.dsl_registry[name] = {
            "function": function,
            "paradigm": paradigm,
            "signature": self._extract_function_signature(function)
        }

    def _extract_function_signature(self, function: Callable) -> Dict[str, Any]:
        """Extract function signature for DSL."""
        try:
            sig = inspect.signature(function)
            return {
                "parameters": list(sig.parameters.keys()),
                "defaults": {k: v.default for k, v in sig.parameters.items() if v.default != inspect.Parameter.empty},
                "annotations": {k: str(v.annotation) for k, v in sig.parameters.items() if v.annotation != inspect.Parameter.empty}
            }
        except Exception:
            return {}


class DSLInterpreter:
    """Ruby/Lua-inspired DSL interpreter for CAD operations."""

    def __init__(self, metaprogramming_engine: MetaprogrammingEngine):
        self.logger = logging.getLogger(__name__)
        self.meta_engine = metaprogramming_engine
        self.variables: Dict[str, Any] = {}
        self.functions: Dict[str, Callable] = {}
        self.context_stack: List[Dict[str, Any]] = []

    def interpret_dsl(self, dsl_code: str, context: Dict[str, Any] = None) -> Result[Any]:
        """Interpret DSL code (Ruby eval equivalent)."""
        try:
            if context:
                self.variables.update(context)

            # Parse DSL syntax
            parsed_statements = self._parse_dsl_syntax(dsl_code)

            # Execute statements
            result = None
            for statement in parsed_statements:
                result = self._execute_statement(statement)
                if isinstance(result, Result) and result.is_err():
                    return result

            return Result.ok(result)

        except Exception as e:
            return Result.err(e)

    def _parse_dsl_syntax(self, code: str) -> List[Dict[str, Any]]:
        """Parse DSL syntax into executable statements."""
        statements = []

        # Simple DSL parsing - in real implementation would use proper parser
        lines = code.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Parse different DSL patterns
            if self._is_ruby_style_block(line):
                statements.append(self._parse_ruby_block(line))
            elif self._is_lua_style_table(line):
                statements.append(self._parse_lua_table(line))
            elif self._is_r_style_formula(line):
                statements.append(self._parse_r_formula(line))
            else:
                statements.append(self._parse_simple_statement(line))

        return statements

    def _is_ruby_style_block(self, line: str) -> bool:
        """Check if line is Ruby-style block."""
        return ' do ' in line or line.endswith(' do') or '{' in line

    def _is_lua_style_table(self, line: str) -> bool:
        """Check if line is Lua-style table."""
        return line.startswith('local ') or '=' in line and '{' in line

    def _is_r_style_formula(self, line: str) -> bool:
        """Check if line is R-style formula."""
        return line.startswith('model <-') or '~' in line or 'lm(' in line

    def _parse_ruby_block(self, line: str) -> Dict[str, Any]:
        """Parse Ruby-style block syntax."""
        # Extract method call and block
        match = re.match(r'(\w+)\s*\(([^)]*)\)\s*do\s*\|([^|]*)\|', line)
        if match:
            method_name, args, block_vars = match.groups()
            return {
                "type": "ruby_block",
                "method": method_name,
                "args": args,
                "block_vars": block_vars.split(','),
                "code": line
            }

        return {"type": "unknown", "code": line}

    def _parse_lua_table(self, line: str) -> Dict[str, Any]:
        """Parse Lua-style table syntax."""
        match = re.match(r'(\w+)\s*=\s*\{([^}]*)\}', line)
        if match:
            table_name, table_content = match.groups()
            return {
                "type": "lua_table",
                "name": table_name,
                "content": table_content,
                "code": line
            }

        return {"type": "unknown", "code": line}

    def _parse_r_formula(self, line: str) -> Dict[str, Any]:
        """Parse R-style formula syntax."""
        if '~' in line:
            parts = line.split('~')
            if len(parts) == 2:
                return {
                    "type": "r_formula",
                    "response": parts[0].strip(),
                    "predictors": parts[1].strip(),
                    "code": line
                }

        return {"type": "unknown", "code": line}

    def _parse_simple_statement(self, line: str) -> Dict[str, Any]:
        """Parse simple statement."""
        return {
            "type": "simple",
            "code": line
        }

    def _execute_statement(self, statement: Dict[str, Any]) -> Any:
        """Execute DSL statement."""
        stmt_type = statement["type"]

        if stmt_type == "ruby_block":
            return self._execute_ruby_block(statement)
        elif stmt_type == "lua_table":
            return self._execute_lua_table(statement)
        elif stmt_type == "r_formula":
            return self._execute_r_formula(statement)
        elif stmt_type == "simple":
            return self._execute_simple_statement(statement)
        else:
            return statement  # Unknown statement

    def _execute_ruby_block(self, statement: Dict[str, Any]) -> Any:
        """Execute Ruby-style block."""
        method_name = statement["method"]
        args = statement.get("args", "")

        # Find corresponding function
        if method_name in self.functions:
            func = self.functions[method_name]

            # Parse arguments
            parsed_args = self._parse_arguments(args)

            # Call function with block context
            return func(*parsed_args)

        return None

    def _execute_lua_table(self, statement: Dict[str, Any]) -> Any:
        """Execute Lua-style table creation."""
        table_name = statement["name"]
        table_content = statement["content"]

        # Parse table content
        table_data = self._parse_table_content(table_content)

        # Store in variables
        self.variables[table_name] = table_data

        return table_data

    def _execute_r_formula(self, statement: Dict[str, Any]) -> Any:
        """Execute R-style formula."""
        response = statement["response"]
        predictors = statement["predictors"]

        # Simple linear model approximation
        if response in self.variables and predictors in self.variables:
            return self._fit_simple_model(self.variables[response], self.variables[predictors])

        return {"formula": f"{response} ~ {predictors}"}

    def _execute_simple_statement(self, statement: Dict[str, Any]) -> Any:
        """Execute simple statement."""
        code = statement["code"]

        try:
            # Safe evaluation
            return eval(code, {"__builtins__": {}}, self.variables)
        except Exception as e:
            self.logger.error(f"Statement execution failed: {e}")
            return None

    def _parse_arguments(self, args_str: str) -> List[Any]:
        """Parse function arguments."""
        if not args_str.strip():
            return []

        # Simple argument parsing
        args = []
        for arg in args_str.split(','):
            arg = arg.strip()
            if arg.isdigit():
                args.append(int(arg))
            elif arg.replace('.', '').isdigit():
                args.append(float(arg))
            elif arg.startswith('"') and arg.endswith('"'):
                args.append(arg[1:-1])
            else:
                # Variable reference
                args.append(self.variables.get(arg, arg))

        return args

    def _parse_table_content(self, content: str) -> Dict[str, Any]:
        """Parse Lua-style table content."""
        table_dict = {}

        # Simple key-value parsing
        pairs = content.split(',')
        for pair in pairs:
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Convert value
                if value.isdigit():
                    table_dict[key] = int(value)
                elif value.replace('.', '').isdigit():
                    table_dict[key] = float(value)
                else:
                    table_dict[key] = value.strip('"')

        return table_dict

    def _fit_simple_model(self, response_data: List[float], predictor_data: List[float]) -> Dict[str, Any]:
        """Fit simple linear model (R lm equivalent)."""
        if len(response_data) != len(predictor_data):
            return {"error": "Data length mismatch"}

        n = len(response_data)

        # Calculate means
        mean_y = sum(response_data) / n
        mean_x = sum(predictor_data) / n

        # Calculate slope and intercept
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(predictor_data, response_data))
        denominator = sum((x - mean_x) ** 2 for x in predictor_data)

        if denominator == 0:
            return {"error": "No variation in predictor"}

        slope = numerator / denominator
        intercept = mean_y - slope * mean_x

        # Calculate R-squared
        y_pred = [intercept + slope * x for x in predictor_data]
        ss_total = sum((y - mean_y) ** 2 for y in response_data)
        ss_residual = sum((y - y_pred) ** 2 for y, y_pred in zip(response_data, y_pred))

        r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 0

        return {
            "coefficients": {"intercept": intercept, "slope": slope},
            "r_squared": r_squared,
            "residuals": [y - y_pred for y, y_pred in zip(response_data, y_pred)]
        }


class CADDSLBuilder:
    """Ruby/R-inspired DSL builder for CAD operations."""

    def __init__(self, metaprogramming_engine: MetaprogrammingEngine):
        self.logger = logging.getLogger(__name__)
        self.meta_engine = metaprogramming_engine
        self.dsl_context: Dict[str, Any] = {}
        self.current_mesh = None

    def create_cad_dsl(self, dsl_name: str) -> 'CADDSL':
        """Create CAD DSL instance."""
        return CADDSL(dsl_name, self.meta_engine, self)

    def register_cad_function(self, name: str, function: Callable,
                            paradigm: DSLParadigm = DSLParadigm.DOMAIN_SPECIFIC) -> None:
        """Register CAD function in DSL."""
        self.meta_engine.register_dsl_function(name, function, paradigm)

        # Add to DSL context
        self.dsl_context[name] = function


class CADDSL:
    """Ruby/R-inspired CAD domain-specific language."""

    def __init__(self, name: str, meta_engine: MetaprogrammingEngine,
                 builder: CADDSLBuilder):
        self.name = name
        self.meta_engine = meta_engine
        self.builder = builder
        self.logger = logging.getLogger(f"dsl.{name}")
        self.local_variables: Dict[str, Any] = {}

    def __getattr__(self, name: str) -> Any:
        """Dynamic method resolution (Ruby method_missing equivalent)."""
        if name in self.local_variables:
            return self.local_variables[name]

        # Look for DSL function
        if name in self.meta_engine.dsl_registry:
            return self.meta_engine.dsl_registry[name]["function"]

        # Create dynamic method (Ruby metaprogramming)
        def dynamic_method(*args, **kwargs):
            return self._handle_unknown_method(name, *args, **kwargs)

        return dynamic_method

    def _handle_unknown_method(self, method_name: str, *args, **kwargs) -> Any:
        """Handle unknown method calls (Ruby method_missing)."""
        self.logger.warning(f"Unknown method called: {method_name}")

        # Try to interpret as DSL operation
        if method_name.startswith("create_"):
            return self._create_shape(method_name[6:], *args, **kwargs)
        elif method_name.startswith("transform_"):
            return self._transform_shape(method_name[10:], *args, **kwargs)
        else:
            return None

    def create_cube(self, size: float = 1.0) -> Dict[str, Any]:
        """Create cube (Ruby DSL syntax)."""
        return {
            "type": "cube",
            "size": size,
            "vertices": self._generate_cube_vertices(size),
            "faces": self._generate_cube_faces(),
            "created_at": time.time()
        }

    def create_sphere(self, radius: float = 1.0, segments: int = 16) -> Dict[str, Any]:
        """Create sphere (Ruby DSL syntax)."""
        return {
            "type": "sphere",
            "radius": radius,
            "segments": segments,
            "vertices": self._generate_sphere_vertices(radius, segments),
            "faces": self._generate_sphere_faces(segments),
            "created_at": time.time()
        }

    def create_cylinder(self, radius: float = 1.0, height: float = 2.0,
                       segments: int = 16) -> Dict[str, Any]:
        """Create cylinder (Ruby DSL syntax)."""
        return {
            "type": "cylinder",
            "radius": radius,
            "height": height,
            "segments": segments,
            "vertices": self._generate_cylinder_vertices(radius, height, segments),
            "faces": self._generate_cylinder_faces(segments),
            "created_at": time.time()
        }

    def _create_shape(self, shape_type: str, *args, **kwargs) -> Dict[str, Any]:
        """Create shape using dynamic dispatch."""
        method_name = f"create_{shape_type}"

        if hasattr(self, method_name):
            return getattr(self, method_name)(*args, **kwargs)
        else:
            return {"error": f"Unknown shape type: {shape_type}"}

    def _transform_shape(self, transform_type: str, *args, **kwargs) -> Dict[str, Any]:
        """Transform shape using dynamic dispatch."""
        transformations = {
            "translate": self._translate_mesh,
            "rotate": self._rotate_mesh,
            "scale": self._scale_mesh,
            "union": self._union_meshes,
            "difference": self._difference_meshes,
            "intersection": self._intersection_meshes
        }

        if transform_type in transformations:
            return transformations[transform_type](*args, **kwargs)
        else:
            return {"error": f"Unknown transformation: {transform_type}"}

    def _translate_mesh(self, mesh_data: Dict[str, Any], offset: List[float]) -> Dict[str, Any]:
        """Translate mesh."""
        vertices = mesh_data["vertices"]

        # Translate each vertex
        new_vertices = [
            [v[0] + offset[0], v[1] + offset[1], v[2] + offset[2]]
            for v in vertices
        ]

        return {
            **mesh_data,
            "vertices": new_vertices,
            "transformation": "translate",
            "offset": offset
        }

    def _rotate_mesh(self, mesh_data: Dict[str, Any], angle: float, axis: str = "z") -> Dict[str, Any]:
        """Rotate mesh."""
        vertices = mesh_data["vertices"]
        cos_a, sin_a = math.cos(angle), math.sin(angle)

        def rotate_vertex(vertex):
            x, y, z = vertex
            if axis == "z":
                return [x * cos_a - y * sin_a, x * sin_a + y * cos_a, z]
            return vertex

        new_vertices = [rotate_vertex(v) for v in vertices]

        return {
            **mesh_data,
            "vertices": new_vertices,
            "transformation": "rotate",
            "angle": angle,
            "axis": axis
        }

    def _scale_mesh(self, mesh_data: Dict[str, Any], scale_factor: float) -> Dict[str, Any]:
        """Scale mesh."""
        vertices = mesh_data["vertices"]
        new_vertices = [[v[0] * scale_factor, v[1] * scale_factor, v[2] * scale_factor]
                       for v in vertices]

        return {
            **mesh_data,
            "vertices": new_vertices,
            "transformation": "scale",
            "scale_factor": scale_factor
        }

    def _union_meshes(self, mesh1: Dict[str, Any], mesh2: Dict[str, Any]) -> Dict[str, Any]:
        """Union of two meshes."""
        # Simplified union - just combine vertices and faces
        offset = len(mesh1["vertices"])

        combined_vertices = mesh1["vertices"] + mesh2["vertices"]
        combined_faces = mesh1["faces"] + [
            [f[0] + offset, f[1] + offset, f[2] + offset]
            for f in mesh2["faces"]
        ]

        return {
            "type": "union",
            "vertices": combined_vertices,
            "faces": combined_faces,
            "source_meshes": [mesh1["type"], mesh2["type"]],
            "created_at": time.time()
        }

    def _difference_meshes(self, mesh1: Dict[str, Any], mesh2: Dict[str, Any]) -> Dict[str, Any]:
        """Difference of two meshes."""
        # Simplified difference
        return {
            "type": "difference",
            "base_mesh": mesh1["type"],
            "tool_mesh": mesh2["type"],
            "vertices": mesh1["vertices"],  # Simplified
            "faces": mesh1["faces"],
            "created_at": time.time()
        }

    def _intersection_meshes(self, mesh1: Dict[str, Any], mesh2: Dict[str, Any]) -> Dict[str, Any]:
        """Intersection of two meshes."""
        # Simplified intersection
        return {
            "type": "intersection",
            "vertices": mesh1["vertices"],  # Simplified
            "faces": mesh1["faces"],
            "created_at": time.time()
        }

    def _generate_cube_vertices(self, size: float) -> List[List[float]]:
        """Generate cube vertices."""
        half_size = size / 2
        return [
            [-half_size, -half_size, -half_size],
            [half_size, -half_size, -half_size],
            [half_size, half_size, -half_size],
            [-half_size, half_size, -half_size],
            [-half_size, -half_size, half_size],
            [half_size, -half_size, half_size],
            [half_size, half_size, half_size],
            [-half_size, half_size, half_size]
        ]

    def _generate_cube_faces(self) -> List[List[int]]:
        """Generate cube faces."""
        return [
            [0, 1, 2], [0, 2, 3],  # Bottom face
            [4, 5, 6], [4, 6, 7],  # Top face
            [0, 1, 5], [0, 5, 4],  # Front face
            [1, 2, 6], [1, 6, 5],  # Right face
            [2, 3, 7], [2, 7, 6],  # Back face
            [3, 0, 4], [3, 4, 7]   # Left face
        ]

    def _generate_sphere_vertices(self, radius: float, segments: int) -> List[List[float]]:
        """Generate sphere vertices (simplified)."""
        vertices = []

        # Generate vertices using spherical coordinates
        for i in range(segments + 1):
            phi = math.pi * i / segments  # Latitude

            for j in range(segments + 1):
                theta = 2 * math.pi * j / segments  # Longitude

                x = radius * math.sin(phi) * math.cos(theta)
                y = radius * math.sin(phi) * math.sin(theta)
                z = radius * math.cos(phi)

                vertices.append([x, y, z])

        return vertices

    def _generate_sphere_faces(self, segments: int) -> List[List[int]]:
        """Generate sphere faces."""
        faces = []

        for i in range(segments):
            for j in range(segments):
                # Create quad and split into triangles
                v0 = i * (segments + 1) + j
                v1 = i * (segments + 1) + j + 1
                v2 = (i + 1) * (segments + 1) + j + 1
                v3 = (i + 1) * (segments + 1) + j

                faces.append([v0, v1, v2])
                faces.append([v0, v2, v3])

        return faces

    def _generate_cylinder_vertices(self, radius: float, height: float, segments: int) -> List[List[float]]:
        """Generate cylinder vertices."""
        vertices = []

        half_height = height / 2

        # Generate circle vertices for bottom and top
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)

            # Bottom vertex
            vertices.append([x, -half_height, z])
            # Top vertex
            vertices.append([x, half_height, z])

        return vertices

    def _generate_cylinder_faces(self, segments: int) -> List[List[int]]:
        """Generate cylinder faces."""
        faces = []

        # Side faces
        for i in range(segments):
            next_i = (i + 1) % segments

            # Bottom face triangle
            bottom_current = i * 2
            bottom_next = next_i * 2
            faces.append([bottom_current, bottom_next, bottom_next + 1])
            faces.append([bottom_current, bottom_next + 1, bottom_current + 1])

        return faces


class StatisticalAnalysisEngine:
    """R language-inspired statistical analysis for CAD."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.datasets: Dict[str, Any] = {}
        self.models: Dict[str, Any] = {}

    def load_dataset(self, name: str, data: Any) -> None:
        """Load dataset (R data.frame equivalent)."""
        self.datasets[name] = data
        self.logger.info(f"Loaded dataset: {name}")

    def linear_regression(self, response_var: str, predictor_vars: List[str],
                        dataset: str = "default") -> Dict[str, Any]:
        """Perform linear regression (R lm equivalent)."""
        if dataset not in self.datasets:
            return {"error": f"Dataset {dataset} not found"}

        data = self.datasets[dataset]

        # Extract variables
        try:
            y = [row[response_var] for row in data]
            X = [[1] + [row[var] for var in predictor_vars] for row in data]

            # Perform regression using numpy
            if hasattr(X[0], '__len__') and len(X[0]) > 1:
                import numpy as np
                X_matrix = np.array(X)
                y_vector = np.array(y)

                # Solve normal equations
                coefficients = np.linalg.solve(X_matrix.T @ X_matrix, X_matrix.T @ y_vector)

                # Calculate R-squared
                y_pred = X_matrix @ coefficients
                ss_total = np.sum((y_vector - np.mean(y_vector))**2)
                ss_residual = np.sum((y_vector - y_pred)**2)
                r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 0

                return {
                    "coefficients": coefficients.tolist(),
                    "r_squared": r_squared,
                    "predictor_variables": predictor_vars,
                    "response_variable": response_var,
                    "method": "least_squares"
                }
            else:
                return {"error": "Insufficient data for regression"}

        except Exception as e:
            return {"error": f"Regression failed: {e}"}

    def correlation_analysis(self, variables: List[str], dataset: str = "default") -> Dict[str, Any]:
        """Perform correlation analysis (R cor equivalent)."""
        if dataset not in self.datasets:
            return {"error": f"Dataset {dataset} not found"}

        data = self.datasets[dataset]

        try:
            # Extract variable data
            var_data = {}
            for var in variables:
                var_data[var] = [row[var] for row in data]

            # Calculate correlation matrix
            correlations = {}
            for i, var1 in enumerate(variables):
                correlations[var1] = {}
                for j, var2 in enumerate(variables):
                    if i <= j:  # Only compute upper triangle
                        corr = self._calculate_correlation(var_data[var1], var_data[var2])
                        correlations[var1][var2] = corr
                        if var1 != var2:
                            correlations[var2][var1] = corr

            return {
                "correlation_matrix": correlations,
                "variables": variables,
                "method": "pearson"
            }

        except Exception as e:
            return {"error": f"Correlation analysis failed: {e}"}

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denominator_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
        denominator_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5

        if denominator_x == 0 or denominator_y == 0:
            return 0.0

        return numerator / (denominator_x * denominator_y)

    def principal_component_analysis(self, variables: List[str],
                                   dataset: str = "default") -> Dict[str, Any]:
        """Perform PCA (R prcomp equivalent)."""
        if dataset not in self.datasets:
            return {"error": f"Dataset {dataset} not found"}

        data = self.datasets[dataset]

        try:
            # Extract and center data
            matrix_data = []
            for row in data:
                matrix_data.append([row[var] for var in variables])

            import numpy as np
            X = np.array(matrix_data)

            # Center data
            X_centered = X - np.mean(X, axis=0)

            # Compute covariance matrix
            cov_matrix = np.cov(X_centered, rowvar=False)

            # Eigendecomposition
            eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

            # Sort in descending order
            indices = np.argsort(eigenvalues)[::-1]
            eigenvalues = eigenvalues[indices]
            eigenvectors = eigenvectors[:, indices]

            return {
                "eigenvalues": eigenvalues.tolist(),
                "eigenvectors": eigenvectors.tolist(),
                "explained_variance_ratio": (eigenvalues / np.sum(eigenvalues)).tolist(),
                "variables": variables,
                "method": "eigen_decomposition"
            }

        except Exception as e:
            return {"error": f"PCA failed: {e}"}

    def cluster_analysis(self, variables: List[str], n_clusters: int = 3,
                        dataset: str = "default") -> Dict[str, Any]:
        """Perform cluster analysis (R kmeans equivalent)."""
        if dataset not in self.datasets:
            return {"error": f"Dataset {dataset} not found"}

        data = self.datasets[dataset]

        try:
            # Extract data for clustering
            cluster_data = []
            for row in data:
                cluster_data.append([row[var] for var in variables])

            # Simple k-means implementation
            centroids, labels = self._kmeans(cluster_data, n_clusters)

            return {
                "centroids": centroids,
                "labels": labels,
                "n_clusters": n_clusters,
                "variables": variables,
                "method": "kmeans"
            }

        except Exception as e:
            return {"error": f"Cluster analysis failed: {e}"}

    def _kmeans(self, data: List[List[float]], n_clusters: int,
               max_iterations: int = 100) -> Tuple[List[List[float]], List[int]]:
        """Simple k-means clustering."""
        import random

        # Initialize centroids randomly
        centroids = random.sample(data, n_clusters)

        for _ in range(max_iterations):
            # Assign points to nearest centroid
            labels = []
            for point in data:
                distances = [
                    sum((a - b) ** 2 for a, b in zip(point, centroid)) ** 0.5
                    for centroid in centroids
                ]
                labels.append(distances.index(min(distances)))

            # Update centroids
            new_centroids = []
            for cluster_id in range(n_clusters):
                cluster_points = [data[i] for i, label in enumerate(labels) if label == cluster_id]

                if cluster_points:
                    new_centroid = [
                        sum(point[axis] for point in cluster_points) / len(cluster_points)
                        for axis in range(len(data[0]))
                    ]
                    new_centroids.append(new_centroid)
                else:
                    new_centroids.append(centroids[cluster_id])  # Keep old centroid

            # Check convergence
            if new_centroids == centroids:
                break

            centroids = new_centroids

        return centroids, labels


class LuaStyleConfiguration:
    """Lua-style table-based configuration system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_tables: Dict[str, Dict[str, Any]] = {}
        self.table_inheritance: Dict[str, str] = {}

    def create_config_table(self, name: str, config_data: Dict[str, Any],
                          parent: Optional[str] = None) -> bool:
        """Create configuration table (Lua table equivalent)."""
        try:
            self.config_tables[name] = config_data.copy()

            if parent and parent in self.config_tables:
                # Inherit from parent table (Lua metatable equivalent)
                self.table_inheritance[name] = parent
                self._inherit_config_properties(name, parent)

            self.logger.info(f"Created config table: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Config table creation failed: {e}")
            return False

    def _inherit_config_properties(self, child_name: str, parent_name: str) -> None:
        """Inherit properties from parent table."""
        parent_config = self.config_tables[parent_name]
        child_config = self.config_tables[child_name]

        # Copy missing properties from parent
        for key, value in parent_config.items():
            if key not in child_config:
                child_config[key] = value

    def get_config_value(self, table_name: str, key_path: str,
                        default: Any = None) -> Any:
        """Get configuration value with path (Lua table access equivalent)."""
        if table_name not in self.config_tables:
            return default

        # Parse key path (e.g., "mesh.optimization.target_vertices")
        keys = key_path.split('.')

        current_table = self.config_tables[table_name]

        try:
            for key in keys:
                if isinstance(current_table, dict) and key in current_table:
                    current_table = current_table[key]
                else:
                    return default

            return current_table

        except Exception:
            return default

    def set_config_value(self, table_name: str, key_path: str, value: Any) -> bool:
        """Set configuration value (Lua table assignment equivalent)."""
        if table_name not in self.config_tables:
            return False

        # Parse key path
        keys = key_path.split('.')

        current_table = self.config_tables[table_name]

        try:
            # Navigate to parent of target key
            for key in keys[:-1]:
                if key not in current_table:
                    current_table[key] = {}
                current_table = current_table[key]

            # Set value
            current_table[keys[-1]] = value
            return True

        except Exception as e:
            self.logger.error(f"Config value setting failed: {e}")
            return False

    def merge_config_tables(self, target_table: str, source_table: str) -> bool:
        """Merge configuration tables (Lua table merging equivalent)."""
        if target_table not in self.config_tables or source_table not in self.config_tables:
            return False

        def merge_dicts(target: Dict, source: Dict):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    merge_dicts(target[key], value)
                else:
                    target[key] = value

        merge_dicts(self.config_tables[target_table], self.config_tables[source_table])
        return True

    def export_config_lua(self, table_name: str) -> str:
        """Export configuration as Lua table syntax."""
        if table_name not in self.config_tables:
            return "-- Table not found"

        def dict_to_lua(table: Dict, indent: int = 0) -> str:
            lua_code = "{\n"
            indent_str = "  " * (indent + 1)

            for key, value in table.items():
                if isinstance(value, dict):
                    lua_code += f"{indent_str}{key} = {dict_to_lua(value, indent + 1)}"
                elif isinstance(value, str):
                    lua_code += f'{indent_str}{key} = "{value}",\n'
                else:
                    lua_code += f"{indent_str}{key} = {value},\n"

            lua_code += "  " * indent + "}"
            return lua_code

        return f"local {table_name} = {dict_to_lua(self.config_tables[table_name])}"


class CADScriptingEngine:
    """Complete CAD scripting engine with Ruby/Lua/R patterns."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.meta_engine = MetaprogrammingEngine()
        self.dsl_builder = CADDSLBuilder(self.meta_engine)
        self.dsl_interpreter = DSLInterpreter(self.meta_engine)
        self.stats_engine = StatisticalAnalysisEngine()
        self.config_system = LuaStyleConfiguration()
        self.script_cache: Dict[str, Any] = {}

    def execute_cad_script(self, script: str, language: str = "ruby_dsl") -> Result[Any]:
        """Execute CAD script in specified language."""
        try:
            if language == "ruby_dsl":
                return self._execute_ruby_dsl(script)
            elif language == "lua_config":
                return self._execute_lua_config(script)
            elif language == "r_analysis":
                return self._execute_r_analysis(script)
            else:
                return Result.err(ValueError(f"Unsupported language: {language}"))

        except Exception as e:
            return Result.err(e)

    def _execute_ruby_dsl(self, script: str) -> Result[Any]:
        """Execute Ruby-style DSL script."""
        # Create DSL context
        dsl = self.dsl_builder.create_cad_dsl("ruby_script")

        # Add CAD functions to DSL context
        self._register_cad_functions(dsl)

        # Execute script in DSL context
        result = dsl.interpret_dsl(script)

        return result

    def _execute_lua_config(self, script: str) -> Result[Any]:
        """Execute Lua-style configuration script."""
        # Parse Lua-style configuration
        lines = script.strip().split('\n')
        config_tables = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith('--'):
                continue

            # Parse table assignment
            match = re.match(r'(\w+)\s*=\s*\{([^}]*)\}', line)
            if match:
                table_name, table_content = match.groups()
                config_data = self.dsl_interpreter._parse_table_content(table_content)
                config_tables[table_name] = config_data

        # Create configuration tables
        for table_name, config_data in config_tables.items():
            self.config_system.create_config_table(table_name, config_data)

        return Result.ok(config_tables)

    def _execute_r_analysis(self, script: str) -> Result[Any]:
        """Execute R-style analysis script."""
        # Parse R-style commands
        lines = script.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Parse R-style assignments
            if '<-' in line:
                var_name, expression = line.split('<-', 1)
                var_name = var_name.strip()
                expression = expression.strip()

                # Evaluate expression
                try:
                    value = eval(expression, {"__builtins__": {}}, self.stats_engine.datasets)
                    self.stats_engine.datasets[var_name] = value
                except Exception as e:
                    self.logger.error(f"R expression evaluation failed: {e}")

            # Parse function calls
            elif '(' in line and ')' in line:
                func_call = line
                try:
                    # Simple evaluation of R-style function calls
                    result = eval(func_call, {"__builtins__": {}}, {
                        **self.stats_engine.datasets,
                        **self._get_r_functions()
                    })
                    self.logger.info(f"R function result: {result}")
                except Exception as e:
                    self.logger.error(f"R function call failed: {e}")

        return Result.ok(self.stats_engine.datasets)

    def _register_cad_functions(self, dsl: CADDSL) -> None:
        """Register CAD functions in DSL."""
        cad_functions = {
            "cube": dsl.create_cube,
            "sphere": dsl.create_sphere,
            "cylinder": dsl.create_cylinder,
            "translate": dsl._translate_mesh,
            "rotate": dsl._rotate_mesh,
            "scale": dsl._scale_mesh,
            "union": dsl._union_meshes,
            "difference": dsl._difference_meshes,
            "intersection": dsl._intersection_meshes
        }

        for name, func in cad_functions.items():
            self.meta_engine.register_dsl_function(name, func, DSLParadigm.DOMAIN_SPECIFIC)
            dsl.local_variables[name] = func

    def _get_r_functions(self) -> Dict[str, Callable]:
        """Get R-style statistical functions."""
        return {
            "lm": self.stats_engine.linear_regression,
            "cor": self.stats_engine.correlation_analysis,
            "prcomp": self.stats_engine.principal_component_analysis,
            "kmeans": self.stats_engine.cluster_analysis,
            "mean": lambda x: sum(x) / len(x) if x else 0,
            "sd": lambda x: (sum((xi - sum(x)/len(x))**2 for xi in x) / len(x))**0.5 if x else 0,
            "summary": lambda x: {"mean": sum(x)/len(x), "min": min(x), "max": max(x), "length": len(x)} if x else {}
        }

    def create_interactive_shell(self, language: str = "ruby") -> 'InteractiveShell':
        """Create interactive shell for CAD scripting."""
        return InteractiveShell(language, self.meta_engine, self.dsl_builder)


class InteractiveShell:
    """Interactive shell for CAD scripting (REPL equivalent)."""

    def __init__(self, language: str, meta_engine: MetaprogrammingEngine,
                 dsl_builder: CADDSLBuilder):
        self.language = language
        self.meta_engine = meta_engine
        self.dsl_builder = dsl_builder
        self.logger = logging.getLogger(__name__)
        self.session_history: List[str] = []
        self.current_context: Dict[str, Any] = {}

    def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute interactive command."""
        try:
            self.session_history.append(command)

            if self.language == "ruby":
                return self._execute_ruby_command(command)
            elif self.language == "lua":
                return self._execute_lua_command(command)
            elif self.language == "r":
                return self._execute_r_command(command)
            else:
                return {"error": f"Unsupported language: {self.language}"}

        except Exception as e:
            return {"error": str(e)}

    def _execute_ruby_command(self, command: str) -> Dict[str, Any]:
        """Execute Ruby-style command."""
        # Create DSL for this command
        dsl = self.dsl_builder.create_cad_dsl("interactive")

        # Execute command
        result = dsl.interpret_dsl(command)

        if result.is_ok():
            return {"result": result.value, "language": "ruby"}
        else:
            return {"error": str(result.error), "language": "ruby"}

    def _execute_lua_command(self, command: str) -> Dict[str, Any]:
        """Execute Lua-style command."""
        result = self.dsl_interpreter.interpret_dsl(command, self.current_context)

        if result.is_ok():
            return {"result": result.value, "language": "lua"}
        else:
            return {"error": str(result.error), "language": "lua"}

    def _execute_r_command(self, command: str) -> Dict[str, Any]:
        """Execute R-style command."""
        result = self.dsl_interpreter.interpret_dsl(command, self.current_context)

        if result.is_ok():
            return {"result": result.value, "language": "r"}
        else:
            return {"error": str(result.error), "language": "r"}

    def get_session_history(self) -> List[str]:
        """Get session command history."""
        return self.session_history.copy()

    def clear_session(self) -> None:
        """Clear session state."""
        self.session_history.clear()
        self.current_context.clear()


# Factory functions for DSL and metaprogramming
def create_metaprogramming_engine() -> MetaprogrammingEngine:
    """Create metaprogramming engine."""
    return MetaprogrammingEngine()


def create_dsl_interpreter(meta_engine: MetaprogrammingEngine) -> DSLInterpreter:
    """Create DSL interpreter."""
    return DSLInterpreter(meta_engine)


def create_cad_dsl_builder(meta_engine: MetaprogrammingEngine) -> CADDSLBuilder:
    """Create CAD DSL builder."""
    return CADDSLBuilder(meta_engine)


def create_scripting_engine() -> CADScriptingEngine:
    """Create complete CAD scripting engine."""
    return CADScriptingEngine()
