"""Smalltalk-inspired live programming and pure object-oriented design for 3D CAD operations."""

from __future__ import annotations

import logging
import time
import inspect
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Type, TypeVar
from pathlib import Path
import types


T = TypeVar('T')


class ObjectProtocol(Enum):
    """Object protocols (Smalltalk object behavior)."""
    MESSAGES = "messages"
    STATE = "state"
    BEHAVIOR = "behavior"
    IDENTITY = "identity"
    EQUALITY = "equality"


@dataclass
class ObjectIdentity:
    """Object identity (Smalltalk object identity)."""
    object_id: str
    creation_time: float = field(default_factory=time.time)
    class_name: str = ""
    namespace: str = "global"

    def __post_init__(self):
        if not self.object_id:
            self.object_id = f"obj_{int(time.time() * 1000000)}"


class SmalltalkObject:
    """Smalltalk-inspired pure object."""

    def __init__(self, identity: Optional[ObjectIdentity] = None):
        self.identity = identity or ObjectIdentity(
            object_id=f"obj_{int(time.time() * 1000000)}",
            class_name=self.__class__.__name__
        )
        self.instance_variables: Dict[str, Any] = {}
        self.logger = logging.getLogger(f"object.{self.identity.object_id}")

    def send_message(self, selector: str, *arguments) -> Any:
        """Send message (Smalltalk message sending)."""
        method_name = f"doesNotUnderstand_{selector}"

        # Look for method
        if hasattr(self, selector):
            method = getattr(self, selector)
            if callable(method):
                return method(*arguments)

        # Handle unknown message
        return self.does_not_understand(selector, *arguments)

    def does_not_understand(self, selector: str, *arguments) -> Any:
        """Handle unknown message (Smalltalk doesNotUnderstand)."""
        self.logger.warning(f"Object {self.identity.object_id} does not understand: {selector}")
        return None

    def inspect(self) -> Dict[str, Any]:
        """Inspect object (Smalltalk inspect equivalent)."""
        return {
            "identity": self.identity.__dict__,
            "class": self.__class__.__name__,
            "instance_variables": self.instance_variables,
            "methods": [name for name in dir(self) if not name.startswith('_') and callable(getattr(self, name))],
            "state": self.get_object_state()
        }

    def get_object_state(self) -> Dict[str, Any]:
        """Get object state."""
        return {
            "instance_variables": self.instance_variables,
            "class_name": self.__class__.__name__,
            "creation_time": self.identity.creation_time
        }

    def become(self, other_object: 'SmalltalkObject') -> None:
        """Become another object (Smalltalk become equivalent)."""
        # Swap identities
        self.identity, other_object.identity = other_object.identity, self.identity

        # Swap instance variables
        self.instance_variables, other_object.instance_variables = other_object.instance_variables, self.instance_variables

        self.logger.info(f"Object {self.identity.object_id} became {other_object.identity.object_id}")


