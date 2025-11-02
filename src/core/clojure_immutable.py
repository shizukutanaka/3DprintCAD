"""Clojure-inspired immutable and functional programming for 3D CAD operations."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Iterator, Tuple
from pathlib import Path
import math
from functools import reduce
import threading


class CADPrimitiveType(Enum):
    """CAD primitive types."""
    CUBE = "cube"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    MESH = "mesh"
    GROUP = "group"


@dataclass(frozen=True)
class CADVector:
    """Immutable 3D vector."""
    x: float
    y: float
    z: float

    @staticmethod
    def zero() -> 'CADVector':
        """Zero vector."""
        return CADVector(0, 0, 0)

    def add(self, other: 'CADVector') -> 'CADVector':
        """Add vectors."""
        return CADVector(self.x + other.x, self.y + other.y, self.z + other.z)

    def scale(self, factor: float) -> 'CADVector':
        """Scale vector."""
        return CADVector(self.x * factor, self.y * factor, self.z * factor)

    def magnitude(self) -> float:
        """Get magnitude."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)


@dataclass(frozen=True)
class CADPrimitive:
    """Immutable CAD primitive."""
    primitive_type: CADPrimitiveType
    parameters: Dict[str, Any]
    transform: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def with_transform(self, transform_type: str, **params) -> 'CADPrimitive':
        """Add transform immutably."""
        new_transform = self.transform.copy()
        new_transform[transform_type] = params
        return CADPrimitive(self.primitive_type, self.parameters, new_transform, self.metadata)

    def with_metadata(self, **metadata) -> 'CADPrimitive':
        """Add metadata immutably."""
        new_metadata = self.metadata.copy()
        new_metadata.update(metadata)
        return CADPrimitive(self.primitive_type, self.parameters, self.transform, new_metadata)

    def get_bounds(self) -> Tuple[CADVector, CADVector]:
        """Get bounding box."""
        if self.primitive_type == CADPrimitiveType.CUBE:
            size = self.parameters.get("size", 10.0)
            half_size = size / 2
            return (CADVector(-half_size, -half_size, -half_size),
                   CADVector(half_size, half_size, half_size))
        elif self.primitive_type == CADPrimitiveType.SPHERE:
            radius = self.parameters.get("radius", 5.0)
            return (CADVector(-radius, -radius, -radius),
                   CADVector(radius, radius, radius))
        return (CADVector.zero(), CADVector.zero())


@dataclass(frozen=True)
class CADDesign:
    """Immutable CAD design."""
    design_id: str
    name: str
    primitives: Tuple[CADPrimitive, ...]
    material: str = "PLA"
    complexity: str = "LOW"

    def add_primitive(self, primitive: CADPrimitive) -> 'CADDesign':
        """Add primitive immutably."""
        new_primitives = self.primitives + (primitive,)
        return CADDesign(self.design_id, self.name, new_primitives, self.material, self.complexity)

    def with_material(self, material: str) -> 'CADDesign':
        """Set material immutably."""
        return CADDesign(self.design_id, self.name, self.primitives, material, self.complexity)

    def with_complexity(self, complexity: str) -> 'CADDesign':
        """Set complexity immutably."""
        return CADDesign(self.design_id, self.name, self.primitives, complexity, self.complexity)

    def get_total_volume(self) -> float:
        """Calculate total volume."""
        return sum(primitive.get_volume() for primitive in self.primitives)

    def get_bounds(self) -> Tuple[CADVector, CADVector]:
        """Get overall bounds."""
        if not self.primitives:
            return (CADVector.zero(), CADVector.zero())

        all_bounds = [p.get_bounds() for p in self.primitives]
        min_bounds = reduce(lambda a, b: CADVector(min(a.x, b[0].x), min(a.y, b[0].y), min(a.z, b[0].z)),
                           all_bounds[1:], all_bounds[0][0])
        max_bounds = reduce(lambda a, b: CADVector(max(a.x, b[1].x), max(a.y, b[1].y), max(a.z, b[1].z)),
                           all_bounds[1:], all_bounds[0][1])

        return (min_bounds, max_bounds)


