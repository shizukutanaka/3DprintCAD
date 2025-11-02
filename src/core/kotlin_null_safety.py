"""Kotlin-inspired null-safe programming for 3D CAD operations."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Iterator, TypeVar, Generic
from pathlib import Path
import asyncio
import math

T = TypeVar('T')
K = TypeVar('K')


class Nullability(Enum):
    """Nullability specification."""
    NON_NULL = "non_null"
    NULLABLE = "nullable"
    UNKNOWN = "unknown"


@dataclass
class CADParameter:
    """CAD parameter with null safety."""
    name: str
    value: Any
    nullability: Nullability = Nullability.NON_NULL
    default_value: Any = None

    def is_null(self) -> bool:
        """Check if value is null."""
        return self.value is None

    def is_not_null(self) -> bool:
        """Check if value is not null."""
        return self.value is not None

    def or_default(self, default: Any = None) -> Any:
        """Get value or default."""
        return self.value if self.is_not_null() else (default or self.default_value)

    def safe_call(self, func: Callable[[Any], T]) -> Optional[T]:
        """Safe function call."""
        if self.is_not_null():
            try:
                return func(self.value)
            except Exception:
                return None
        return None


@dataclass
class CADMaterial:
    """CAD material specification."""
    name: str
    density: float
    strength: float
    flexibility: str
    temperature: int
    cost_per_kg: float

    def is_suitable_for(self, complexity: str) -> bool:
        """Check material suitability."""
        suitability = {
            "PLA": ["LOW", "MEDIUM"],
            "ABS": ["LOW", "MEDIUM", "HIGH"],
            "PETG": ["LOW", "MEDIUM", "HIGH"],
            "TPU": ["LOW"],
            "NYLON": ["MEDIUM", "HIGH"]
        }
        return complexity.upper() in suitability.get(self.name.upper(), [])


@dataclass
class CADDesignSpec:
    """CAD design specification with null safety."""
    design_id: Optional[str] = None
    design_name: Optional[str] = None
    material: Optional[CADMaterial] = None
    dimensions: Optional[Dict[str, float]] = None
    complexity: Optional[str] = None
    quality_grade: Optional[str] = None
    print_settings: Optional[Dict[str, Any]] = None

    def is_valid(self) -> bool:
        """Check if design spec is valid."""
        return (self.design_id.is_not_null() and
                self.material.is_not_null() and
                self.dimensions.is_not_null() and
                len(self.dimensions) > 0)

    def get_volume(self) -> Optional[float]:
        """Calculate volume safely."""
        if not self.dimensions:
            return None

        volume = 1.0
        for dimension in self.dimensions.values():
            volume *= dimension

        return volume

    def get_estimated_cost(self) -> Optional[float]:
        """Calculate estimated cost safely."""
        volume = self.get_volume()
        if not volume or not self.material:
            return None

        return volume * self.material.density * self.material.cost_per_kg / 1000000  # Convert to kg


class CADNullSafeProcessor:
    """Kotlin-inspired null-safe CAD processor."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.design_specs: Dict[str, CADDesignSpec] = {}
        self.materials: Dict[str, CADMaterial] = {}
        self.extension_functions: Dict[str, Callable] = {}

    def register_material(self, material: CADMaterial) -> None:
        """Register material safely."""
        self.materials[material.name.upper()] = material

    def create_design_spec(self, **kwargs) -> CADDesignSpec:
        """Create design spec safely."""
        # Safe parameter extraction with defaults
        design_spec = CADDesignSpec(
            design_id=kwargs.get("design_id"),
            design_name=kwargs.get("design_name"),
            material=self._safe_get_material(kwargs.get("material")),
            dimensions=self._safe_get_dimensions(kwargs.get("dimensions")),
            complexity=kwargs.get("complexity", "LOW"),
            quality_grade=kwargs.get("quality_grade", "B"),
            print_settings=kwargs.get("print_settings", {})
        )

        # Validate and store
        if design_spec.is_valid():
            self.design_specs[design_spec.design_id or "unknown"] = design_spec

        return design_spec

    def _safe_get_material(self, material_name: Optional[str]) -> Optional[CADMaterial]:
        """Get material safely."""
        if not material_name:
            return None
        return self.materials.get(material_name.upper())

    def _safe_get_dimensions(self, dimensions: Optional[Union[Dict, List]]) -> Optional[Dict[str, float]]:
        """Get dimensions safely."""
        if not dimensions:
            return None

        if isinstance(dimensions, dict):
            # Validate dimension values
            safe_dims = {}
            for key, value in dimensions.items():
                if isinstance(value, (int, float)) and value > 0:
                    safe_dims[key] = float(value)
            return safe_dims if safe_dims else None

        elif isinstance(dimensions, (list, tuple)) and len(dimensions) >= 3:
            # Convert list to dict
            dim_names = ["width", "height", "depth"]
            safe_dims = {}
            for i, value in enumerate(dimensions[:3]):
                if isinstance(value, (int, float)) and value > 0:
                    safe_dims[dim_names[i]] = float(value)
            return safe_dims if len(safe_dims) == 3 else None

        return None

    def process_designs_safely(self, design_ids: List[str]) -> Dict[str, Any]:
        """Process designs with null safety."""
        result = {
            "designs_processed": 0,
            "designs_successful": 0,
            "designs_failed": 0,
            "results": {},
            "errors": []
        }

        for design_id in design_ids:
            design_result = self._process_single_design_safely(design_id)
            result["results"][design_id] = design_result

            if design_result["success"]:
                result["designs_successful"] += 1
            else:
                result["designs_failed"] += 1
                result["errors"].extend(design_result["errors"])

            result["designs_processed"] += 1

        return result

    def _process_single_design_safely(self, design_id: str) -> Dict[str, Any]:
        """Process single design safely."""
        result = {
            "design_id": design_id,
            "success": False,
            "volume": None,
            "cost": None,
            "validation": {},
            "errors": []
        }

        # Safe access to design spec
        design_spec = self.design_specs.get(design_id)
        if not design_spec:
            result["errors"].append(f"Design {design_id} not found")
            return result

        # Safe property access with let
        volume = design_spec.get_volume()
        if volume:
            result["volume"] = volume

        cost = design_spec.get_estimated_cost()
        if cost:
            result["cost"] = cost

        # Safe validation
        validation_result = self._validate_design_safely(design_spec)
        result["validation"] = validation_result

        result["success"] = len(result["errors"]) == 0

        return result

    def _validate_design_safely(self, design_spec: CADDesignSpec) -> Dict[str, Any]:
        """Validate design safely."""
        validation = {
            "is_valid": False,
            "checks": [],
            "warnings": []
        }

        # Safe checks with Elvis operator pattern
        if not design_spec.design_id:
            validation["checks"].append({"check": "design_id", "passed": False, "error": "Missing design ID"})
            return validation

        if not design_spec.material:
            validation["checks"].append({"check": "material", "passed": False, "error": "Missing material"})
            return validation

        if not design_spec.dimensions:
            validation["checks"].append({"check": "dimensions", "passed": False, "error": "Missing dimensions"})
            return validation

        # Additional safety checks
        complexity = design_spec.complexity or "LOW"
        if not design_spec.material.is_suitable_for(complexity):
            validation["warnings"].append(f"Material {design_spec.material.name} may not be suitable for {complexity} complexity")

        # Dimension safety
        max_dimension = max(design_spec.dimensions.values()) if design_spec.dimensions else 0
        if max_dimension > 1000:
            validation["warnings"].append(f"Large dimension detected: {max_dimension}")

        validation["is_valid"] = True
        validation["checks"].append({"check": "overall", "passed": True})

        return validation

    def add_extension_function(self, name: str, func: Callable) -> None:
        """Add extension function (Kotlin-style)."""
        self.extension_functions[name] = func

    def apply_extension(self, target: Any, extension_name: str, *args, **kwargs) -> Any:
        """Apply extension function safely."""
        if extension_name in self.extension_functions:
            try:
                return self.extension_functions[extension_name](target, *args, **kwargs)
            except Exception as e:
                self.logger.error(f"Extension {extension_name} failed: {e}")
                return target
        return target

    def get_statistics(self) -> Dict[str, Any]:
        """Get processor statistics."""
        valid_designs = sum(1 for spec in self.design_specs.values() if spec.is_valid())

        return {
            "design_specs": len(self.design_specs),
            "valid_designs": valid_designs,
            "invalid_designs": len(self.design_specs) - valid_designs,
            "materials_registered": len(self.materials),
            "extension_functions": len(self.extension_functions),
            "kotlin_features": [
                "null_safety",
                "extension_functions",
                "data_classes",
                "smart_casts",
                "safe_calls",
                "elvis_operator"
            ]
        }