class ClassBrowser:
    """Smalltalk Class Browser equivalent for code exploration."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.class_hierarchy: Dict[str, Dict[str, Any]] = {}
        self.method_index: Dict[str, List[str]] = defaultdict(list)
        self.protocol_index: Dict[str, List[str]] = defaultdict(list)

    def browse_class(self, class_obj: Type) -> Dict[str, Any]:
        """Browse class definition and methods."""
        class_info = {
            "class_name": class_obj.__name__,
            "module": class_obj.__module__,
            "base_classes": [base.__name__ for base in class_obj.__bases__],
            "methods": self._get_class_methods(class_obj),
            "protocols": self._get_class_protocols(class_obj),
            "subclasses": self._get_subclasses(class_obj),
            "documentation": class_obj.__doc__ or ""
        }

        self.class_hierarchy[class_obj.__name__] = class_info
        return class_info

    def _get_class_methods(self, class_obj: Type) -> Dict[str, List[str]]:
        """Get class methods organized by protocol."""
        methods = defaultdict(list)

        for name in dir(class_obj):
            if not name.startswith('_'):
                attr = getattr(class_obj, name)
                if callable(attr) and not isinstance(attr, property):
                    # Determine protocol
                    protocol = self._determine_method_protocol(name, attr)
                    methods[protocol].append(name)

                    # Index method
                    self.method_index[name].append(class_obj.__name__)

        return dict(methods)

    def _determine_method_protocol(self, method_name: str, method: Callable) -> str:
        """Determine method protocol."""
        # Simple protocol determination based on method name
        name_lower = method_name.lower()

        if name_lower.startswith(('get', 'set', 'is', 'has')):
            return "accessing"
        elif name_lower.startswith(('add', 'remove', 'insert', 'delete')):
            return "adding"
        elif name_lower.startswith(('print', 'display', 'show')):
            return "printing"
        elif name_lower.startswith(('load', 'save', 'import', 'export')):
            return "file"
        elif name_lower.startswith(('init', 'create', 'new')):
            return "instance creation"
        else:
            return "other"

    def _get_class_protocols(self, class_obj: Type) -> List[str]:
        """Get class protocols."""
        protocols = set()

        for name in dir(class_obj):
            if not name.startswith('_'):
                attr = getattr(class_obj, name)
                if callable(attr):
                    protocol = self._determine_method_protocol(name, attr)
                    protocols.add(protocol)

        return list(protocols)

    def _get_subclasses(self, class_obj: Type) -> List[str]:
        """Get direct subclasses."""
        subclasses = []

        for subclass in class_obj.__subclasses__():
            subclasses.append(subclass.__name__)

        return subclasses

    def find_method_implementations(self, method_name: str) -> List[str]:
        """Find all implementations of a method."""
        return self.method_index.get(method_name, [])

    def find_classes_with_protocol(self, protocol: str) -> List[str]:
        """Find classes that implement a protocol."""
        return self.protocol_index.get(protocol, [])


class LiveProgrammingEnvironment:
    """Smalltalk live programming environment."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.class_browser = ClassBrowser()
        self.workspace: Dict[str, Any] = {}
        self.system_classes: Dict[str, Type] = {}
        self.changesets: List[Dict[str, Any]] = []

    def add_class_to_system(self, class_obj: Type) -> bool:
        """Add class to live system."""
        try:
            class_name = class_obj.__name__

            # Browse class
            class_info = self.class_browser.browse_class(class_obj)

            # Store in system
            self.system_classes[class_name] = class_obj
            self.workspace[class_name] = class_obj

            # Record changeset
            self.changesets.append({
                "type": "class_added",
                "class_name": class_name,
                "timestamp": time.time(),
                "description": f"Added class {class_name}"
            })

            self.logger.info(f"Added class to live system: {class_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add class: {e}")
            return False

    def modify_class_method(self, class_name: str, method_name: str, new_method: Callable) -> bool:
        """Modify class method at runtime."""
        try:
            if class_name not in self.system_classes:
                return False

            class_obj = self.system_classes[class_name]

            # Store original method
            if hasattr(class_obj, method_name):
                original_method = getattr(class_obj, method_name)

            # Add new method
            setattr(class_obj, method_name, new_method)

            # Record changeset
            self.changesets.append({
                "type": "method_modified",
                "class_name": class_name,
                "method_name": method_name,
                "timestamp": time.time(),
                "description": f"Modified method {class_name}.{method_name}"
            })

            self.logger.info(f"Modified method: {class_name}.{method_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to modify method: {e}")
            return False

    def evaluate_expression(self, expression: str) -> Any:
        """Evaluate expression in workspace context."""
        try:
            # Create safe execution context
            context = {
                "__builtins__": {
                    "print": print,
                    "len": len,
                    "range": range,
                    "str": str,
                    "int": int,
                    "float": float
                }
            }

            # Add workspace objects
            context.update(self.workspace)

            result = eval(expression, context)

            # Store result in workspace
            result_var = f"result_{int(time.time())}"
            self.workspace[result_var] = result

            return result

        except Exception as e:
            self.logger.error(f"Expression evaluation failed: {e}")
            return None

    def get_workspace_contents(self) -> Dict[str, Any]:
        """Get workspace contents."""
        return {
            "variables": {k: v for k, v in self.workspace.items() if not k.startswith('__')},
            "classes": list(self.system_classes.keys()),
            "changesets": self.changesets[-10:],  # Last 10 changes
            "system_stats": {
                "total_classes": len(self.system_classes),
                "total_methods": sum(len(methods) for methods in self.class_browser.method_index.values()),
                "total_changes": len(self.changesets)
            }
        }


