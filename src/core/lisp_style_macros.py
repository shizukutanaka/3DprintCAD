"""Lisp/Scheme-inspired macro system and metaprogramming for 3D CAD operations."""

from __future__ import annotations

import ast
import logging
import operator
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Type, TypeVar
from pathlib import Path


T = TypeVar('T')


class LispSyntax(Enum):
    """Lisp syntax elements."""
    SYMBOL = "symbol"
    LIST = "list"
    ATOM = "atom"
    QUOTE = "quote"
    QUASIQUOTE = "quasiquote"
    UNQUOTE = "unquote"
    LAMBDA = "lambda"
    MACRO = "macro"


@dataclass
class LispSymbol:
    """Lisp symbol (atom) equivalent."""
    name: str
    value: Any = None
    is_bound: bool = False

    def __repr__(self) -> str:
        return self.name


@dataclass
class LispList:
    """Lisp list (cons cell) equivalent."""
    car: Any  # First element
    cdr: Any  # Rest of list

    def __repr__(self) -> str:
        return f"({self._to_string()})"

    def _to_string(self) -> str:
        result = []
        current = self

        while current is not None:
            if isinstance(current, LispList):
                result.append(str(current.car))
                current = current.cdr
            else:
                result.append(str(current))
                break

        return " ".join(result)


class LispEnvironment:
    """Lisp environment for variable bindings."""

    def __init__(self, parent: Optional['LispEnvironment'] = None):
        self.parent = parent
        self.bindings: Dict[str, Any] = {}
        self.macros: Dict[str, Callable] = {}

    def lookup(self, symbol: str) -> Any:
        """Lookup symbol in environment."""
        if symbol in self.bindings:
            return self.bindings[symbol]

        if self.parent:
            return self.parent.lookup(symbol)

        raise NameError(f"Undefined symbol: {symbol}")

    def define(self, symbol: str, value: Any) -> None:
        """Define symbol in environment."""
        self.bindings[symbol] = value

    def set(self, symbol: str, value: Any) -> None:
        """Set symbol value."""
        if symbol in self.bindings:
            self.bindings[symbol] = value
        elif self.parent:
            self.parent.set(symbol, value)
        else:
            raise NameError(f"Undefined symbol: {symbol}")

    def define_macro(self, name: str, macro_func: Callable) -> None:
        """Define macro."""
        self.macros[name] = macro_func

    def lookup_macro(self, name: str) -> Optional[Callable]:
        """Lookup macro."""
        if name in self.macros:
            return self.macros[name]

        if self.parent:
            return self.parent.lookup_macro(name)

        return None


