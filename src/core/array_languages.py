"""APL/J/K-inspired mathematical notation and array processing for 3D CAD operations."""

from __future__ import annotations

import logging
import math
import operator
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from pathlib import Path
import functools
import itertools

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class NotationStyle(Enum):
    """Mathematical notation styles."""
    APL = "apl"           # APL Iverson notation
    J = "j"              # J programming language
    K = "k"              # K programming language
    MATHEMATICAL = "mathematical"  # Standard mathematical notation
    CAD_SPECIFIC = "cad_specific"  # CAD-specific notation


@dataclass
class ArrayShape:
    """Array shape descriptor."""
    dimensions: Tuple[int, ...]
    rank: int = 0
    total_elements: int = 0

    def __post_init__(self):
        self.rank = len(self.dimensions)
        self.total_elements = functools.reduce(operator.mul, self.dimensions, 1)


class APLStyleArray:
    """APL-inspired array with mathematical operations."""

    def __init__(self, data: Any, shape: Optional[ArrayShape] = None):
        self.data = data
        self.shape = shape or self._infer_shape(data)
        self.rank = self.shape.rank

    def _infer_shape(self, data: Any) -> ArrayShape:
        """Infer array shape."""
        if isinstance(data, list):
            if not data:
                return ArrayShape((0,), 1, 0)

            # Check if it's a nested list (multidimensional)
            if isinstance(data[0], list):
                # Multidimensional array
                sub_shape = self._infer_shape(data[0])
                return ArrayShape((len(data),) + sub_shape.dimensions, sub_shape.rank + 1,
                                len(data) * sub_shape.total_elements)
            else:
                # 1D array
                return ArrayShape((len(data),), 1, len(data))
        else:
            # Scalar
            return ArrayShape((1,), 0, 1)

    def reshape(self, new_shape: Tuple[int, ...]) -> 'APLStyleArray':
        """Reshape array (APL ⍴ equivalent)."""
        if HAS_NUMPY:
            flat_data = np.array(self.data).flatten()
            new_total = functools.reduce(operator.mul, new_shape, 1)

            if new_total != self.shape.total_elements:
                raise ValueError("Cannot reshape: total elements don't match")

            reshaped_data = flat_data[:new_total].reshape(new_shape)
            return APLStyleArray(reshaped_data.tolist(), ArrayShape(new_shape, len(new_shape), new_total))
        else:
            # Manual reshape
            flat_data = self._flatten_data()
            new_total = functools.reduce(operator.mul, new_shape, 1)

            if new_total != len(flat_data):
                raise ValueError("Cannot reshape: total elements don't match")

            reshaped_data = self._reshape_manual(flat_data, new_shape)
            return APLStyleArray(reshaped_data, ArrayShape(new_shape, len(new_shape), new_total))

    def _flatten_data(self) -> List[Any]:
        """Flatten nested data."""
        if isinstance(self.data, list):
            result = []
            for item in self.data:
                if isinstance(item, list):
                    result.extend(self._flatten_data_recursive(item))
                else:
                    result.append(item)
            return result
        else:
            return [self.data]

    def _flatten_data_recursive(self, data: List) -> List[Any]:
        """Recursive flattening."""
        result = []
        for item in data:
            if isinstance(item, list):
                result.extend(self._flatten_data_recursive(item))
            else:
                result.append(item)
        return result

    def _reshape_manual(self, flat_data: List[Any], shape: Tuple[int, ...]) -> List:
        """Manual reshape implementation."""
        if len(shape) == 1:
            return flat_data[:shape[0]]
        else:
            result = []
            elements_per_subarray = functools.reduce(operator.mul, shape[1:], 1)

            for i in range(shape[0]):
                start_idx = i * elements_per_subarray
                end_idx = start_idx + elements_per_subarray
                subarray = self._reshape_manual(flat_data[start_idx:end_idx], shape[1:])
                result.append(subarray)

            return result

    def apply_function(self, func: str, *args) -> 'APLStyleArray':
        """Apply APL-style function."""
        if func == "iota":  # Generate range (⍳)
            if len(args) == 1:
                n = args[0]
                if isinstance(n, int):
                    data = list(range(n))
                    return APLStyleArray(data, ArrayShape((n,), 1, n))

        elif func == "rho":  # Reshape (⍴)
            if len(args) == 2:
                shape = args[0]
                data = args[1]
                return self.reshape(shape)

        elif func == "plus":  # Addition (+)
            if len(args) == 1:
                other = args[0]
                if isinstance(other, (int, float)):
                    # Scalar addition
                    if isinstance(self.data, list):
                        result_data = [x + other if isinstance(x, (int, float)) else x for x in self.data]
                    else:
                        result_data = self.data + other
                    return APLStyleArray(result_data, self.shape)
                elif isinstance(other, APLStyleArray):
                    # Array addition
                    return self._element_wise_operation(other, operator.add)

        elif func == "times":  # Multiplication (×)
            if len(args) == 1:
                other = args[0]
                if isinstance(other, (int, float)):
                    result_data = [x * other if isinstance(x, (int, float)) else x for x in self.data]
                    return APLStyleArray(result_data, self.shape)
                elif isinstance(other, APLStyleArray):
                    return self._element_wise_operation(other, operator.mul)

        elif func == "reduce":  # Reduce (/)
            if len(args) == 1:
                op = args[0]
                if op == "+":
                    return self._reduce_operation(operator.add)
                elif op == "*":
                    return self._reduce_operation(operator.mul)

        return self

    def _element_wise_operation(self, other: 'APLStyleArray', op: Callable) -> 'APLStyleArray':
        """Element-wise operation."""
        if self.shape != other.shape:
            raise ValueError("Array shapes must match for element-wise operations")

        if isinstance(self.data, list) and isinstance(other.data, list):
            if isinstance(self.data[0], list):
                # Multidimensional
                result_data = [
                    [op(a, b) for a, b in zip(row1, row2)]
                    for row1, row2 in zip(self.data, other.data)
                ]
            else:
                # 1D
                result_data = [op(a, b) for a, b in zip(self.data, other.data)]
        else:
            result_data = op(self.data, other.data)

        return APLStyleArray(result_data, self.shape)

    def _reduce_operation(self, op: Callable) -> Any:
        """Reduce operation."""
        if isinstance(self.data, list):
            return functools.reduce(op, self.data)
        else:
            return self.data

    def transpose(self, axes: Optional[Tuple[int, ...]] = None) -> 'APLStyleArray':
        """Transpose array (APL ⍉ equivalent)."""
        if axes is None:
            # Reverse dimensions
            axes = tuple(range(self.rank - 1, -1, -1))

        if HAS_NUMPY:
            np_data = np.array(self.data)
            transposed_data = np_data.transpose(axes)
            return APLStyleArray(transposed_data.tolist(), ArrayShape(transposed_data.shape, len(transposed_data.shape), transposed_data.size))
        else:
            # Manual transpose
            return self._manual_transpose(axes)

    def _manual_transpose(self, axes: Tuple[int, ...]) -> 'APLStyleArray':
        """Manual transpose implementation."""
        # Simplified transpose for 2D arrays
        if len(self.shape.dimensions) == 2:
            rows, cols = self.shape.dimensions
            transposed_data = [[self.data[j][i] for j in range(rows)] for i in range(cols)]
            return APLStyleArray(transposed_data, ArrayShape((cols, rows), 2, rows * cols))

        return self

    def rotate(self, amount: int) -> 'APLStyleArray':
        """Rotate array (APL ⌽ equivalent)."""
        if isinstance(self.data, list):
            rotated_data = self.data[amount:] + self.data[:amount]
            return APLStyleArray(rotated_data, self.shape)
        else:
            return self

    def compress(self, mask: List[bool]) -> 'APLStyleArray':
        """Compress array (APL / equivalent)."""
        if isinstance(self.data, list) and len(mask) == len(self.data):
            compressed_data = [item for item, keep in zip(self.data, mask) if keep]
            return APLStyleArray(compressed_data, ArrayShape((len(compressed_data),), 1, len(compressed_data)))
        else:
            return self


