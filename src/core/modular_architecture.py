"""Modular architecture manager for better code organization and separation of concerns."""

import importlib
import inspect
import logging
from typing import Dict, List, Any, Optional, Callable, Type, Set
from dataclasses import dataclass
from abc import ABC, abstractmethod
import time


@dataclass
class ModuleInfo:
    """Information about a registered module."""
    name: str
    version: str
    description: str
    dependencies: List[str]
    class_type: Type
    instance: Any = None
    load_time: float = 0.0
    initialized: bool = False


class ModuleRegistry:
    """Registry for managing modular components with lazy loading and dependency resolution."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._modules: Dict[str, ModuleInfo] = {}
        self._initialization_order: List[str] = []
        self._dependency_graph: Dict[str, Set[str]] = {}

    def register_module(self,
                       name: str,
                       class_type: Type,
                       version: str = "1.0.0",
                       description: str = "",
                       dependencies: Optional[List[str]] = None):
        """Register a module for lazy loading.

        Args:
            name: Unique module name
            class_type: Module class type
            version: Module version
            description: Module description
            dependencies: List of module names this module depends on
        """
        if name in self._modules:
            self.logger.warning(f"Module {name} already registered, overwriting")

        self._modules[name] = ModuleInfo(
            name=name,
            version=version,
            description=description,
            dependencies=dependencies or [],
            class_type=class_type
        )

        # Update dependency graph
        self._update_dependency_graph()

        self.logger.info(f"Registered module {name} v{version}")

    def _update_dependency_graph(self):
        """Update the dependency graph based on registered modules."""
        self._dependency_graph.clear()

        for name, module_info in self._modules.items():
            self._dependency_graph[name] = set(module_info.dependencies)

    def get_module(self, name: str, force_reload: bool = False) -> Any:
        """Get a module instance, initializing it if needed.

        Args:
            name: Module name
            force_reload: Force re-initialization even if already loaded

        Returns:
            Module instance

        Raises:
            ValueError: If module is not registered
            ImportError: If module initialization fails
        """
        if name not in self._modules:
            raise ValueError(f"Module {name} not registered")

        module_info = self._modules[name]

        # Return existing instance if already initialized and not forcing reload
        if module_info.initialized and not force_reload:
            return module_info.instance

        # Initialize dependencies first
        for dep_name in module_info.dependencies:
            if dep_name != name:  # Avoid self-dependency
                self.get_module(dep_name)

        # Initialize the module
        try:
            start_time = time.time()
            module_info.instance = module_info.class_type()
            module_info.load_time = time.time() - start_time
            module_info.initialized = True

            self.logger.info(f"Initialized module {name} in {module_info.load_time:.3f}s")

        except Exception as e:
            self.logger.error(f"Failed to initialize module {name}: {e}")
            raise ImportError(f"Module {name} initialization failed: {e}")

        return module_info.instance

    def get_initialization_order(self) -> List[str]:
        """Get the correct order for initializing all modules based on dependencies.

        Returns:
            List of module names in initialization order
        """
        if not self._modules:
            return []

        # Topological sort to resolve dependencies
        visited = set()
        temp_visited = set()
        order = []

        def visit(module_name: str):
            if module_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {module_name}")
            if module_name in visited:
                return

            temp_visited.add(module_name)

            # Visit dependencies first
            for dep in self._dependency_graph.get(module_name, set()):
                if dep in self._modules:
                    visit(dep)

            temp_visited.remove(module_name)
            visited.add(module_name)
            order.append(module_name)

        # Visit all modules
        for module_name in self._modules:
            if module_name not in visited:
                visit(module_name)

        return order

    def initialize_all_modules(self) -> Dict[str, Any]:
        """Initialize all registered modules in dependency order.

        Returns:
            Dictionary mapping module names to instances
        """
        order = self.get_initialization_order()
        instances = {}

        for module_name in order:
            instances[module_name] = self.get_module(module_name)

        self.logger.info(f"Initialized {len(instances)} modules: {list(instances.keys())}")
        return instances

    def get_module_info(self, name: str) -> Optional[ModuleInfo]:
        """Get information about a registered module.

        Args:
            name: Module name

        Returns:
            ModuleInfo if found, None otherwise
        """
        return self._modules.get(name)

    def list_modules(self) -> List[ModuleInfo]:
        """List all registered modules.

        Returns:
            List of ModuleInfo objects
        """
        return list(self._modules.values())

    def get_loaded_modules(self) -> Dict[str, ModuleInfo]:
        """Get all loaded/initialized modules.

        Returns:
            Dictionary of loaded modules
        """
        return {
            name: info for name, info in self._modules.items()
            if info.initialized
        }

    def get_module_stats(self) -> Dict[str, Any]:
        """Get statistics about registered and loaded modules.

        Returns:
            Dictionary with module statistics
        """
        total_modules = len(self._modules)
        loaded_modules = len(self.get_loaded_modules())
        total_load_time = sum(
            info.load_time for info in self._modules.values()
            if info.initialized
        )

        return {
            'total_registered': total_modules,
            'loaded_modules': loaded_modules,
            'unloaded_modules': total_modules - loaded_modules,
            'total_load_time': total_load_time,
            'average_load_time': total_load_time / loaded_modules if loaded_modules > 0 else 0,
            'modules_by_dependency': self._analyze_dependency_patterns()
        }

    def _analyze_dependency_patterns(self) -> Dict[str, Any]:
        """Analyze dependency patterns in registered modules."""
        patterns = {
            'max_dependencies': 0,
            'avg_dependencies': 0.0,
            'modules_with_dependencies': 0,
            'independent_modules': 0
        }

        if not self._modules:
            return patterns

        dependency_counts = []
        for module_info in self._modules.values():
            dep_count = len(module_info.dependencies)
            dependency_counts.append(dep_count)

            if dep_count > 0:
                patterns['modules_with_dependencies'] += 1
            else:
                patterns['independent_modules'] += 1

        patterns['max_dependencies'] = max(dependency_counts) if dependency_counts else 0
        patterns['avg_dependencies'] = sum(dependency_counts) / len(dependency_counts) if dependency_counts else 0

        return patterns

    def reset(self):
        """Reset the registry, clearing all modules and instances."""
        self._modules.clear()
        self._initialization_order.clear()
        self._dependency_graph.clear()
        self.logger.info("Module registry reset")


# Base classes for modular components
class BaseModule(ABC):
    """Base class for all modular components."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the module. Called once when module is first loaded.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup resources when module is unloaded."""
        pass

    def is_initialized(self) -> bool:
        """Check if module has been initialized."""
        return self._initialized

    def _mark_initialized(self):
        """Mark module as initialized."""
        self._initialized = True


class DataModule(BaseModule):
    """Base class for data processing modules."""

    def __init__(self):
        super().__init__()
        self._data_cache: Dict[str, Any] = {}

    def cache_data(self, key: str, data: Any):
        """Cache data for later use."""
        self._data_cache[key] = data

    def get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data."""
        return self._data_cache.get(key)

    def clear_cache(self):
        """Clear all cached data."""
        self._data_cache.clear()


class ProcessingModule(BaseModule):
    """Base class for processing modules."""

    def __init__(self):
        super().__init__()
        self._processing_stats = {
            'operations_count': 0,
            'total_processing_time': 0.0,
            'errors_count': 0
        }

    def record_operation(self, duration: float, success: bool = True):
        """Record processing operation statistics."""
        self._processing_stats['operations_count'] += 1
        self._processing_stats['total_processing_time'] += duration

        if not success:
            self._processing_stats['errors_count'] += 1

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = self._processing_stats.copy()

        if stats['operations_count'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['operations_count']
            stats['error_rate'] = stats['errors_count'] / stats['operations_count']

        return stats


# Global module registry
module_registry = ModuleRegistry()
