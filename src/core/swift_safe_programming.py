"""Swift-inspired safe programming for 3D CAD operations."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Iterator, Protocol
from pathlib import Path
import math


class SafetyLevel(Enum):
    """Safety levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    RELAXED = "relaxed"


class CADPrimitiveType(Enum):
    """CAD primitive types."""
    CUBE = "cube"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    MESH = "mesh"
    GROUP = "group"


class CADResult:
    """Result type for safe operations."""

    def __init__(self, success: bool, value: Any = None, error: Optional[str] = None):
        self.success = success
        self.value = value
        self.error = error

    @staticmethod
    def ok(value: Any) -> 'CADResult':
        """Create successful result."""
        return CADResult(True, value)

    @staticmethod
    def err(error: str) -> 'CADResult':
        """Create error result."""
        return CADResult(False, None, error)

    def is_ok(self) -> bool:
        """Check if result is successful."""
        return self.success

    def is_err(self) -> bool:
        """Check if result is error."""
        return not self.success

    def unwrap(self) -> Any:
        """Get value or raise error."""
        if self.success:
            return self.value
        else:
            raise ValueError(self.error or "Unknown error")

    def unwrap_or(self, default: Any) -> Any:
        """Get value or default."""
        return self.value if self.success else default


class CADOptional:
    """Optional type for safe operations."""

    def __init__(self, value: Any = None, has_value: bool = True):
        self.value = value
        self.has_value = has_value

    @staticmethod
    def some(value: Any) -> 'CADOptional':
        """Create optional with value."""
        return CADOptional(value, True)

    @staticmethod
    def none() -> 'CADOptional':
        """Create optional without value."""
        return CADOptional(None, False)

    def is_some(self) -> bool:
        """Check if has value."""
        return self.has_value

    def is_none(self) -> bool:
        """Check if no value."""
        return not self.has_value

    def unwrap(self) -> Any:
        """Get value or raise error."""
        if self.has_value:
            return self.value
        else:
            raise ValueError("Optional has no value")

    def unwrap_or(self, default: Any) -> Any:
        """Get value or default."""
        return self.value if self.has_value else default

    def map(self, func: Callable) -> 'CADOptional':
        """Map function over optional."""
        if self.has_value:
            return CADOptional.some(func(self.value))
        else:
            return CADOptional.none()


class CADProtocol(Protocol):
    """CAD object protocol."""

    def get_bounds(self) -> CADResult:
        """Get object bounds."""
        ...

    def get_volume(self) -> CADResult:
        """Get object volume."""
        ...

    def validate(self) -> CADResult:
        """Validate object."""
        ...

    def transform(self, transform_type: str, **params) -> CADResult:
        """Transform object."""
        ...


