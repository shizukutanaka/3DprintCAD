"""Lazy import system for heavy modules to improve startup time."""

import importlib
import logging
import functools
from typing import Any, Optional, Dict, Callable
import sys
import time


class LazyImportManager:
    """Manages lazy imports for heavy modules to improve startup performance."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._import_cache: Dict[str, Any] = {}
        self._import_times: Dict[str, float] = {}

        # Define heavy modules that should be lazy-loaded
        self._heavy_modules = {
            'trimesh': {
                'package': 'trimesh',
                'min_version': '3.0.0',
                'fallback': None
            },
            'numpy': {
                'package': 'numpy',
                'min_version': '1.20.0',
                'fallback': None
            },
            'scipy': {
                'package': 'scipy',
                'min_version': '1.7.0',
                'fallback': None
            },
            'matplotlib': {
                'package': 'matplotlib',
                'min_version': '3.3.0',
                'fallback': None
            },
            'Pillow': {
                'package': 'PIL',
                'min_version': '8.0.0',
                'fallback': None
            },
            'cv2': {
                'package': 'cv2',
                'min_version': '4.5.0',
                'fallback': None
            },
            'open3d': {
                'package': 'open3d',
                'min_version': '0.13.0',
                'fallback': None
            },
            'vtk': {
                'package': 'vtk',
                'min_version': '9.0.0',
                'fallback': None
            },
            'cryptography': {
                'package': 'cryptography',
                'min_version': '3.4.0',
                'fallback': None
            },
            'PyQt5': {
                'package': 'PyQt5',
                'min_version': '5.15.0',
                'fallback': None
            }
        }

    def register_module(self, name: str, package: str, min_version: str, fallback: Optional[str] = None):
        """Register a module for lazy loading.

        Args:
            name: Module identifier
            package: Package name to import
            min_version: Minimum required version
            fallback: Optional fallback package if primary fails
        """
        self._heavy_modules[name] = {
            'package': package,
            'min_version': min_version,
            'fallback': fallback
        }

    def is_module_available(self, name: str) -> bool:
        """Check if a module is available without importing it.

        Args:
            name: Module identifier

        Returns:
            True if module can be imported
        """
        if name in self._import_cache:
            return self._import_cache[name] is not None

        module_info = self._heavy_modules.get(name)
        if not module_info:
            return False

        try:
            # Try to import just to check availability
            importlib.import_module(module_info['package'])
            return True
        except ImportError:
            return False

    def get_module(self, name: str, force_reload: bool = False) -> Any:
        """Get a module, importing it lazily if needed.

        Args:
            name: Module identifier
            force_reload: Force reload even if already imported

        Returns:
            Imported module

        Raises:
            ImportError: If module cannot be imported and no fallback available
        """
        if not force_reload and name in self._import_cache:
            module = self._import_cache[name]
            if module is not None:
                return module
            else:
                raise ImportError(f"Module {name} previously failed to import")

        module_info = self._heavy_modules.get(name)
        if not module_info:
            raise ImportError(f"Unknown module: {name}")

        start_time = time.time()
        module = None
        error_msg = None

        try:
            # Try primary package
            self.logger.debug(f"Lazy importing {module_info['package']}")
            module = importlib.import_module(module_info['package'])

            # Check version if specified
            if module_info['min_version']:
                if hasattr(module, '__version__'):
                    version = getattr(module, '__version__')
                    if self._compare_versions(version, module_info['min_version']) < 0:
                        self.logger.warning(f"Module {name} version {version} is below required {module_info['min_version']}")

        except ImportError as e:
            error_msg = str(e)
            self.logger.warning(f"Failed to import {module_info['package']}: {error_msg}")

            # Try fallback if available
            if module_info['fallback']:
                try:
                    self.logger.info(f"Trying fallback import {module_info['fallback']}")
                    module = importlib.import_module(module_info['fallback'])
                except ImportError as fallback_error:
                    self.logger.error(f"Fallback import {module_info['fallback']} also failed: {fallback_error}")
                    error_msg = f"Primary: {error_msg}; Fallback: {fallback_error}"

        import_time = time.time() - start_time
        self._import_times[name] = import_time

        if module:
            self._import_cache[name] = module
            self.logger.debug(f"Successfully imported {name} in {import_time:.3f}s")
            return module
        else:
            self._import_cache[name] = None
            raise ImportError(f"Failed to import module {name}: {error_msg}")

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings.

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        def normalize_version(v):
            return [int(x) for x in v.split('.')]

        try:
            v1_parts = normalize_version(version1)
            v2_parts = normalize_version(version2)

            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            if v1_parts > v2_parts:
                return 1
            elif v1_parts < v2_parts:
                return -1
            else:
                return 0
        except (ValueError, AttributeError):
            # Fallback to string comparison
            return 1 if version1 > version2 else (-1 if version1 < version2 else 0)

    def preload_critical_modules(self, module_names: Optional[list] = None):
        """Preload critical modules in background.

        Args:
            module_names: List of module names to preload. If None, preload all.
        """
        if module_names is None:
            module_names = list(self._heavy_modules.keys())

        for name in module_names:
            if name not in self._import_cache:
                try:
                    self.get_module(name)
                except ImportError:
                    self.logger.debug(f"Skipping preload of unavailable module {name}")

    def get_import_stats(self) -> Dict[str, Any]:
        """Get statistics about module imports.

        Returns:
            Dictionary with import statistics
        """
        return {
            'total_modules': len(self._heavy_modules),
            'imported_modules': len([m for m in self._import_cache.values() if m is not None]),
            'failed_modules': len([m for m in self._import_cache.values() if m is None]),
            'import_times': self._import_times.copy(),
            'cache_size': len(self._import_cache)
        }

    def clear_cache(self):
        """Clear the import cache."""
        self._import_cache.clear()
        self._import_times.clear()
        self.logger.info("Cleared lazy import cache")


# Decorator for lazy module functions
def lazy_import_module(module_name: str):
    """Decorator to lazily import a module before function execution.

    Args:
        module_name: Name of module to import

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Import the module if not already imported
            lazy_import_manager.get_module(module_name)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Global lazy import manager instance
lazy_import_manager = LazyImportManager()


# Convenience functions for common modules
def get_trimesh():
    """Get trimesh module with lazy loading."""
    return lazy_import_manager.get_module('trimesh')


def get_numpy():
    """Get numpy module with lazy loading."""
    return lazy_import_manager.get_module('numpy')


def get_scipy():
    """Get scipy module with lazy loading."""
    return lazy_import_manager.get_module('scipy')


def get_matplotlib():
    """Get matplotlib module with lazy loading."""
    return lazy_import_manager.get_module('matplotlib')


def get_pillow():
    """Get Pillow module with lazy loading."""
    return lazy_import_manager.get_module('Pillow')


def get_cv2():
    """Get OpenCV module with lazy loading."""
    return lazy_import_manager.get_module('cv2')


def get_open3d():
    """Get Open3D module with lazy loading."""
    return lazy_import_manager.get_module('open3d')


def get_vtk():
    """Get VTK module with lazy loading."""
    return lazy_import_manager.get_module('vtk')


def get_cryptography():
    """Get cryptography module with lazy loading."""
    return lazy_import_manager.get_module('cryptography')


def get_pyqt5():
    """Get PyQt5 module with lazy loading."""
    return lazy_import_manager.get_module('PyQt5')