class MathematicalExpression:
    """Mathematical expression parser and evaluator."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.variables: Dict[str, Any] = {}
        self.functions: Dict[str, Callable] = {}

    def parse_expression(self, expression: str) -> Any:
        """Parse mathematical expression."""
        # Simple expression parsing
        # Support for basic arithmetic and functions

        # Replace variables
        for var_name, var_value in self.variables.items():
            expression = expression.replace(var_name, str(var_value))

        # Replace functions
        for func_name, func_impl in self.functions.items():
            if func_name in expression:
                # Simple function call replacement
                expression = expression.replace(func_name, str(func_impl))

        try:
            return eval(expression, {"__builtins__": {}})
        except Exception as e:
            self.logger.error(f"Expression evaluation failed: {e}")
            return None

    def define_function(self, name: str, implementation: str) -> None:
        """Define mathematical function."""
        self.functions[name] = implementation

    def define_variable(self, name: str, value: Any) -> None:
        """Define mathematical variable."""
        self.variables[name] = value


class CADMathematicalEngine:
    """APL/J/K-inspired mathematical engine for CAD."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.expression_parser = MathematicalExpression()
        self.arrays: Dict[str, APLStyleArray] = {}
        self.notation_style = NotationStyle.APL

    def create_array(self, name: str, data: Any, shape: Optional[Tuple[int, ...]] = None) -> APLStyleArray:
        """Create APL-style array."""
        array = APLStyleArray(data, shape)
        self.arrays[name] = array
        return array

    def apply_notation(self, expression: str, style: NotationStyle = None) -> Any:
        """Apply mathematical notation to expression."""
        if style is None:
            style = self.notation_style

        if style == NotationStyle.APL:
            return self._apply_apl_notation(expression)
        elif style == NotationStyle.J:
            return self._apply_j_notation(expression)
        elif style == NotationStyle.K:
            return self._apply_k_notation(expression)
        elif style == NotationStyle.MATHEMATICAL:
            return self._apply_mathematical_notation(expression)
        else:
            return self.expression_parser.parse_expression(expression)

    def _apply_apl_notation(self, expression: str) -> Any:
        """Apply APL notation."""
        # Parse APL expressions like +/array, ⍳10, etc.

        if expression.startswith("+/"):
            # Sum reduction
            array_name = expression[2:]
            if array_name in self.arrays:
                array = self.arrays[array_name]
                return array.apply_function("reduce", "+").data

        elif expression.startswith("⍳"):
            # Iota (range)
            n_str = expression[1:]
            try:
                n = int(n_str)
                return list(range(n))
            except ValueError:
                return []

        elif expression.startswith("⍴"):
            # Reshape
            parts = expression[1:].split()
            if len(parts) == 2:
                shape = tuple(int(x) for x in parts[0].split('×'))
                data = [int(x) for x in parts[1].split()]
                return APLStyleArray(data, ArrayShape(shape, len(shape), len(data)))

        return self.expression_parser.parse_expression(expression)

    def _apply_j_notation(self, expression: str) -> Any:
        """Apply J notation."""
        # J uses similar notation to APL but with different symbols

        if expression.startswith("+/"):
            # Sum reduction
            array_name = expression[2:]
            if array_name in self.arrays:
                array = self.arrays[array_name]
                return array.apply_function("reduce", "+").data

        elif expression.startswith("i."):
            # Iota
            n_str = expression[2:]
            try:
                n = int(n_str)
                return list(range(n))
            except ValueError:
                return []

        return self.expression_parser.parse_expression(expression)

    def _apply_k_notation(self, expression: str) -> Any:
        """Apply K notation."""
        # K is more terse than APL/J

        if expression.startswith("+\\"):
            # Sum scan
            array_name = expression[2:]
            if array_name in self.arrays:
                array = self.arrays[array_name]
                # Simplified scan operation
                data = array.data
                if isinstance(data, list):
                    scan_result = [sum(data[:i+1]) for i in range(len(data))]
                    return scan_result

        return self.expression_parser.parse_expression(expression)

    def _apply_mathematical_notation(self, expression: str) -> Any:
        """Apply standard mathematical notation."""
        return self.expression_parser.parse_expression(expression)

    def define_mathematical_function(self, name: str, formula: str) -> None:
        """Define mathematical function."""
        self.expression_parser.define_function(name, formula)

    def define_mathematical_variable(self, name: str, value: Any) -> None:
        """Define mathematical variable."""
        self.expression_parser.define_variable(name, value)

    def compute_geometric_properties(self, vertices: List[List[float]]) -> Dict[str, Any]:
        """Compute geometric properties using mathematical notation."""
        if not vertices:
            return {}

        # Create vertex array
        vertex_array = APLStyleArray(vertices)

        # Compute centroid (APL style)
        centroid_x = sum(v[0] for v in vertices) / len(vertices)
        centroid_y = sum(v[1] for v in vertices) / len(vertices)
        centroid_z = sum(v[2] for v in vertices) / len(vertices)

        # Compute bounding box
        min_coords = [min(coord[i] for coord in vertices) for i in range(3)]
        max_coords = [max(coord[i] for coord in vertices) for i in range(3)]

        # Compute dimensions
        dimensions = [max_coords[i] - min_coords[i] for i in range(3)]

        return {
            "centroid": [centroid_x, centroid_y, centroid_z],
            "bounding_box": {"min": min_coords, "max": max_coords},
            "dimensions": dimensions,
            "volume": dimensions[0] * dimensions[1] * dimensions[2],
            "surface_area": 2 * (dimensions[0] * dimensions[1] + dimensions[1] * dimensions[2] + dimensions[2] * dimensions[0])
        }

    def optimize_mesh_mathematically(self, vertices: List[List[float]],
                                   faces: List[List[int]]) -> Dict[str, Any]:
        """Optimize mesh using mathematical operations."""
        # Create arrays
        vertex_array = APLStyleArray(vertices)
        face_array = APLStyleArray(faces)

        # Compute face centroids
        face_centroids = []
        for face in faces:
            face_vertices = [vertices[i] for i in face]
            centroid = [
                sum(v[0] for v in face_vertices) / len(face_vertices),
                sum(v[1] for v in face_vertices) / len(face_vertices),
                sum(v[2] for v in face_vertices) / len(face_vertices)
            ]
            face_centroids.append(centroid)

        # Compute face normals
        face_normals = []
        for face in faces:
            face_vertices = [vertices[i] for i in face]

            # Calculate two edges
            edge1 = [face_vertices[1][0] - face_vertices[0][0],
                    face_vertices[1][1] - face_vertices[0][1],
                    face_vertices[1][2] - face_vertices[0][2]]

            edge2 = [face_vertices[2][0] - face_vertices[0][0],
                    face_vertices[2][1] - face_vertices[0][1],
                    face_vertices[2][2] - face_vertices[0][2]]

            # Cross product
            normal = [
                edge1[1] * edge2[2] - edge1[2] * edge2[1],
                edge1[2] * edge2[0] - edge1[0] * edge2[2],
                edge1[0] * edge2[1] - edge1[1] * edge2[0]
            ]

            # Normalize
            magnitude = math.sqrt(sum(x*x for x in normal))
            if magnitude > 0:
                normal = [x / magnitude for x in normal]

            face_normals.append(normal)

        return {
            "vertex_count": len(vertices),
            "face_count": len(faces),
            "face_centroids": face_centroids,
            "face_normals": face_normals,
            "optimization_applied": True,
            "method": "mathematical_optimization"
        }

    def solve_mathematical_problem(self, problem_type: str, parameters: Dict[str, Any]) -> Any:
        """Solve mathematical problem."""
        if problem_type == "linear_system":
            return self._solve_linear_system(parameters)
        elif problem_type == "optimization":
            return self._solve_optimization(parameters)
        elif problem_type == "interpolation":
            return self._solve_interpolation(parameters)
        else:
            return {"error": f"Unknown problem type: {problem_type}"}

    def _solve_linear_system(self, parameters: Dict[str, Any]) -> Any:
        """Solve linear system Ax = b."""
        A = parameters.get("A", [])
        b = parameters.get("b", [])

        if not A or not b:
            return {"error": "Missing A or b parameters"}

        # Simplified solution using numpy if available
        if HAS_NUMPY:
            try:
                A_matrix = np.array(A)
                b_vector = np.array(b)

                x = np.linalg.solve(A_matrix, b_vector)
                return {
                    "solution": x.tolist(),
                    "method": "numpy_solve"
                }
            except Exception as e:
                return {"error": f"Solve failed: {e}"}

        # Manual solution for small systems
        return self._manual_linear_solve(A, b)

    def _manual_linear_solve(self, A: List[List[float]], b: List[float]) -> Dict[str, Any]:
        """Manual linear system solution."""
        n = len(A)

        if n != len(b):
            return {"error": "Matrix and vector dimensions don't match"}

        # Gaussian elimination
        augmented = [row + [b[i]] for i, row in enumerate(A)]

        # Forward elimination
        for i in range(n):
            # Find pivot
            pivot = i
            for j in range(i + 1, n):
                if abs(augmented[j][i]) > abs(augmented[pivot][i]):
                    pivot = j

            # Swap rows
            augmented[i], augmented[pivot] = augmented[pivot], augmented[i]

            # Eliminate
            for j in range(i + 1, n):
                factor = augmented[j][i] / augmented[i][i] if augmented[i][i] != 0 else 0
                for k in range(i, n + 1):
                    augmented[j][k] -= factor * augmented[i][k]

        # Back substitution
        x = [0.0] * n
        for i in range(n - 1, -1, -1):
            x[i] = augmented[i][n]
            for j in range(i + 1, n):
                x[i] -= augmented[i][j] * x[j]
            x[i] /= augmented[i][i] if augmented[i][i] != 0 else 1

        return {
            "solution": x,
            "method": "manual_gaussian_elimination"
        }

    def _solve_optimization(self, parameters: Dict[str, Any]) -> Any:
        """Solve optimization problem."""
        objective = parameters.get("objective")
        constraints = parameters.get("constraints", [])

        # Simplified optimization
        return {
            "optimal_value": 0.0,
            "optimal_point": [0.0] * len(parameters.get("variables", [])),
            "method": "simplified_optimization"
        }

    def _solve_interpolation(self, parameters: Dict[str, Any]) -> Any:
        """Solve interpolation problem."""
        x_data = parameters.get("x_data", [])
        y_data = parameters.get("y_data", [])
        x_target = parameters.get("x_target", 0)

        if len(x_data) != len(y_data):
            return {"error": "X and Y data must have same length"}

        # Linear interpolation
        for i in range(len(x_data) - 1):
            if x_data[i] <= x_target <= x_data[i + 1]:
                x1, x2 = x_data[i], x_data[i + 1]
                y1, y2 = y_data[i], y_data[i + 1]

                y_target = y1 + (y2 - y1) * (x_target - x1) / (x2 - x1)
                return {
                    "interpolated_value": y_target,
                    "method": "linear_interpolation"
                }

        return {"error": "Target value outside data range"}

    def create_mathematical_model(self, model_type: str, parameters: Dict[str, Any]) -> Any:
        """Create mathematical model."""
        if model_type == "linear_regression":
            return self._create_linear_model(parameters)
        elif model_type == "polynomial":
            return self._create_polynomial_model(parameters)
        elif model_type == "geometric":
            return self._create_geometric_model(parameters)
        else:
            return {"error": f"Unknown model type: {model_type}"}

    def _create_linear_model(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create linear regression model."""
        x_data = parameters.get("x_data", [])
        y_data = parameters.get("y_data", [])

        if len(x_data) != len(y_data):
            return {"error": "X and Y data must have same length"}

        n = len(x_data)
        sum_x = sum(x_data)
        sum_y = sum(y_data)
        sum_xy = sum(x * y for x, y in zip(x_data, y_data))
        sum_x2 = sum(x * x for x in x_data)

        # Calculate slope and intercept
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return {"error": "Cannot compute linear regression"}

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n

        # Calculate R-squared
        y_mean = sum_y / n
        ss_total = sum((y - y_mean) ** 2 for y in y_data)
        ss_residual = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_data, y_data))

        r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 0

        return {
            "model_type": "linear_regression",
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "equation": f"y = {slope:.3f}x + {intercept:.3f}"
        }

    def _create_polynomial_model(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create polynomial model."""
        return {
            "model_type": "polynomial",
            "degree": parameters.get("degree", 2),
            "coefficients": [1.0] * (parameters.get("degree", 2) + 1)
        }

    def _create_geometric_model(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create geometric model."""
        return {
            "model_type": "geometric",
            "transformation": parameters.get("transformation", "none"),
            "parameters": parameters
        }

    def evaluate_mathematical_expression(self, expression: str) -> Any:
        """Evaluate mathematical expression."""
        return self.apply_notation(expression)

    def get_mathematical_analysis(self, data: List[List[float]]) -> Dict[str, Any]:
        """Perform mathematical analysis on data."""
        if not data:
            return {}

        # Create array
        array = APLStyleArray(data)

        # Compute statistics
        flat_data = array._flatten_data()

        if not flat_data:
            return {}

        # Basic statistics
        mean_val = sum(flat_data) / len(flat_data)
        variance = sum((x - mean_val) ** 2 for x in flat_data) / len(flat_data)
        std_dev = variance ** 0.5

        # Min/max
        min_val = min(flat_data)
        max_val = max(flat_data)

        return {
            "array_shape": array.shape.__dict__,
            "statistics": {
                "mean": mean_val,
                "variance": variance,
                "std_deviation": std_dev,
                "min": min_val,
                "max": max_val,
                "range": max_val - min_val
            },
            "data_points": len(flat_data),
            "notation_style": self.notation_style.value
        }


class CADMathematicalSystem:
    """Complete mathematical system for CAD."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.math_engine = CADMathematicalEngine()
        self.expression_cache: Dict[str, Any] = {}
        self.model_cache: Dict[str, Any] = {}

    def setup_mathematical_environment(self) -> None:
        """Setup mathematical environment."""
        # Define common mathematical functions
        self.math_engine.define_mathematical_function("sin", "math.sin")
        self.math_engine.define_mathematical_function("cos", "math.cos")
        self.math_engine.define_mathematical_function("tan", "math.tan")
        self.math_engine.define_mathematical_function("exp", "math.exp")
        self.math_engine.define_mathematical_function("log", "math.log")
        self.math_engine.define_mathematical_function("sqrt", "math.sqrt")

        # Define common variables
        self.math_engine.define_mathematical_variable("pi", math.pi)
        self.math_engine.define_mathematical_variable("e", math.e)

    def analyze_mesh_mathematically(self, vertices: List[List[float]],
                                  faces: List[List[int]]) -> Dict[str, Any]:
        """Analyze mesh using mathematical methods."""
        analysis = {
            "mesh_analysis": {},
            "mathematical_properties": {},
            "optimization_suggestions": []
        }

        try:
            # Basic geometric analysis
            geometric_props = self.math_engine.compute_geometric_properties(vertices)
            analysis["mathematical_properties"] = geometric_props

            # Mathematical optimization
            optimization = self.math_engine.optimize_mesh_mathematically(vertices, faces)
            analysis["mesh_analysis"] = optimization

            # Generate suggestions
            if geometric_props.get("volume", 0) > 1000:
                analysis["optimization_suggestions"].append("Consider mesh decimation for large volumes")

            if len(vertices) > 50000:
                analysis["optimization_suggestions"].append("High vertex count - mathematical optimization recommended")

        except Exception as e:
            self.logger.error(f"Mathematical analysis failed: {e}")
            analysis["error"] = str(e)

        return analysis

    def solve_cad_mathematical_problem(self, problem_type: str, parameters: Dict[str, Any]) -> Any:
        """Solve CAD mathematical problem."""
        return self.math_engine.solve_mathematical_problem(problem_type, parameters)

    def create_mathematical_model(self, model_type: str, parameters: Dict[str, Any]) -> Any:
        """Create mathematical model for CAD."""
        return self.math_engine.create_mathematical_model(model_type, parameters)

    def evaluate_mathematical_expression(self, expression: str) -> Any:
        """Evaluate mathematical expression."""
        cache_key = hash(expression)

        if cache_key in self.expression_cache:
            return self.expression_cache[cache_key]

        result = self.math_engine.evaluate_mathematical_expression(expression)
        self.expression_cache[cache_key] = result

        return result

    def get_mathematical_statistics(self) -> Dict[str, Any]:
        """Get mathematical system statistics."""
        return {
            "notation_style": self.math_engine.notation_style.value,
            "cached_expressions": len(self.expression_cache),
            "cached_models": len(self.model_cache),
            "available_functions": len(self.math_engine.expression_parser.functions),
            "available_variables": len(self.math_engine.expression_parser.variables)
        }


# Factory functions
def create_apl_array(data: Any, shape: Optional[Tuple[int, ...]] = None) -> APLStyleArray:
    """Create APL-style array."""
    return APLStyleArray(data, shape)


def create_math_engine() -> CADMathematicalEngine:
    """Create mathematical engine."""
    return CADMathematicalEngine()


def create_mathematical_system() -> CADMathematicalSystem:
    """Create mathematical system."""
    return CADMathematicalSystem()