class CADKotlinExtensions:
    """Kotlin-style extension functions for CAD objects."""

    @staticmethod
    def scale_by(obj: Dict[str, Any], factor: float) -> Dict[str, Any]:
        """Scale object by factor."""
        result = obj.copy()
        if "dimensions" in result:
            if isinstance(result["dimensions"], dict):
                result["dimensions"] = {k: v * factor for k, v in result["dimensions"].items()}
            elif isinstance(result["dimensions"], (list, tuple)):
                result["dimensions"] = [v * factor for v in result["dimensions"]]
        return result

    @staticmethod
    def translate_by(obj: Dict[str, Any], offset: Dict[str, float]) -> Dict[str, Any]:
        """Translate object by offset."""
        result = obj.copy()
        result["transform"] = result.get("transform", {})
        result["transform"]["translate"] = offset
        return result

    @staticmethod
    def with_material(obj: Dict[str, Any], material: str) -> Dict[str, Any]:
        """Set material for object."""
        result = obj.copy()
        result["material"] = material
        return result

    @staticmethod
    def calculate_bounds(obj: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Calculate object bounds safely."""
        if "dimensions" not in obj:
            return None

        dimensions = obj["dimensions"]
        if isinstance(dimensions, dict):
            return {
                "min": {k: -v/2 for k, v in dimensions.items()},
                "max": {k: v/2 for k, v in dimensions.items()},
                "center": {k: 0 for k in dimensions.keys()}
            }
        elif isinstance(dimensions, (list, tuple)):
            return {
                "min": [-v/2 for v in dimensions],
                "max": [v/2 for v in dimensions],
                "center": [0] * len(dimensions)
            }
        return None


class CADAsyncProcessor:
    """Async CAD processing with Kotlin-style coroutines."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.null_safe_processor = CADNullSafeProcessor()
        self.async_tasks: Dict[str, asyncio.Task] = {}

    async def process_designs_async(self, design_ids: List[str]) -> Dict[str, Any]:
        """Process designs asynchronously."""
        # Simulate async processing
        await asyncio.sleep(0.1)  # Simulate I/O

        # Use null-safe processor
        return self.null_safe_processor.process_designs_safely(design_ids)

    async def validate_designs_async(self, design_ids: List[str]) -> Dict[str, Any]:
        """Validate designs asynchronously."""
        validation_results = {}

        for design_id in design_ids:
            # Safe async validation
            validation = await self._validate_single_design_async(design_id)
            validation_results[design_id] = validation

        return {
            "validations": validation_results,
            "total_validations": len(validation_results),
            "async_processed": True
        }

    async def _validate_single_design_async(self, design_id: str) -> Dict[str, Any]:
        """Validate single design asynchronously."""
        await asyncio.sleep(0.01)  # Simulate async operation

        design_spec = self.null_safe_processor.design_specs.get(design_id)
        if not design_spec:
            return {"valid": False, "error": "Design not found"}

        validation = self.null_safe_processor._validate_design_safely(design_spec)

        return {
            "valid": validation["is_valid"],
            "checks": validation["checks"],
            "warnings": validation["warnings"]
        }

    def process_with_coroutines(self, design_ids: List[str]) -> Dict[str, Any]:
        """Process with coroutine simulation."""
        # In a real Kotlin implementation, this would use actual coroutines
        # Here we simulate the async behavior

        async def async_processing():
            results = await self.process_designs_async(design_ids)
            validations = await self.validate_designs_async(design_ids)

            return {
                "processing": results,
                "validations": validations,
                "coroutines_used": True
            }

        # Simulate coroutine execution
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(async_processing())
            return result
        finally:
            loop.close()


class CADKotlinSystem:
    """Complete Kotlin-style CAD system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.null_safe_processor = CADNullSafeProcessor()
        self.async_processor = CADAsyncProcessor()
        self.extension_registry: Dict[str, Callable] = {}

    def initialize_kotlin_system(self) -> bool:
        """Initialize Kotlin-style system."""
        try:
            # Register built-in materials
            self._register_default_materials()

            # Register extension functions
            self._register_extension_functions()

            # Setup null-safe processing
            self._setup_null_safe_processing()

            self.logger.info("Kotlin-style CAD system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Kotlin system initialization failed: {e}")
            return False

    def _register_default_materials(self) -> None:
        """Register default materials."""
        materials = [
            CADMaterial("PLA", 1.24, 50, "low", 200, 25.0),
            CADMaterial("ABS", 1.04, 40, "medium", 240, 30.0),
            CADMaterial("PETG", 1.27, 45, "medium", 230, 35.0),
            CADMaterial("TPU", 1.20, 35, "high", 210, 45.0),
            CADMaterial("NYLON", 1.14, 55, "low", 250, 50.0)
        ]

        for material in materials:
            self.null_safe_processor.register_material(material)

    def _register_extension_functions(self) -> None:
        """Register extension functions."""
        extensions = [
            ("scaleBy", CADKotlinExtensions.scale_by),
            ("translateBy", CADKotlinExtensions.translate_by),
            ("withMaterial", CADKotlinExtensions.with_material),
            ("calculateBounds", CADKotlinExtensions.calculate_bounds)
        ]

        for name, func in extensions:
            self.null_safe_processor.add_extension_function(name, func)
            self.extension_registry[name] = func

    def _setup_null_safe_processing(self) -> None:
        """Setup null-safe processing."""
        # Add safe operators and null checks
        pass

    def create_design_with_null_safety(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create design with null safety."""
        safe_result = {
            "design_data": design_data,
            "null_safety_checks": [],
            "design_created": False,
            "validation_result": {},
            "warnings": []
        }

        try:
            # Safe parameter extraction
            safe_params = {}

            # Safe string extraction
            design_id = design_data.get("design_id")
            if design_id:
                safe_params["design_id"] = str(design_id)
                safe_result["null_safety_checks"].append("design_id: safe")
            else:
                safe_result["null_safety_checks"].append("design_id: null")
                safe_result["warnings"].append("Design ID is null")

            # Safe material extraction
            material_name = design_data.get("material")
            material = self.null_safe_processor._safe_get_material(material_name)
            if material:
                safe_params["material"] = material
                safe_result["null_safety_checks"].append("material: safe")
            else:
                safe_result["null_safety_checks"].append("material: null")
                safe_result["warnings"].append(f"Material {material_name} not found")

            # Safe dimensions extraction
            dimensions = self.null_safe_processor._safe_get_dimensions(design_data.get("dimensions"))
            if dimensions:
                safe_params["dimensions"] = dimensions
                safe_result["null_safety_checks"].append("dimensions: safe")
            else:
                safe_result["null_safety_checks"].append("dimensions: null")
                safe_result["warnings"].append("Invalid or missing dimensions")

            # Create design spec safely
            if len(safe_result["warnings"]) == 0:
                design_spec = self.null_safe_processor.create_design_spec(**safe_params)
                safe_result["design_created"] = design_spec.is_valid()
                safe_result["validation_result"] = self.null_safe_processor._validate_design_safely(design_spec)
            else:
                safe_result["design_created"] = False

        except Exception as e:
            safe_result["warnings"].append(f"Design creation failed: {str(e)}")

        return safe_result

    def apply_kotlin_extensions(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply Kotlin-style extensions."""
        extended_result = {
            "original_design": design_data,
            "extensions_applied": [],
            "extended_properties": {},
            "extension_errors": []
        }

        try:
            # Apply extension functions safely
            current_obj = design_data

            # Scale by factor
            if "scale_factor" in design_data:
                scale_result = self.null_safe_processor.apply_extension(current_obj, "scaleBy", design_data["scale_factor"])
                if scale_result != current_obj:
                    current_obj = scale_result
                    extended_result["extensions_applied"].append("scaleBy")
                    extended_result["extended_properties"]["scaled"] = True

            # Translate by offset
            if "translate_offset" in design_data:
                offset = design_data["translate_offset"]
                translate_result = self.null_safe_processor.apply_extension(current_obj, "translateBy", offset)
                if translate_result != current_obj:
                    current_obj = translate_result
                    extended_result["extensions_applied"].append("translateBy")
                    extended_result["extended_properties"]["translated"] = True

            # Set material
            if "material" in design_data:
                material_result = self.null_safe_processor.apply_extension(current_obj, "withMaterial", design_data["material"])
                if material_result != current_obj:
                    current_obj = material_result
                    extended_result["extensions_applied"].append("withMaterial")
                    extended_result["extended_properties"]["material_set"] = True

            # Calculate bounds
            bounds_result = self.null_safe_processor.apply_extension(current_obj, "calculateBounds")
            if bounds_result:
                extended_result["extended_properties"]["bounds"] = bounds_result
                extended_result["extensions_applied"].append("calculateBounds")

            extended_result["final_object"] = current_obj

        except Exception as e:
            extended_result["extension_errors"].append(str(e))

        return extended_result

    def process_with_smart_casts(self, objects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process objects with smart casts."""
        smart_cast_result = {
            "objects_processed": len(objects),
            "type_checks": [],
            "safe_operations": 0,
            "unsafe_operations": 0
        }

        for obj in objects:
            # Smart cast pattern - check type and process accordingly
            obj_type = obj.get("type", "").lower()

            if obj_type == "cube":
                # Safe processing for cubes
                if isinstance(obj.get("size"), (int, float)):
                    smart_cast_result["type_checks"].append({"object": "cube", "safe": True})
                    smart_cast_result["safe_operations"] += 1
                else:
                    smart_cast_result["type_checks"].append({"object": "cube", "safe": False})
                    smart_cast_result["unsafe_operations"] += 1

            elif obj_type == "sphere":
                # Safe processing for spheres
                if isinstance(obj.get("radius"), (int, float)):
                    smart_cast_result["type_checks"].append({"object": "sphere", "safe": True})
                    smart_cast_result["safe_operations"] += 1
                else:
                    smart_cast_result["type_checks"].append({"object": "sphere", "safe": False})
                    smart_cast_result["unsafe_operations"] += 1

            elif obj_type == "cylinder":
                # Safe processing for cylinders
                radius = obj.get("radius")
                height = obj.get("height")
                if isinstance(radius, (int, float)) and isinstance(height, (int, float)):
                    smart_cast_result["type_checks"].append({"object": "cylinder", "safe": True})
                    smart_cast_result["safe_operations"] += 1
                else:
                    smart_cast_result["type_checks"].append({"object": "cylinder", "safe": False})
                    smart_cast_result["unsafe_operations"] += 1

            else:
                smart_cast_result["type_checks"].append({"object": obj_type, "safe": False})
                smart_cast_result["unsafe_operations"] += 1

        return smart_cast_result

    def get_kotlin_system_summary(self) -> Dict[str, Any]:
        """Get Kotlin system summary."""
        return {
            "null_safe_processor": self.null_safe_processor.get_statistics(),
            "async_processor": {"async_capable": True},
            "extension_functions": len(self.extension_registry),
            "registered_extensions": list(self.extension_registry.keys()),
            "kotlin_features": [
                "null_safety",
                "extension_functions",
                "data_classes",
                "smart_casts",
                "safe_calls",
                "elvis_operator",
                "coroutines",
                "type_inference"
            ]
        }


# Factory functions for Kotlin-style null safety
def create_cad_parameter(name: str, value: Any, nullability: Nullability = Nullability.NON_NULL) -> CADParameter:
    """Create CAD parameter."""
    return CADParameter(name, value, nullability)


def create_cad_material(name: str, density: float, strength: float, flexibility: str, temperature: int, cost_per_kg: float) -> CADMaterial:
    """Create CAD material."""
    return CADMaterial(name, density, strength, flexibility, temperature, cost_per_kg)


def create_design_spec(**kwargs) -> CADDesignSpec:
    """Create design specification."""
    return CADDesignSpec(**kwargs)


def create_null_safe_processor() -> CADNullSafeProcessor:
    """Create null-safe processor."""
    return CADNullSafeProcessor()


def create_kotlin_system() -> CADKotlinSystem:
    """Create Kotlin-style system."""
    return CADKotlinSystem()


# Kotlin-style operator overloads and utilities
class CADOperators:
    """Kotlin-style operators and utilities."""

    @staticmethod
    def safe_let(value: Any, func: Callable[[Any], T]) -> Optional[T]:
        """Safe let operation (Kotlin's let)."""
        if value is not None:
            return func(value)
        return None

    @staticmethod
    def elvis_operator(value: Any, default: Any) -> Any:
        """Elvis operator (?:)."""
        return value if value is not None else default

    @staticmethod
    def safe_call(obj: Any, method_name: str, *args, **kwargs) -> Any:
        """Safe method call."""
        if obj is None:
            return None

        method = getattr(obj, method_name, None)
        if method and callable(method):
            try:
                return method(*args, **kwargs)
            except Exception:
                return None

        return None

    @staticmethod
    def also(obj: Any, func: Callable[[Any], None]) -> Any:
        """Also function (Kotlin's also)."""
        func(obj)
        return obj

    @staticmethod
    def take_if(obj: Any, predicate: Callable[[Any], bool]) -> Optional[Any]:
        """Take if (Kotlin's takeIf)."""
        if predicate(obj):
            return obj
        return None

    @staticmethod
    def take_unless(obj: Any, predicate: Callable[[Any], bool]) -> Optional[Any]:
        """Take unless (Kotlin's takeUnless)."""
        if not predicate(obj):
            return obj
        return None