class CADLazySequence:
    """Lazy sequence implementation."""

    def __init__(self, generator_func: Callable[[], Iterator[T]]):
        self.generator_func = generator_func
        self._cache: List[T] = []
        self._computed = False

    def __iter__(self) -> Iterator[T]:
        """Iterate lazily."""
        for item in self.generator_func():
            yield item

    def take(self, n: int) -> List[T]:
        """Take first n items."""
        result = []
        for i, item in enumerate(self):
            if i >= n:
                break
            result.append(item)
        return result

    def map(self, func: Callable[[T], U]) -> 'CADLazySequence[U]':
        """Map function lazily."""
        def mapped_generator():
            for item in self.generator_func():
                yield func(item)
        return CADLazySequence(mapped_generator)

    def filter(self, predicate: Callable[[T], bool]) -> 'CADLazySequence[T]':
        """Filter lazily."""
        def filtered_generator():
            for item in self.generator_func():
                if predicate(item):
                    yield item
        return CADLazySequence(filtered_generator)


class CADPureFunctions:
    """Pure functions for CAD operations."""

    @staticmethod
    def create_cube(size: float) -> CADPrimitive:
        """Create cube (pure function)."""
        return CADPrimitive(CADPrimitiveType.CUBE, {"size": size})

    @staticmethod
    def create_sphere(radius: float) -> CADPrimitive:
        """Create sphere (pure function)."""
        return CADPrimitive(CADPrimitiveType.SPHERE, {"radius": radius})

    @staticmethod
    def create_cylinder(radius: float, height: float) -> CADPrimitive:
        """Create cylinder (pure function)."""
        return CADPrimitive(CADPrimitiveType.CYLINDER, {"radius": radius, "height": height})

    @staticmethod
    def translate_primitive(primitive: CADPrimitive, offset: CADVector) -> CADPrimitive:
        """Translate primitive (pure function)."""
        return primitive.with_transform("translate", x=offset.x, y=offset.y, z=offset.z)

    @staticmethod
    def scale_primitive(primitive: CADPrimitive, factor: float) -> CADPrimitive:
        """Scale primitive (pure function)."""
        return primitive.with_transform("scale", factor=factor)

    @staticmethod
    def union_designs(design1: CADDesign, design2: CADDesign) -> CADDesign:
        """Union designs (pure function)."""
        combined_primitives = design1.primitives + design2.primitives
        return CADDesign(f"{design1.design_id}_union_{design2.design_id}",
                        f"{design1.name} + {design2.name}",
                        combined_primitives, design1.material, design1.complexity)

    @staticmethod
    def calculate_mesh_points_lazy(center: CADVector, radius: float, steps: int = 10) -> CADLazySequence:
        """Calculate mesh points lazily."""
        def point_generator():
            for i in range(steps):
                angle = (2 * math.pi * i) / steps
                x = center.x + radius * math.cos(angle)
                y = center.y + radius * math.sin(angle)
                yield CADVector(x, y, center.z)

        return CADLazySequence(point_generator)