class MessagePassingSystem:
    """Smalltalk-style message passing system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.objects: Dict[str, SmalltalkObject] = {}
        self.message_queue: List[Dict[str, Any]] = []
        self.message_handlers: Dict[str, Callable] = {}

    def create_object(self, object_class: Type[SmalltalkObject], identity: Optional[ObjectIdentity] = None) -> SmalltalkObject:
        """Create object."""
        obj = object_class(identity)
        self.objects[obj.identity.object_id] = obj
        return obj

    def send_message(self, receiver_id: str, selector: str, *arguments) -> Any:
        """Send message to object."""
        if receiver_id not in self.objects:
            self.logger.error(f"Object {receiver_id} not found")
            return None

        receiver = self.objects[receiver_id]

        # Queue message for processing
        message = {
            "receiver_id": receiver_id,
            "selector": selector,
            "arguments": arguments,
            "timestamp": time.time()
        }

        self.message_queue.append(message)

        # Process message
        return receiver.send_message(selector, *arguments)

    def broadcast_message(self, selector: str, *arguments) -> Dict[str, Any]:
        """Broadcast message to all objects."""
        results = {}

        for object_id, obj in self.objects.items():
            try:
                result = obj.send_message(selector, *arguments)
                results[object_id] = result
            except Exception as e:
                self.logger.error(f"Broadcast failed for {object_id}: {e}")
                results[object_id] = None

        return results

    def get_object_info(self, object_id: str) -> Optional[Dict[str, Any]]:
        """Get object information."""
        if object_id in self.objects:
            return self.objects[object_id].inspect()
        return None


class CADLiveObject(SmalltalkObject):
    """Live CAD object with Smalltalk behavior."""

    def __init__(self, identity: Optional[ObjectIdentity] = None):
        super().__init__(identity)
        self.mesh_data: Optional[Dict[str, Any]] = None
        self.transformation_matrix: List[List[float]] = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        self.material_properties: Dict[str, Any] = {}

    def translate(self, x: float, y: float, z: float) -> None:
        """Translate object."""
        self.transformation_matrix[0][2] += x  # X translation
        self.transformation_matrix[1][2] += y  # Y translation
        self.transformation_matrix[2][2] += z  # Z translation

        self.instance_variables["last_translation"] = [x, y, z]

    def rotate(self, angle: float, axis: str = "z") -> None:
        """Rotate object."""
        import math

        if axis == "x":
            # Rotate around X axis
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            rotation_matrix = [
                [1, 0, 0],
                [0, cos_a, -sin_a],
                [0, sin_a, cos_a]
            ]
        elif axis == "y":
            # Rotate around Y axis
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            rotation_matrix = [
                [cos_a, 0, sin_a],
                [0, 1, 0],
                [-sin_a, 0, cos_a]
            ]
        else:
            # Rotate around Z axis
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            rotation_matrix = [
                [cos_a, -sin_a, 0],
                [sin_a, cos_a, 0],
                [0, 0, 1]
            ]

        # Multiply transformation matrices
        self.transformation_matrix = self._matrix_multiply(rotation_matrix, self.transformation_matrix)

        self.instance_variables["last_rotation"] = [angle, axis]

    def _matrix_multiply(self, a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        """Multiply 3x3 matrices."""
        result = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

        for i in range(3):
            for j in range(3):
                for k in range(3):
                    result[i][j] += a[i][k] * b[k][j]

        return result

    def scale(self, scale_factor: float) -> None:
        """Scale object."""
        for i in range(3):
            self.transformation_matrix[i][i] *= scale_factor

        self.instance_variables["last_scale"] = scale_factor

    def set_material(self, material_name: str, properties: Dict[str, Any]) -> None:
        """Set material properties."""
        self.material_properties[material_name] = properties
        self.instance_variables["material"] = material_name

    def get_bounds(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Get object bounds."""
        if not self.mesh_data:
            return ((0, 0, 0), (0, 0, 0))

        vertices = self.mesh_data.get("vertices", [])

        if not vertices:
            return ((0, 0, 0), (0, 0, 0))

        min_coords = [min(coord[i] for coord in vertices) for i in range(3)]
        max_coords = [max(coord[i] for coord in vertices) for i in range(3)]

        return (tuple(min_coords), tuple(max_coords))