@dataclass(frozen=True)
class CADVector:
    """Immutable 3D vector."""
    x: float
    y: float
    z: float

    def __add__(self, other: 'CADVector') -> 'CADVector':
        """Add vectors."""
        return CADVector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, scalar: float) -> 'CADVector':
        """Multiply by scalar."""
        return CADVector(self.x * scalar, self.y * scalar, self.z * scalar)

    def magnitude(self) -> float:
        """Get magnitude."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> 'CADVector':
        """Get normalized vector."""
        mag = self.magnitude()
        if mag == 0:
            return CADVector(0, 0, 0)
        return CADVector(self.x / mag, self.y / mag, self.z / mag)


@dataclass(frozen=True)
class CADBounds:
    """Immutable bounds."""
    min: CADVector
    max: CADVector

    def size(self) -> CADVector:
        """Get size."""
        return self.max - self.min

    def center(self) -> CADVector:
        """Get center."""
        return CADVector(
            (self.min.x + self.max.x) / 2,
            (self.min.y + self.max.y) / 2,
            (self.min.z + self.max.z) / 2
        )


@dataclass
class CADObject:
    """Safe CAD object."""
    object_type: CADPrimitiveType
    parameters: Dict[str, Any]
    bounds: Optional[CADBounds] = None
    volume: Optional[float] = None
    is_valid: bool = True

    def get_bounds(self) -> CADResult:
        """Get object bounds safely."""
        try:
            if self.bounds:
                return CADResult.ok(self.bounds)

            # Calculate bounds based on type
            if self.object_type == CADPrimitiveType.CUBE:
                size = self.parameters.get("size", 10.0)
                half_size = size / 2
                bounds = CADBounds(
                    CADVector(-half_size, -half_size, -half_size),
                    CADVector(half_size, half_size, half_size)
                )
                return CADResult.ok(bounds)

            elif self.object_type == CADPrimitiveType.SPHERE:
                radius = self.parameters.get("radius", 5.0)
                bounds = CADBounds(
                    CADVector(-radius, -radius, -radius),
                    CADVector(radius, radius, radius)
                )
                return CADResult.ok(bounds)

            elif self.object_type == CADPrimitiveType.CYLINDER:
                radius = self.parameters.get("radius", 5.0)
                height = self.parameters.get("height", 10.0)
                bounds = CADBounds(
                    CADVector(-radius, -radius, -height/2),
                    CADVector(radius, radius, height/2)
                )
                return CADResult.ok(bounds)

            else:
                return CADResult.err(f"Unsupported object type: {self.object_type}")

        except Exception as e:
            return CADResult.err(f"Bounds calculation failed: {str(e)}")

    def get_volume(self) -> CADResult:
        """Get object volume safely."""
        try:
            if self.volume:
                return CADResult.ok(self.volume)

            # Calculate volume based on type
            if self.object_type == CADPrimitiveType.CUBE:
                size = self.parameters.get("size", 10.0)
                volume = size ** 3
                return CADResult.ok(volume)

            elif self.object_type == CADPrimitiveType.SPHERE:
                radius = self.parameters.get("radius", 5.0)
                volume = (4/3) * math.pi * (radius ** 3)
                return CADResult.ok(volume)

            elif self.object_type == CADPrimitiveType.CYLINDER:
                radius = self.parameters.get("radius", 5.0)
                height = self.parameters.get("height", 10.0)
                volume = math.pi * (radius ** 2) * height
                return CADResult.ok(volume)

            else:
                return CADResult.err(f"Unsupported object type: {self.object_type}")

        except Exception as e:
            return CADResult.err(f"Volume calculation failed: {str(e)}")

    def validate(self) -> CADResult:
        """Validate object safely."""
        try:
            # Check required parameters
            required_params = []
            if self.object_type == CADPrimitiveType.CUBE:
                required_params = ["size"]
            elif self.object_type == CADPrimitiveType.SPHERE:
                required_params = ["radius"]
            elif self.object_type == CADPrimitiveType.CYLINDER:
                required_params = ["radius", "height"]

            for param in required_params:
                if param not in self.parameters:
                    return CADResult.err(f"Missing required parameter: {param}")

                value = self.parameters[param]
                if not isinstance(value, (int, float)) or value <= 0:
                    return CADResult.err(f"Invalid parameter {param}: {value}")

            # Additional validation
            if self.object_type == CADPrimitiveType.CYLINDER:
                radius = self.parameters.get("radius", 0)
                height = self.parameters.get("height", 0)
                if radius > height * 10:  # Unusually thin cylinder
                    return CADResult.err("Cylinder proportions may cause printing issues")

            return CADResult.ok(True)

        except Exception as e:
            return CADResult.err(f"Validation failed: {str(e)}")

    def transform(self, transform_type: str, **params) -> CADResult:
        """Transform object safely."""
        try:
            if transform_type == "translate":
                x = params.get("x", 0)
                y = params.get("y", 0)
                z = params.get("z", 0)

                # Validate translation parameters
                if not all(isinstance(v, (int, float)) for v in [x, y, z]):
                    return CADResult.err("Translation parameters must be numeric")

                # Create new object with transformation
                new_params = self.parameters.copy()
                new_params["transform"] = new_params.get("transform", {})
                new_params["transform"]["translate"] = [x, y, z]

                return CADResult.ok(CADObject(self.object_type, new_params))

            elif transform_type == "rotate":
                x = params.get("x", 0)
                y = params.get("y", 0)
                z = params.get("z", 0)

                # Validate rotation parameters
                if not all(isinstance(v, (int, float)) for v in [x, y, z]):
                    return CADResult.err("Rotation parameters must be numeric")

                new_params = self.parameters.copy()
                new_params["transform"] = new_params.get("transform", {})
                new_params["transform"]["rotate"] = [x, y, z]

                return CADResult.ok(CADObject(self.object_type, new_params))

            elif transform_type == "scale":
                x = params.get("x", 1)
                y = params.get("y", 1)
                z = params.get("z", 1)

                # Validate scale parameters
                if not all(isinstance(v, (int, float)) for v in [x, y, z]):
                    return CADResult.err("Scale parameters must be numeric")

                if any(v <= 0 for v in [x, y, z]):
                    return CADResult.err("Scale parameters must be positive")

                new_params = self.parameters.copy()
                new_params["transform"] = new_params.get("transform", {})
                new_params["transform"]["scale"] = [x, y, z]

                return CADResult.ok(CADObject(self.object_type, new_params))

            else:
                return CADResult.err(f"Unsupported transform type: {transform_type}")

        except Exception as e:
            return CADResult.err(f"Transform failed: {str(e)}")


class SwiftStyleCADBuilder:
    """Swift-inspired CAD builder."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.objects: Dict[str, CADObject] = {}
        self.current_object: Optional[CADObject] = None
        self.safety_level: SafetyLevel = SafetyLevel.STRICT

    def set_safety_level(self, level: SafetyLevel) -> None:
        """Set safety level."""
        self.safety_level = level

    def create_cube(self, size: float) -> CADResult:
        """Create cube safely."""
        try:
            if size <= 0:
                return CADResult.err("Cube size must be positive")

            if self.safety_level == SafetyLevel.STRICT:
                if size > 1000:
                    return CADResult.err("Cube size exceeds safety limit")

            cube = CADObject(CADPrimitiveType.CUBE, {"size": size})
            validation = cube.validate()

            if validation.is_err():
                return validation

            self.current_object = cube
            return CADResult.ok(cube)

        except Exception as e:
            return CADResult.err(f"Cube creation failed: {str(e)}")

    def create_sphere(self, radius: float) -> CADResult:
        """Create sphere safely."""
        try:
            if radius <= 0:
                return CADResult.err("Sphere radius must be positive")

            if self.safety_level == SafetyLevel.STRICT:
                if radius > 500:
                    return CADResult.err("Sphere radius exceeds safety limit")

            sphere = CADObject(CADPrimitiveType.SPHERE, {"radius": radius})
            validation = sphere.validate()

            if validation.is_err():
                return validation

            self.current_object = sphere
            return CADResult.ok(sphere)

        except Exception as e:
            return CADResult.err(f"Sphere creation failed: {str(e)}")

    def create_cylinder(self, radius: float, height: float) -> CADResult:
        """Create cylinder safely."""
        try:
            if radius <= 0 or height <= 0:
                return CADResult.err("Cylinder dimensions must be positive")

            if self.safety_level == SafetyLevel.STRICT:
                if radius > 200 or height > 1000:
                    return CADResult.err("Cylinder dimensions exceed safety limits")

            cylinder = CADObject(CADPrimitiveType.CYLINDER, {"radius": radius, "height": height})
            validation = cylinder.validate()

            if validation.is_err():
                return validation

            self.current_object = cylinder
            return CADResult.ok(cylinder)

        except Exception as e:
            return CADResult.err(f"Cylinder creation failed: {str(e)}")

    def translate(self, x: float = 0, y: float = 0, z: float = 0) -> CADResult:
        """Translate current object safely."""
        if not self.current_object:
            return CADResult.err("No current object to translate")

        return self.current_object.transform("translate", x=x, y=y, z=z)

    def rotate(self, x: float = 0, y: float = 0, z: float = 0) -> CADResult:
        """Rotate current object safely."""
        if not self.current_object:
            return CADResult.err("No current object to rotate")

        return self.current_object.transform("rotate", x=x, y=y, z=z)

    def scale(self, x: float = 1, y: float = 1, z: float = 1) -> CADResult:
        """Scale current object safely."""
        if not self.current_object:
            return CADResult.err("No current object to scale")

        return self.current_object.transform("scale", x=x, y=y, z=z)

    def union(self, other_name: str) -> CADResult:
        """Union with another object."""
        if other_name not in self.objects:
            return CADResult.err(f"Object {other_name} not found")

        if not self.current_object:
            return CADResult.err("No current object")

        other_object = self.objects[other_name]

        # Create union object
        union_obj = CADObject(
            CADPrimitiveType.GROUP,
            {
                "operation": "union",
                "objects": [self.current_object, other_object]
            }
        )

        self.current_object = union_obj
        return CADResult.ok(union_obj)

    def subtract(self, other_name: str) -> CADResult:
        """Subtract another object."""
        if other_name not in self.objects:
            return CADResult.err(f"Object {other_name} not found")

        if not self.current_object:
            return CADResult.err("No current object")

        other_object = self.objects[other_name]

        # Create difference object
        diff_obj = CADObject(
            CADPrimitiveType.GROUP,
            {
                "operation": "difference",
                "base": self.current_object,
                "subtract": other_object
            }
        )

        self.current_object = diff_obj
        return CADResult.ok(diff_obj)

    def save_object(self, name: str) -> CADResult:
        """Save current object."""
        if not self.current_object:
            return CADResult.err("No current object to save")

        self.objects[name] = self.current_object
        return CADResult.ok(name)

    def load_object(self, name: str) -> CADResult:
        """Load object as current."""
        if name not in self.objects:
            return CADResult.err(f"Object {name} not found")

        self.current_object = self.objects[name]
        return CADResult.ok(self.current_object)

    def validate_all(self) -> Dict[str, CADResult]:
        """Validate all objects."""
        results = {}
        for name, obj in self.objects.items():
            results[name] = obj.validate()
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get builder statistics."""
        total_objects = len(self.objects)
        valid_objects = sum(1 for obj in self.objects.values() if obj.is_valid)

        return {
            "total_objects": total_objects,
            "valid_objects": valid_objects,
            "invalid_objects": total_objects - valid_objects,
            "safety_level": self.safety_level.value,
            "current_object": self.current_object.object_type.value if self.current_object else None,
            "swift_features": [
                "type_safety",
                "optional_types",
                "memory_safety",
                "error_handling",
                "protocol_oriented",
                "value_types"
            ]
        }


class CADSafeProcessor:
    """Safe CAD processing engine."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.builders: Dict[str, SwiftStyleCADBuilder] = {}
        self.processing_history: List[Dict[str, Any]] = {}

    def create_builder(self, builder_name: str, safety_level: SafetyLevel = SafetyLevel.STRICT) -> CADResult:
        """Create safe builder."""
        try:
            builder = SwiftStyleCADBuilder()
            builder.set_safety_level(safety_level)
            self.builders[builder_name] = builder

            return CADResult.ok(builder)

        except Exception as e:
            return CADResult.err(f"Builder creation failed: {str(e)}")

    def safe_execute(self, operation: str, builder_name: str, **params) -> CADResult:
        """Execute operation safely."""
        if builder_name not in self.builders:
            return CADResult.err(f"Builder {builder_name} not found")

        builder = self.builders[builder_name]

        try:
            if operation == "create_cube":
                size = params.get("size", 10.0)
                return builder.create_cube(size)

            elif operation == "create_sphere":
                radius = params.get("radius", 5.0)
                return builder.create_sphere(radius)

            elif operation == "create_cylinder":
                radius = params.get("radius", 5.0)
                height = params.get("height", 10.0)
                return builder.create_cylinder(radius, height)

            elif operation == "translate":
                x = params.get("x", 0)
                y = params.get("y", 0)
                z = params.get("z", 0)
                return builder.translate(x, y, z)

            elif operation == "rotate":
                x = params.get("x", 0)
                y = params.get("y", 0)
                z = params.get("z", 0)
                return builder.rotate(x, y, z)

            elif operation == "scale":
                x = params.get("x", 1)
                y = params.get("y", 1)
                z = params.get("z", 1)
                return builder.scale(x, y, z)

            elif operation == "save":
                name = params.get("name", "object")
                return builder.save_object(name)

            elif operation == "load":
                name = params.get("name", "")
                return builder.load_object(name)

            else:
                return CADResult.err(f"Unsupported operation: {operation}")

        except Exception as e:
            return CADResult.err(f"Operation failed: {str(e)}")

    def process_with_error_handling(self, operations: List[Dict[str, Any]], builder_name: str = "default") -> Dict[str, Any]:
        """Process operations with comprehensive error handling."""
        processing_result = {
            "builder": builder_name,
            "operations_total": len(operations),
            "operations_successful": 0,
            "operations_failed": 0,
            "results": [],
            "errors": [],
            "processing_time": 0.0,
            "safe_execution": True
        }

        if builder_name not in self.builders:
            # Create default builder
            create_result = self.create_builder(builder_name)
            if create_result.is_err():
                processing_result["errors"].append(create_result.error)
                processing_result["safe_execution"] = False
                return processing_result

        start_time = time.time()

        try:
            for operation in operations:
                op_name = operation.get("operation", "unknown")
                op_params = operation.get("params", {})

                # Execute operation safely
                result = self.safe_execute(op_name, builder_name, **op_params)

                if result.is_ok():
                    processing_result["operations_successful"] += 1
                else:
                    processing_result["operations_failed"] += 1
                    processing_result["errors"].append(f"{op_name}: {result.error}")

                processing_result["results"].append({
                    "operation": op_name,
                    "params": op_params,
                    "success": result.is_ok(),
                    "result": result.value if result.is_ok() else None,
                    "error": result.error if result.is_err() else None
                })

        except Exception as e:
            processing_result["errors"].append(f"Processing failed: {str(e)}")
            processing_result["safe_execution"] = False

        processing_result["processing_time"] = time.time() - start_time

        # Store in history
        self.processing_history.append(processing_result)

        return processing_result

    def validate_design_safety(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate design safety comprehensively."""
        safety_result = {
            "design_validated": True,
            "safety_checks": [],
            "warnings": [],
            "errors": [],
            "safety_score": 1.0
        }

        try:
            # Check design parameters
            safety_checks = [
                self._check_dimension_safety,
                self._check_material_safety,
                self._check_geometry_safety,
                self._check_printability_safety
            ]

            for check in safety_checks:
                check_result = check(design_data)
                safety_result["safety_checks"].append(check_result)

                if not check_result.get("passed", False):
                    safety_result["design_validated"] = False
                    safety_result["errors"].extend(check_result.get("errors", []))

                safety_result["warnings"].extend(check_result.get("warnings", []))

            # Calculate safety score
            safety_result["safety_score"] = self._calculate_safety_score(safety_result)

        except Exception as e:
            safety_result["design_validated"] = False
            safety_result["errors"].append(f"Safety validation failed: {str(e)}")

        return safety_result

    def _check_dimension_safety(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check dimension safety."""
        check_result = {
            "check_type": "dimensions",
            "passed": True,
            "warnings": [],
            "errors": []
        }

        dimensions = design_data.get("dimensions", {})
        max_size = max(dimensions.values()) if dimensions else 0

        # Safety limits
        MAX_DIMENSION = 1000
        MIN_DIMENSION = 0.1

        if max_size > MAX_DIMENSION:
            check_result["passed"] = False
            check_result["errors"].append(f"Dimension {max_size} exceeds maximum {MAX_DIMENSION}")

        if max_size < MIN_DIMENSION:
            check_result["passed"] = False
            check_result["errors"].append(f"Dimension {max_size} below minimum {MIN_DIMENSION}")

        # Aspect ratio check
        if len(dimensions) >= 2:
            aspect_ratio = max(dimensions.values()) / min(dimensions.values())
            if aspect_ratio > 50:
                check_result["warnings"].append(f"High aspect ratio detected: {aspect_ratio}")

        return check_result

    def _check_material_safety(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check material safety."""
        check_result = {
            "check_type": "material",
            "passed": True,
            "warnings": [],
            "errors": []
        }

        material = design_data.get("material", "").upper()

        # Material compatibility
        safe_materials = ["PLA", "ABS", "PETG", "TPU", "NYLON"]
        if material not in safe_materials:
            check_result["passed"] = False
            check_result["errors"].append(f"Unsupported material: {material}")

        # Material-specific checks
        if material == "TPU" and design_data.get("complexity", "LOW") == "HIGH":
            check_result["warnings"].append("TPU may not be suitable for high complexity designs")

        return check_result

    def _check_geometry_safety(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check geometry safety."""
        check_result = {
            "check_type": "geometry",
            "passed": True,
            "warnings": [],
            "errors": []
        }

        # Check for thin walls
        wall_thickness = design_data.get("wall_thickness", 1.0)
        if wall_thickness < 0.4:
            check_result["passed"] = False
            check_result["errors"].append(f"Wall thickness {wall_thickness} too thin")

        # Check for overhangs
        overhang_angle = design_data.get("max_overhang", 45)
        if overhang_angle > 60:
            check_result["warnings"].append("Large overhangs may require support")

        return check_result

    def _check_printability_safety(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check printability safety."""
        check_result = {
            "check_type": "printability",
            "passed": True,
            "warnings": [],
            "errors": []
        }

        # Check print volume
        volume = design_data.get("volume", 0)
        MAX_VOLUME = 1000000  # 1 million cubic mm

        if volume > MAX_VOLUME:
            check_result["passed"] = False
            check_result["errors"].append(f"Print volume {volume} exceeds printer capacity")

        # Check estimated print time
        print_time = design_data.get("estimated_time", 0)
        MAX_TIME = 24 * 60 * 60  # 24 hours in seconds

        if print_time > MAX_TIME:
            check_result["warnings"].append(f"Long print time: {print_time/3600".1f"} hours")

        return check_result

    def _calculate_safety_score(self, safety_result: Dict[str, Any]) -> float:
        """Calculate overall safety score."""
        if not safety_result.get("safety_checks", []):
            return 1.0

        total_checks = len(safety_result["safety_checks"])
        passed_checks = sum(1 for check in safety_result["safety_checks"] if check.get("passed", False))

        # Reduce score for warnings
        warnings_count = len(safety_result.get("warnings", []))

        score = (passed_checks / total_checks) * (1 - (warnings_count * 0.1))

        return max(0.0, min(1.0, score))

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get processing summary."""
        return {
            "builders": len(self.builders),
            "processing_history": len(self.processing_history),
            "builder_names": list(self.builders.keys()),
            "total_operations": sum(h.get("operations_total", 0) for h in self.processing_history),
            "successful_operations": sum(h.get("operations_successful", 0) for h in self.processing_history),
            "failed_operations": sum(h.get("operations_failed", 0) for h in self.processing_history),
            "swift_features": [
                "type_safety",
                "optional_types",
                "memory_safety",
                "error_handling",
                "protocol_oriented",
                "value_types",
                "immutable_data"
            ]
        }


class CADSafeSystem:
    """Complete safe CAD system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.safe_processor = CADSafeProcessor()
        self.safety_policies: Dict[str, Dict[str, Any]] = {}
        self.validation_rules: Dict[str, Callable] = {}

    def initialize_safe_system(self) -> bool:
        """Initialize safe system."""
        try:
            # Create default builder
            self.safe_processor.create_builder("default", SafetyLevel.STRICT)

            # Setup safety policies
            self._setup_safety_policies()

            # Setup validation rules
            self._setup_validation_rules()

            self.logger.info("Safe CAD system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Safe system initialization failed: {e}")
            return False

    def _setup_safety_policies(self) -> None:
        """Setup safety policies."""
        self.safety_policies = {
            "dimension_limits": {
                "max_dimension": 1000,
                "min_dimension": 0.1,
                "max_aspect_ratio": 50
            },
            "material_safety": {
                "approved_materials": ["PLA", "ABS", "PETG", "TPU", "NYLON"],
                "temperature_limits": {"PLA": 220, "ABS": 260, "PETG": 250},
                "compatibility_rules": {
                    "TPU": "low_complexity_only",
                    "NYLON": "requires_enclosure"
                }
            },
            "geometry_safety": {
                "min_wall_thickness": 0.4,
                "max_overhang_angle": 60,
                "min_hole_diameter": 1.0
            },
            "print_safety": {
                "max_print_volume": 1000000,
                "max_print_time": 86400,  # 24 hours
                "requires_support_threshold": 45
            }
        }

    def _setup_validation_rules(self) -> None:
        """Setup validation rules."""

        def validate_design_parameters(design_data: Dict[str, Any]) -> CADResult:
            """Validate design parameters."""
            required_fields = ["dimensions", "material", "complexity"]

            for field in required_fields:
                if field not in design_data:
                    return CADResult.err(f"Missing required field: {field}")

            # Validate dimensions
            dimensions = design_data["dimensions"]
            if not isinstance(dimensions, dict):
                return CADResult.err("Dimensions must be a dictionary")

            for dim_name, dim_value in dimensions.items():
                if not isinstance(dim_value, (int, float)) or dim_value <= 0:
                    return CADResult.err(f"Invalid dimension {dim_name}: {dim_value}")

            return CADResult.ok(True)

        def validate_material_settings(material_data: Dict[str, Any]) -> CADResult:
            """Validate material settings."""
            required_settings = ["temperature", "speed", "layer_height"]

            for setting in required_settings:
                if setting not in material_data:
                    return CADResult.err(f"Missing material setting: {setting}")

                value = material_data[setting]
                if not isinstance(value, (int, float)):
                    return CADResult.err(f"Invalid {setting}: {value}")

            # Temperature range check
            temp = material_data["temperature"]
            if not (150 <= temp <= 300):
                return CADResult.err(f"Temperature {temp} out of range 150-300°C")

            return CADResult.ok(True)

        self.validation_rules = {
            "design_parameters": validate_design_parameters,
            "material_settings": validate_material_settings
        }

    def create_safe_design(self, design_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create design with safety checks."""
        safe_result = {
            "design_spec": design_spec,
            "safety_validation": {},
            "design_created": False,
            "safety_warnings": [],
            "safety_errors": []
        }

        try:
            # Validate design parameters
            param_validation = self.validation_rules["design_parameters"](design_spec)
            safe_result["safety_validation"]["parameters"] = param_validation.is_ok()

            if param_validation.is_err():
                safe_result["safety_errors"].append(param_validation.error)
                return safe_result

            # Check material safety
            material = design_spec.get("material", "").upper()
            material_check = self._check_material_safety(material, design_spec)
            safe_result["safety_validation"]["material"] = material_check["safe"]

            if not material_check["safe"]:
                safe_result["safety_errors"].extend(material_check["errors"])

            # Validate with comprehensive safety check
            safety_analysis = self.safe_processor.validate_design_safety(design_spec)
            safe_result["safety_validation"]["comprehensive"] = safety_analysis["design_validated"]
            safe_result["safety_warnings"] = safety_analysis["warnings"]
            safe_result["safety_errors"].extend(safety_analysis["errors"])

            # Create design if all checks pass
            if all(safe_result["safety_validation"].values()):
                operations = self._design_spec_to_operations(design_spec)
                processing_result = self.safe_processor.process_with_error_handling(operations)

                safe_result["design_created"] = processing_result["safe_execution"]
                safe_result["processing_result"] = processing_result

        except Exception as e:
            safe_result["safety_errors"].append(f"Design creation failed: {str(e)}")

        return safe_result

    def _check_material_safety(self, material: str, design_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Check material safety."""
        material_check = {
            "safe": True,
            "errors": [],
            "warnings": []
        }

        policies = self.safety_policies.get("material_safety", {})
        approved_materials = policies.get("approved_materials", [])

        if material not in approved_materials:
            material_check["safe"] = False
            material_check["errors"].append(f"Material {material} not approved")

        # Material-specific checks
        compatibility_rules = policies.get("compatibility_rules", {})
        if material in compatibility_rules:
            rule = compatibility_rules[material]
            if rule == "low_complexity_only":
                complexity = design_spec.get("complexity", "LOW")
                if complexity.upper() == "HIGH":
                    material_check["warnings"].append(f"{material} not recommended for high complexity")

        return material_check

    def _design_spec_to_operations(self, design_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert design spec to operations."""
        operations = []

        # Extract design parameters
        dimensions = design_spec.get("dimensions", {})
        material = design_spec.get("material", "PLA")
        complexity = design_spec.get("complexity", "LOW")

        # Determine primitive type based on dimensions
        if len(dimensions) == 1:
            # Sphere or cylinder
            size = list(dimensions.values())[0]
            if complexity.lower() == "simple":
                operations.append({"operation": "create_sphere", "params": {"radius": size/2}})
            else:
                operations.append({"operation": "create_cylinder", "params": {"radius": size/2, "height": size}})
        else:
            # Cube or rectangular prism
            if len(dimensions) == 3:
                width, height, depth = dimensions.get("width", 10), dimensions.get("height", 10), dimensions.get("depth", 10)
                operations.append({"operation": "create_cube", "params": {"size": max(width, height, depth)}})

                # Apply scaling for rectangular shapes
                if not (width == height == depth):
                    operations.append({"operation": "scale", "params": {"x": width/max(width, height, depth),
                                                                      "y": height/max(width, height, depth),
                                                                      "z": depth/max(width, height, depth)}})

        # Apply material-specific transformations
        if material == "TPU":
            operations.append({"operation": "scale", "params": {"x": 1.1, "y": 1.1, "z": 1.1}})  # Compensate for flexibility

        # Save final design
        operations.append({"operation": "save", "params": {"name": "safe_design"}})

        return operations

    def get_safe_system_summary(self) -> Dict[str, Any]:
        """Get safe system summary."""
        return {
            "safe_processor": self.safe_processor.get_processing_summary(),
            "safety_policies": len(self.safety_policies),
            "validation_rules": len(self.validation_rules),
            "policy_names": list(self.safety_policies.keys()),
            "rule_names": list(self.validation_rules.keys()),
            "swift_features": [
                "type_safety",
                "optional_types",
                "memory_safety",
                "error_handling",
                "protocol_oriented",
                "value_types",
                "immutable_data",
                "comprehensive_validation"
            ]
        }


# Factory functions for Swift-style safe programming
def create_cad_result(success: bool, value: Any = None, error: Optional[str] = None) -> CADResult:
    """Create CAD result."""
    return CADResult(success, value, error)


def create_cad_optional(value: Any = None) -> CADOptional:
    """Create CAD optional."""
    return CADOptional.some(value) if value is not None else CADOptional.none()


def create_safe_builder() -> SwiftStyleCADBuilder:
    """Create safe CAD builder."""
    return SwiftStyleCADBuilder()


def create_safe_processor() -> CADSafeProcessor:
    """Create safe CAD processor."""
    return CADSafeProcessor()


def create_safe_system() -> CADSafeSystem:
    """Create safe CAD system."""
    return CADSafeSystem()