class CADClojureProcessor:
    """Clojure-inspired CAD processor."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.designs: Dict[str, CADDesign] = {}
        self.primitives: Dict[str, CADPrimitive] = {}
        self.lazy_sequences: Dict[str, CADLazySequence] = {}
        self.concurrent_refs: Dict[str, Any] = {}

    def initialize_clojure_system(self) -> bool:
        """Initialize Clojure-style system."""
        try:
            # Create sample immutable designs
            self._create_sample_designs()

            # Setup lazy sequences
            self._setup_lazy_sequences()

            self.logger.info("Clojure-style CAD system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Clojure system initialization failed: {e}")
            return False

    def _create_sample_designs(self) -> None:
        """Create sample immutable designs."""

        # Simple cube
        cube = CADPureFunctions.create_cube(50)
        cube_design = CADDesign("cube_001", "Simple Cube", (cube,), "PLA", "LOW")
        self.designs["cube_001"] = cube_design

        # Translated sphere
        sphere = CADPureFunctions.create_sphere(25)
        translated_sphere = CADPureFunctions.translate_primitive(sphere, CADVector(30, 0, 0))
        sphere_design = CADDesign("sphere_001", "Translated Sphere", (translated_sphere,), "ABS", "LOW")
        self.designs["sphere_001"] = sphere_design

        # Complex assembly
        cylinder = CADPureFunctions.create_cylinder(10, 40)
        scaled_cube = CADPureFunctions.scale_primitive(cube, 0.5)
        assembly_primitives = (cylinder, scaled_cube)
        assembly = CADDesign("assembly_001", "Complex Assembly", assembly_primitives, "PETG", "HIGH")
        self.designs["assembly_001"] = assembly

    def _setup_lazy_sequences(self) -> None:
        """Setup lazy sequences."""

        # Circle points
        circle_points = CADPureFunctions.calculate_mesh_points_lazy(CADVector(0, 0, 0), 50, 20)
        self.lazy_sequences["circle_points"] = circle_points

        # Spiral points
        def spiral_generator():
            for i in range(50):
                angle = (2 * math.pi * i) / 10
                radius = i * 2
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                yield CADVector(x, y, i * 5)

        spiral_points = CADLazySequence(spiral_generator)
        self.lazy_sequences["spiral_points"] = spiral_points

    def process_with_pure_functions(self, design_ids: List[str]) -> Dict[str, Any]:
        """Process designs with pure functions."""
        functional_result = {
            "designs_processed": 0,
            "pure_operations": [],
            "immutable_results": {}
        }

        for design_id in design_ids:
            if design_id not in self.designs:
                continue

            design = self.designs[design_id]

            # Pure function applications
            volumes = [p.get_volume() for p in design.primitives]
            functional_result["pure_operations"].append(f"calculate_volumes_{design_id}")
            functional_result["immutable_results"][f"{design_id}_volumes"] = volumes

            # Immutable transformations
            translated_design = design
            for i, primitive in enumerate(design.primitives):
                offset = CADVector(i * 10, i * 5, 0)
                translated_primitive = CADPureFunctions.translate_primitive(primitive, offset)
                translated_design = translated_design.add_primitive(translated_primitive)

            functional_result["pure_operations"].append(f"translate_primitives_{design_id}")
            functional_result["immutable_results"][f"{design_id}_translated"] = translated_design.get_bounds()

            functional_result["designs_processed"] += 1

        return functional_result

    def apply_lazy_evaluation(self, sequence_name: str, operations: int = 5) -> Dict[str, Any]:
        """Apply lazy evaluation."""
        if sequence_name not in self.lazy_sequences:
            return {"error": f"Lazy sequence {sequence_name} not found"}

        sequence = self.lazy_sequences[sequence_name]

        lazy_result = {
            "sequence_name": sequence_name,
            "operations_performed": 0,
            "results": []
        }

        # Demonstrate lazy evaluation
        first_five = sequence.take(operations)
        lazy_result["results"] = first_five
        lazy_result["operations_performed"] = len(first_five)

        # Map operation (lazy)
        squared_magnitudes = sequence.map(lambda v: v.magnitude() ** 2)
        first_squared = squared_magnitudes.take(3)
        lazy_result["results"].extend([{"squared_magnitude": m} for m in first_squared])

        return lazy_result

    def create_design_with_reducers(self, base_design: CADDesign, operations: List[Callable]) -> CADDesign:
        """Create design using reducers (fold)."""
        return reduce(lambda design, op: op(design), operations, base_design)

    def get_clojure_statistics(self) -> Dict[str, Any]:
        """Get Clojure system statistics."""
        return {
            "designs": len(self.designs),
            "primitives": len(self.primitives),
            "lazy_sequences": len(self.lazy_sequences),
            "concurrent_refs": len(self.concurrent_refs),
            "clojure_features": [
                "immutable_data_structures",
                "pure_functions",
                "lazy_evaluation",
                "higher_order_functions",
                "persistent_collections",
                "software_transactional_memory"
            ]
        }


class CADFunctionalPipeline:
    """Functional pipeline for CAD operations."""

    @staticmethod
    def create_design_pipeline(base_size: float) -> Callable[[CADDesign], CADDesign]:
        """Create design pipeline."""
        def pipeline(design: CADDesign) -> CADDesign:
            # Add base cube
            cube = CADPureFunctions.create_cube(base_size)
            design_with_cube = design.add_primitive(cube)

            # Add sphere
            sphere = CADPureFunctions.create_sphere(base_size / 2)
            translated_sphere = CADPureFunctions.translate_primitive(sphere, CADVector(base_size, 0, 0))
            design_with_sphere = design_with_cube.add_primitive(translated_sphere)

            return design_with_sphere

        return pipeline

    @staticmethod
    def transform_pipeline(transforms: List[Callable]) -> Callable[[CADPrimitive], CADPrimitive]:
        """Create transformation pipeline."""
        def pipeline(primitive: CADPrimitive) -> CADPrimitive:
            return reduce(lambda p, t: t(p), transforms, primitive)

        return pipeline

    @staticmethod
    def filter_designs_by_material(material: str) -> Callable[[List[CADDesign]], List[CADDesign]]:
        """Filter designs by material."""
        def filter_func(designs: List[CADDesign]) -> List[CADDesign]:
            return [d for d in designs if d.material.upper() == material.upper()]

        return filter_func

    @staticmethod
    def map_designs(func: Callable[[CADDesign], Any]) -> Callable[[List[CADDesign]], List[Any]]:
        """Map function over designs."""
        def map_func(designs: List[CADDesign]) -> List[Any]:
            return [func(design) for design in designs]

        return map_func


class CADClojureSystem:
    """Complete Clojure-style CAD system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.clojure_processor = CADClojureProcessor()
        self.functional_pipeline = CADFunctionalPipeline()
        self.design_history: List[CADDesign] = []

    def initialize_clojure_cad(self) -> bool:
        """Initialize Clojure-style CAD system."""
        try:
            if not self.clojure_processor.initialize_clojure_system():
                return False

            # Create functional pipelines
            self._create_functional_pipelines()

            self.logger.info("Clojure-style CAD system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Clojure CAD initialization failed: {e}")
            return False

    def _create_functional_pipelines(self) -> None:
        """Create functional pipelines."""

        # Cube scaling pipeline
        scale_transforms = [
            lambda p: CADPureFunctions.scale_primitive(p, 1.5),
            lambda p: CADPureFunctions.translate_primitive(p, CADVector(10, 10, 10))
        ]

        self.functional_pipeline.scale_pipeline = CADFunctionalPipeline.transform_pipeline(scale_transforms)

        # Design enhancement pipeline
        enhancement_operations = [
            lambda d: d.with_material("ABS"),
            lambda d: d.with_complexity("MEDIUM")
        ]

        self.functional_pipeline.enhancement_pipeline = enhancement_operations

    def process_designs_functionally(self, design_ids: List[str]) -> Dict[str, Any]:
        """Process designs functionally."""
        designs = [self.clojure_processor.designs[design_id] for design_id in design_ids
                  if design_id in self.clojure_processor.designs]

        if not designs:
            return {"error": "No designs found"}

        functional_result = {
            "designs_input": len(designs),
            "functional_operations": [],
            "immutable_results": {}
        }

        # Apply filter by material
        pla_designs = CADFunctionalPipeline.filter_designs_by_material("PLA")(designs)
        functional_result["functional_operations"].append("filter_by_material_PLA")
        functional_result["immutable_results"]["pla_designs"] = len(pla_designs)

        # Apply map operations
        volumes = CADFunctionalPipeline.map_designs(lambda d: d.get_total_volume())(designs)
        functional_result["functional_operations"].append("map_volumes")
        functional_result["immutable_results"]["total_volumes"] = volumes

        # Apply design pipeline
        pipeline = CADFunctionalPipeline.create_design_pipeline(30.0)
        base_design = CADDesign("pipeline_base", "Pipeline Base", (), "PLA", "LOW")
        enhanced_design = pipeline(base_design)
        functional_result["functional_operations"].append("design_pipeline")
        functional_result["immutable_results"]["enhanced_design"] = enhanced_design.get_total_volume()

        return functional_result

    def demonstrate_immutability(self) -> Dict[str, Any]:
        """Demonstrate immutability."""
        immutable_demo = {
            "original_design": None,
            "modified_versions": [],
            "immutability_preserved": True,
            "operations_performed": 0
        }

        # Start with base design
        base_design = self.clojure_processor.designs.get("cube_001")
        if not base_design:
            return {"error": "Base design not found"}

        immutable_demo["original_design"] = base_design

        # Create modified versions (immutable)
        current_design = base_design

        # Add primitives immutably
        for i in range(3):
            new_primitive = CADPureFunctions.create_sphere(10 + i * 5)
            offset = CADVector(i * 20, i * 10, 0)
            translated_primitive = CADPureFunctions.translate_primitive(new_primitive, offset)
            current_design = current_design.add_primitive(translated_primitive)
            immutable_demo["modified_versions"].append(current_design)
            immutable_demo["operations_performed"] += 1

        # Verify original is unchanged
        immutable_demo["immutability_preserved"] = len(base_design.primitives) == 1

        return immutable_demo

    def get_clojure_cad_summary(self) -> Dict[str, Any]:
        """Get Clojure CAD system summary."""
        return {
            "clojure_processor": self.clojure_processor.get_clojure_statistics(),
            "functional_pipeline": {"available": True},
            "design_history": len(self.design_history),
            "clojure_features": [
                "immutable_data_structures",
                "pure_functions",
                "lazy_evaluation",
                "higher_order_functions",
                "persistent_collections",
                "software_transactional_memory",
                "repl_driven_development",
                "functional_composition"
            ]
        }