class LispMacroExpander:
    """Lisp macro expansion system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.environment = LispEnvironment()
        self.expansion_cache: Dict[str, Any] = {}

    def expand_macros(self, expression: Any, env: Optional[LispEnvironment] = None) -> Any:
        """Expand macros in expression."""
        if env is None:
            env = self.environment

        try:
            if isinstance(expression, LispList):
                return self._expand_list_macros(expression, env)
            elif isinstance(expression, list):
                return [self.expand_macros(item, env) for item in expression]
            else:
                return expression

        except Exception as e:
            self.logger.error(f"Macro expansion failed: {e}")
            return expression

    def _expand_list_macros(self, lst: LispList, env: LispEnvironment) -> Any:
        """Expand macros in list."""
        if lst.car == "quote":
            # Don't expand quoted expressions
            return lst
        elif lst.car == "quasiquote":
            # Handle quasiquote expansion
            return self._expand_quasiquote(lst.cdr, env)
        elif lst.car in env.macros:
            # Expand macro
            macro_func = env.macros[lst.car]
            return self._expand_macro_call(macro_func, lst, env)
        else:
            # Recursively expand arguments
            expanded_car = self.expand_macros(lst.car, env)
            expanded_cdr = self.expand_macros(lst.cdr, env)
            return LispList(expanded_car, expanded_cdr)

    def _expand_quasiquote(self, expr: Any, env: LispEnvironment) -> Any:
        """Expand quasiquote."""
        if isinstance(expr, LispList) and expr.car == "unquote":
            # Evaluate unquoted expression
            return self.evaluate_expression(expr.cdr.car, env)
        else:
            # Recursively expand
            return self.expand_macros(expr, env)

    def _expand_macro_call(self, macro_func: Callable, call: LispList, env: LispEnvironment) -> Any:
        """Expand macro call."""
        try:
            # Call macro function with arguments
            return macro_func(call, env)
        except Exception as e:
            self.logger.error(f"Macro call failed: {e}")
            return call

    def evaluate_expression(self, expression: Any, env: LispEnvironment) -> Any:
        """Evaluate expression."""
        if isinstance(expression, LispSymbol):
            return env.lookup(expression.name)
        elif isinstance(expression, LispList):
            return self._evaluate_function_call(expression, env)
        elif isinstance(expression, list):
            return [self.evaluate_expression(item, env) for item in expression]
        else:
            return expression

    def _evaluate_function_call(self, call: LispList, env: LispEnvironment) -> Any:
        """Evaluate function call."""
        function_name = call.car

        if isinstance(function_name, LispSymbol):
            func_name = function_name.name
        else:
            func_name = str(function_name)

        # Built-in functions
        if func_name == "+":
            return self._evaluate_arithmetic(call.cdr, operator.add, env)
        elif func_name == "-":
            return self._evaluate_arithmetic(call.cdr, operator.sub, env)
        elif func_name == "*":
            return self._evaluate_arithmetic(call.cdr, operator.mul, env)
        elif func_name == "/":
            return self._evaluate_arithmetic(call.cdr, operator.truediv, env)
        elif func_name == "car":
            return self._evaluate_car(call.cdr, env)
        elif func_name == "cdr":
            return self._evaluate_cdr(call.cdr, env)
        elif func_name == "cons":
            return self._evaluate_cons(call.cdr, env)
        elif func_name == "list":
            return self._evaluate_list(call.cdr, env)
        else:
            # User-defined function
            func = env.lookup(func_name)
            if callable(func):
                args = self._evaluate_arguments(call.cdr, env)
                return func(*args)

        return None

    def _evaluate_arithmetic(self, args: Any, op: Callable, env: LispEnvironment) -> Any:
        """Evaluate arithmetic expression."""
        if args is None:
            return 0

        values = []
        current = args

        while current is not None:
            if isinstance(current, LispList):
                value = self.evaluate_expression(current.car, env)
                values.append(value)
                current = current.cdr
            else:
                value = self.evaluate_expression(current, env)
                values.append(value)
                break

        if not values:
            return 0

        result = values[0]
        for value in values[1:]:
            result = op(result, value)

        return result

    def _evaluate_car(self, args: Any, env: LispEnvironment) -> Any:
        """Evaluate car (first element)."""
        if args is None:
            return None

        if isinstance(args, LispList):
            return self.evaluate_expression(args.car, env)
        else:
            return self.evaluate_expression(args, env)

    def _evaluate_cdr(self, args: Any, env: LispEnvironment) -> Any:
        """Evaluate cdr (rest of list)."""
        if args is None:
            return None

        if isinstance(args, LispList):
            return args.cdr
        else:
            return None

    def _evaluate_cons(self, args: Any, env: LispEnvironment) -> Any:
        """Evaluate cons (construct list)."""
        if args is None or not isinstance(args, LispList):
            return None

        car_value = self.evaluate_expression(args.car, env)
        cdr_value = self.evaluate_expression(args.cdr, env)

        return LispList(car_value, cdr_value)

    def _evaluate_list(self, args: Any, env: LispEnvironment) -> List[Any]:
        """Evaluate list creation."""
        result = []
        current = args

        while current is not None:
            if isinstance(current, LispList):
                value = self.evaluate_expression(current.car, env)
                result.append(value)
                current = current.cdr
            else:
                value = self.evaluate_expression(current, env)
                result.append(value)
                break

        return result

    def _evaluate_arguments(self, args: Any, env: LispEnvironment) -> List[Any]:
        """Evaluate function arguments."""
        result = []
        current = args

        while current is not None:
            if isinstance(current, LispList):
                value = self.evaluate_expression(current.car, env)
                result.append(value)
                current = current.cdr
            else:
                value = self.evaluate_expression(current, env)
                result.append(value)
                break

        return result


class CADMacroSystem:
    """Lisp-inspired macro system for CAD operations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.macro_expander = LispMacroExpander()
        self.cad_macros: Dict[str, Callable] = {}
        self.macro_registry: Dict[str, Dict[str, Any]] = {}

    def define_cad_macro(self, name: str, macro_func: Callable,
                        description: str = "") -> None:
        """Define CAD macro."""
        self.cad_macros[name] = macro_func

        self.macro_registry[name] = {
            "function": macro_func,
            "description": description,
            "created_at": time.time(),
            "usage_count": 0
        }

        # Register in Lisp environment
        self.macro_expander.environment.define_macro(name, macro_func)

        self.logger.info(f"Defined CAD macro: {name}")

    def expand_macro(self, macro_call: str, context: Dict[str, Any]) -> Any:
        """Expand macro call."""
        try:
            # Parse macro call
            parsed_call = self._parse_macro_call(macro_call)

            # Expand using Lisp macro system
            expanded = self.macro_expander.expand_macros(parsed_call)

            # Update usage count
            if parsed_call.car in self.macro_registry:
                self.macro_registry[parsed_call.car]["usage_count"] += 1

            return expanded

        except Exception as e:
            self.logger.error(f"Macro expansion failed: {e}")
            return macro_call

    def _parse_macro_call(self, call: str) -> LispList:
        """Parse macro call string into Lisp structure."""
        # Simple parsing - in real implementation would be more sophisticated
        # For now, assume simple (function arg1 arg2) format

        # Remove parentheses
        call = call.strip()
        if call.startswith('(') and call.endswith(')'):
            call = call[1:-1]

        parts = call.split()
        if not parts:
            return LispList("empty", None)

        # Create Lisp list structure
        head = LispSymbol(parts[0])
        current = LispList(head, None)

        tail = current
        for part in parts[1:]:
            if part.isdigit():
                value = int(part)
            elif part.replace('.', '').isdigit():
                value = float(part)
            else:
                value = LispSymbol(part)

            new_node = LispList(value, None)
            tail.cdr = new_node
            tail = new_node

        return current

    def create_mesh_generation_macro(self) -> Callable:
        """Create mesh generation macro."""
        def mesh_gen_macro(call: LispList, env: LispEnvironment) -> Any:
            """Macro for mesh generation."""
            if call.car == "generate_mesh":
                # Generate mesh code
                mesh_code = """
                def generated_mesh():
                    vertices = []
                    faces = []

                    # Generate cube vertices
                    for x in [-1, 1]:
                        for y in [-1, 1]:
                            for z in [-1, 1]:
                                vertices.append([x, y, z])

                    # Generate cube faces
                    faces = [
                        [0, 1, 2], [0, 2, 3],  # Bottom
                        [4, 5, 6], [4, 6, 7],  # Top
                        [0, 1, 5], [0, 5, 4],  # Front
                        [1, 2, 6], [1, 6, 5],  # Right
                        [2, 3, 7], [2, 7, 6],  # Back
                        [3, 0, 4], [3, 4, 7]   # Left
                    ]

                    return {"vertices": vertices, "faces": faces}
                """

                return mesh_code

        return mesh_gen_macro

    def create_optimization_macro(self) -> Callable:
        """Create optimization macro."""
        def optimization_macro(call: LispList, env: LispEnvironment) -> Any:
            """Macro for optimization."""
            if call.car == "optimize_mesh":
                # Generate optimization code
                optimization_code = """
                def optimize_mesh(mesh_data):
                    # Remove duplicate vertices
                    vertices = mesh_data.get("vertices", [])
                    faces = mesh_data.get("faces", [])

                    unique_vertices = []
                    vertex_map = {}

                    for i, vertex in enumerate(vertices):
                        vertex_key = tuple(round(v, 6) for v in vertex)
                        if vertex_key not in vertex_map:
                            vertex_map[vertex_key] = len(unique_vertices)
                            unique_vertices.append(vertex)

                    # Remap faces
                    optimized_faces = []
                    for face in faces:
                        optimized_face = [vertex_map[tuple(round(vertices[i], 6) for i in face)] for i in face]
                        optimized_faces.append(optimized_face)

                    return {
                        "vertices": unique_vertices,
                        "faces": optimized_faces,
                        "optimization_applied": True
                    }
                """

                return optimization_code

        return optimization_macro

    def generate_cad_code(self, macro_calls: List[str]) -> str:
        """Generate CAD code from macro calls."""
        generated_code = []

        for macro_call in macro_calls:
            expanded = self.expand_macro(macro_call, {})
            if expanded:
                generated_code.append(str(expanded))

        return "\n".join(generated_code)

    def get_macro_statistics(self) -> Dict[str, Any]:
        """Get macro usage statistics."""
        return {
            "total_macros": len(self.cad_macros),
            "macro_registry": {
                name: {
                    "usage_count": info["usage_count"],
                    "description": info["description"]
                }
                for name, info in self.macro_registry.items()
            },
            "expansion_cache_size": len(self.macro_expander.expansion_cache)
        }