class IncrementalDevelopmentSystem:
    """Smalltalk-style incremental development system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.live_environment = LiveProgrammingEnvironment()
        self.message_system = MessagePassingSystem()
        self.development_history: List[Dict[str, Any]] = []
        self.current_version = "1.0.0"

    def start_live_session(self) -> bool:
        """Start live development session."""
        try:
            # Initialize CAD classes in live environment
            cad_classes = [
                CADLiveObject,
                type('MeshProcessor', (), {}),
                type('MaterialManager', (), {})
            ]

            for class_obj in cad_classes:
                self.live_environment.add_class_to_system(class_obj)

            self.logger.info("Live development session started")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start live session: {e}")
            return False

    def modify_object_behavior(self, object_id: str, method_name: str, new_behavior: Callable) -> bool:
        """Modify object behavior at runtime."""
        try:
            obj = self.message_system.objects.get(object_id)
            if not obj:
                return False

            # Add new method to object
            setattr(obj, method_name, new_behavior)

            # Record change
            self.development_history.append({
                "type": "behavior_modification",
                "object_id": object_id,
                "method_name": method_name,
                "timestamp": time.time(),
                "description": f"Modified behavior of {object_id}.{method_name}"
            })

            self.logger.info(f"Modified object behavior: {object_id}.{method_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to modify behavior: {e}")
            return False

    def create_object_variant(self, base_object_id: str, variant_name: str) -> Optional[str]:
        """Create object variant."""
        try:
            base_object = self.message_system.objects.get(base_object_id)
            if not base_object:
                return None

            # Create variant object
            variant_identity = ObjectIdentity(
                object_id=f"{base_object_id}_{variant_name}",
                class_name=f"{base_object.__class__.__name__}_{variant_name}"
            )

            variant_object = CADLiveObject(variant_identity)

            # Copy state from base object
            variant_object.instance_variables = base_object.instance_variables.copy()
            variant_object.mesh_data = base_object.mesh_data
            variant_object.transformation_matrix = [row[:] for row in base_object.transformation_matrix]

            # Register variant
            self.message_system.objects[variant_identity.object_id] = variant_object

            # Record creation
            self.development_history.append({
                "type": "variant_creation",
                "base_object_id": base_object_id,
                "variant_id": variant_identity.object_id,
                "variant_name": variant_name,
                "timestamp": time.time()
            })

            self.logger.info(f"Created object variant: {variant_identity.object_id}")
            return variant_identity.object_id

        except Exception as e:
            self.logger.error(f"Failed to create variant: {e}")
            return None

    def get_development_status(self) -> Dict[str, Any]:
        """Get development status."""
        return {
            "live_environment": self.live_environment.get_workspace_contents(),
            "message_system": {
                "total_objects": len(self.message_system.objects),
                "message_queue_size": len(self.message_system.message_queue)
            },
            "development_history": self.development_history[-10:],  # Last 10 changes
            "current_version": self.current_version,
            "session_active": True
        }


class ObjectOrientedCADSystem:
    """Complete object-oriented CAD system with Smalltalk patterns."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.live_system = IncrementalDevelopmentSystem()
        self.class_browser = ClassBrowser()
        self.object_registry: Dict[str, CADLiveObject] = {}

    def initialize_live_system(self) -> bool:
        """Initialize live object-oriented system."""
        try:
            # Start live session
            if not self.live_system.start_live_session():
                return False

            # Create initial CAD objects
            self._create_initial_objects()

            self.logger.info("Live object-oriented CAD system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Live system initialization failed: {e}")
            return False

    def _create_initial_objects(self) -> None:
        """Create initial CAD objects."""
        # Create mesh processing object
        mesh_processor = CADLiveObject()
        mesh_processor.identity.class_name = "MeshProcessor"
        self.object_registry["mesh_processor"] = mesh_processor

        # Create material manager object
        material_manager = CADLiveObject()
        material_manager.identity.class_name = "MaterialManager"
        self.object_registry["material_manager"] = material_manager

        # Register with message system
        for obj_id, obj in self.object_registry.items():
            self.live_system.message_system.objects[obj.identity.object_id] = obj

    def send_cad_message(self, object_name: str, message: str, *args) -> Any:
        """Send message to CAD object."""
        if object_name not in self.object_registry:
            self.logger.error(f"Object {object_name} not found")
            return None

        obj = self.object_registry[object_name]
        return obj.send_message(message, *args)

    def inspect_cad_object(self, object_name: str) -> Optional[Dict[str, Any]]:
        """Inspect CAD object."""
        if object_name not in self.object_registry:
            return None

        return self.object_registry[object_name].inspect()

    def browse_cad_classes(self) -> Dict[str, Any]:
        """Browse CAD classes."""
        return {
            "class_hierarchy": self.class_browser.class_hierarchy,
            "method_index": dict(self.class_browser.method_index),
            "protocol_index": dict(self.class_browser.protocol_index)
        }

    def modify_object_at_runtime(self, object_name: str, modification: Dict[str, Any]) -> bool:
        """Modify object at runtime."""
        if object_name not in self.object_registry:
            return False

        obj = self.object_registry[object_name]

        try:
            # Apply modifications
            for key, value in modification.items():
                if key == "add_method":
                    # Add new method
                    method_name = value.get("name")
                    method_func = value.get("function")
                    if method_name and method_func:
                        setattr(obj, method_name, method_func)
                        self.logger.info(f"Added method {method_name} to {object_name}")

                elif key == "modify_property":
                    # Modify instance variable
                    property_name = value.get("name")
                    property_value = value.get("value")
                    if property_name:
                        obj.instance_variables[property_name] = property_value
                        self.logger.info(f"Modified property {property_name} of {object_name}")

            return True

        except Exception as e:
            self.logger.error(f"Runtime modification failed: {e}")
            return False

    def get_system_snapshot(self) -> Dict[str, Any]:
        """Get system snapshot."""
        return {
            "live_system": self.live_system.get_development_status(),
            "object_registry": {
                name: obj.inspect() for name, obj in self.object_registry.items()
            },
            "class_browser": self.browse_cad_classes(),
            "system_health": {
                "total_objects": len(self.object_registry),
                "live_modifications": len(self.live_system.development_history),
                "system_uptime": time.time() - self.live_system.live_environment.workspace.get("start_time", time.time())
            }
        }


# Factory functions for Smalltalk-style systems
def create_live_environment() -> LiveProgrammingEnvironment:
    """Create live programming environment."""
    return LiveProgrammingEnvironment()


def create_message_system() -> MessagePassingSystem:
    """Create message passing system."""
    return MessagePassingSystem()


def create_incremental_system() -> IncrementalDevelopmentSystem:
    """Create incremental development system."""
    return IncrementalDevelopmentSystem()


def create_object_oriented_system() -> ObjectOrientedCADSystem:
    """Create object-oriented CAD system."""
    return ObjectOrientedCADSystem()