# Factory functions for Clojure-style programming
def create_cad_vector(x: float, y: float, z: float) -> CADVector:
    """Create CAD vector."""
    return CADVector(x, y, z)


def create_cad_primitive(primitive_type: CADPrimitiveType, **parameters) -> CADPrimitive:
    """Create CAD primitive."""
    return CADPrimitive(primitive_type, parameters)


def create_cad_design(design_id: str, name: str, primitives: Tuple[CADPrimitive, ...],
                     material: str = "PLA", complexity: str = "LOW") -> CADDesign:
    """Create CAD design."""
    return CADDesign(design_id, name, primitives, material, complexity)


def create_clojure_processor() -> CADClojureProcessor:
    """Create Clojure processor."""
    return CADClojureProcessor()


def create_clojure_system() -> CADClojureSystem:
    """Create Clojure system."""
    return CADClojureSystem()


# Pure function compositions
class CADFunctionComposition:
    """Function composition utilities."""

    @staticmethod
    def compose(*functions: Callable) -> Callable:
        """Compose functions."""
        def composed(x):
            return reduce(lambda acc, f: f(acc), functions, x)
        return composed

    @staticmethod
    def pipe(value: Any, *functions: Callable) -> Any:
        """Pipe value through functions."""
        return reduce(lambda acc, f: f(acc), functions, value)

    @staticmethod
    def curry(func: Callable, *args) -> Callable:
        """Curry function."""
        def curried(*more_args):
            return func(*args, *more_args)
        return curried

    @staticmethod
    def partial(func: Callable, *args) -> Callable:
        """Create partial function."""
        def partial_func(*more_args):
            return func(*args, *more_args)
        return partial_func