class SchemeStyleEvaluation:
    """Scheme-inspired evaluation system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.global_environment = LispEnvironment()
        self.evaluation_cache: Dict[str, Any] = {}

    def evaluate_scheme_expression(self, expression: str) -> Any:
        """Evaluate Scheme-style expression."""
        cache_key = hash(expression)

        if cache_key in self.evaluation_cache:
            return self.evaluation_cache[cache_key]

        try:
            # Parse expression
            parsed = self._parse_scheme_expression(expression)

            # Evaluate
            result = self._evaluate_parsed_expression(parsed, self.global_environment)

            self.evaluation_cache[cache_key] = result
            return result

        except Exception as e:
            self.logger.error(f"Scheme evaluation failed: {e}")
            return None

    def _parse_scheme_expression(self, expr: str) -> Any:
        """Parse Scheme expression."""
        # Simple parsing - in real implementation would use proper Scheme parser
        expr = expr.strip()

        if expr.startswith('(') and expr.endswith(')'):
            # List expression
            content = expr[1:-1].strip()

            if not content:
                return LispList(None, None)

            parts = self._split_scheme_list(content)
            head = LispSymbol(parts[0])

            current = LispList(head, None)
            tail = current

            for part in parts[1:]:
                if part.startswith('('):
                    # Nested list
                    nested = self._parse_scheme_expression(part)
                    new_node = LispList(nested, None)
                else:
                    # Symbol or atom
                    if part.isdigit():
                        new_node = LispList(int(part), None)
                    elif part.replace('.', '').isdigit():
                        new_node = LispList(float(part), None)
                    elif part == "#t":
                        new_node = LispList(True, None)
                    elif part == "#f":
                        new_node = LispList(False, None)
                    else:
                        new_node = LispList(LispSymbol(part), None)

                tail.cdr = new_node
                tail = new_node

            return current
        else:
            # Atom
            if expr.isdigit():
                return int(expr)
            elif expr.replace('.', '').isdigit():
                return float(expr)
            elif expr == "#t":
                return True
            elif expr == "#f":
                return False
            else:
                return LispSymbol(expr)

    def _split_scheme_list(self, content: str) -> List[str]:
        """Split Scheme list content."""
        parts = []
        current = ""
        paren_depth = 0

        for char in content:
            if char == '(':
                paren_depth += 1
                current += char
            elif char == ')':
                paren_depth -= 1
                current += char
            elif char == ' ' and paren_depth == 0:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char

        if current:
            parts.append(current)

        return parts

    def _evaluate_parsed_expression(self, expr: Any, env: LispEnvironment) -> Any:
        """Evaluate parsed expression."""
        if isinstance(expr, LispSymbol):
            return env.lookup(expr.name)
        elif isinstance(expr, LispList):
            return self._evaluate_list_expression(expr, env)
        else:
            return expr

    def _evaluate_list_expression(self, lst: LispList, env: LispEnvironment) -> Any:
        """Evaluate list expression."""
        if lst.car == "define":
            return self._evaluate_define(lst.cdr, env)
        elif lst.car == "lambda":
            return self._evaluate_lambda(lst.cdr, env)
        elif lst.car == "if":
            return self._evaluate_if(lst.cdr, env)
        elif lst.car == "quote":
            return lst.cdr.car  # Return quoted expression
        else:
            # Function application
            function = self._evaluate_parsed_expression(lst.car, env)
            if callable(function):
                args = self._evaluate_arguments_list(lst.cdr, env)
                return function(*args)

        return None

    def _evaluate_define(self, define_expr: Any, env: LispEnvironment) -> None:
        """Evaluate define expression."""
        if isinstance(define_expr, LispList):
            symbol = define_expr.car
            value_expr = define_expr.cdr

            if isinstance(symbol, LispSymbol):
                value = self._evaluate_parsed_expression(value_expr, env)
                env.define(symbol.name, value)

    def _evaluate_lambda(self, lambda_expr: Any, env: LispEnvironment) -> Callable:
        """Evaluate lambda expression."""
        if isinstance(lambda_expr, LispList):
            parameters = lambda_expr.car
            body = lambda_expr.cdr

            def lambda_function(*args):
                # Create new environment
                lambda_env = LispEnvironment(env)

                # Bind parameters
                if isinstance(parameters, LispList):
                    param_names = []
                    current = parameters
                    while current is not None:
                        if isinstance(current, LispList):
                            if isinstance(current.car, LispSymbol):
                                param_names.append(current.car.name)
                            current = current.cdr
                        else:
                            break

                    for name, arg in zip(param_names, args):
                        lambda_env.define(name, arg)

                # Evaluate body
                result = None
                current = body
                while current is not None:
                    if isinstance(current, LispList):
                        result = self._evaluate_parsed_expression(current.car, lambda_env)
                        current = current.cdr
                    else:
                        result = self._evaluate_parsed_expression(current, lambda_env)
                        break

                return result

            return lambda_function

    def _evaluate_if(self, if_expr: Any, env: LispEnvironment) -> Any:
        """Evaluate if expression."""
        if isinstance(if_expr, LispList):
            condition = self._evaluate_parsed_expression(if_expr.car, env)

            if condition:
                # True branch
                return self._evaluate_parsed_expression(if_expr.cdr.car, env)
            else:
                # False branch
                false_branch = if_expr.cdr.cdr
                if false_branch:
                    return self._evaluate_parsed_expression(false_branch.car, env)

        return None

    def _evaluate_arguments_list(self, args: Any, env: LispEnvironment) -> List[Any]:
        """Evaluate argument list."""
        result = []

        if args is None:
            return result

        current = args
        while current is not None:
            if isinstance(current, LispList):
                value = self._evaluate_parsed_expression(current.car, env)
                result.append(value)
                current = current.cdr
            else:
                value = self._evaluate_parsed_expression(current, env)
                result.append(value)
                break

        return result


class LispStyleCADSystem:
    """Complete Lisp/Scheme-inspired CAD system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.macro_system = CADMacroSystem()
        self.scheme_evaluator = SchemeStyleEvaluation()
        self.generated_code: List[str] = []
        self.macro_usage: Dict[str, int] = defaultdict(int)

    def initialize_cad_macros(self) -> None:
        """Initialize CAD-specific macros."""
        # Define mesh generation macro
        self.macro_system.define_cad_macro(
            "generate_mesh",
            self.macro_system.create_mesh_generation_macro(),
            "Generate 3D mesh code"
        )

        # Define optimization macro
        self.macro_system.define_cad_macro(
            "optimize_mesh",
            self.macro_system.create_optimization_macro(),
            "Optimize mesh code"
        )

        # Define transformation macros
        self.macro_system.define_cad_macro(
            "transform_mesh",
            self._create_transformation_macro(),
            "Transform mesh code"
        )

    def _create_transformation_macro(self) -> Callable:
        """Create transformation macro."""
        def transformation_macro(call: LispList, env: LispEnvironment) -> Any:
            """Macro for mesh transformations."""
            if call.car == "transform_mesh":
                transform_code = """
                def transform_mesh(mesh_data, transform_type, *params):
                    vertices = mesh_data.get("vertices", [])

                    if transform_type == "translate":
                        tx, ty, tz = params
                        transformed_vertices = [
                            [v[0] + tx, v[1] + ty, v[2] + tz]
                            for v in vertices
                        ]
                    elif transform_type == "scale":
                        sx, sy, sz = params
                        transformed_vertices = [
                            [v[0] * sx, v[1] * sy, v[2] * sz]
                            for v in vertices
                        ]
                    elif transform_type == "rotate":
                        angle, axis = params
                        # Simplified rotation
                        transformed_vertices = vertices
                    else:
                        transformed_vertices = vertices

                    return {
                        "vertices": transformed_vertices,
                        "faces": mesh_data.get("faces", []),
                        "transformation_applied": transform_type
                    }
                """

                return transform_code

        return transformation_macro

    def generate_cad_code_from_macros(self, macro_sequence: List[str]) -> str:
        """Generate CAD code from macro sequence."""
        generated_functions = []

        for macro_call in macro_sequence:
            expanded = self.macro_system.expand_macro(macro_call, {})
            if expanded:
                generated_functions.append(str(expanded))

                # Track usage
                macro_name = macro_call.split('(')[0] if '(' in macro_call else macro_call
                self.macro_usage[macro_name] += 1

        return "\n\n".join(generated_functions)

    def evaluate_cad_expression(self, expression: str) -> Any:
        """Evaluate CAD expression using Scheme-style evaluation."""
        return self.scheme_evaluator.evaluate_scheme_expression(expression)

    def create_dsl_from_macros(self, domain: str) -> str:
        """Create domain-specific language from macros."""
        dsl_code = f"""
        # {domain.title()} CAD DSL generated from macros

        """

        # Add macro definitions
        for macro_name, macro_info in self.macro_system.macro_registry.items():
            dsl_code += f"""
        # Macro: {macro_name}
        # {macro_info['description']}
        """

        return dsl_code

    def get_macro_analysis(self) -> Dict[str, Any]:
        """Get macro usage analysis."""
        return {
            "total_macros": len(self.macro_system.cad_macros),
            "macro_usage": dict(self.macro_usage),
            "generated_code_blocks": len(self.generated_code),
            "evaluation_cache_size": len(self.scheme_evaluator.evaluation_cache)
        }


# Factory functions for Lisp/Scheme-style systems
def create_macro_system() -> CADMacroSystem:
    """Create CAD macro system."""
    return CADMacroSystem()


def create_scheme_evaluator() -> SchemeStyleEvaluation:
    """Create Scheme-style evaluator."""
    return SchemeStyleEvaluation()


def create_lisp_cad_system() -> LispStyleCADSystem:
    """Create Lisp/Scheme-inspired CAD system."""
    return LispStyleCADSystem()
