"""Base classes and interfaces for plugin system."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import inspect


class PluginType(Enum):
    """Plugin type enumeration."""
    VALIDATOR = "validator"
    ANALYZER = "analyzer"
    PROCESSOR = "processor"
    EXPORTER = "exporter"
    IMPORTER = "importer"
    SLICER = "slicer"
    OPTIMIZER = "optimizer"
    VISUALIZER = "visualizer"


@dataclass
class PluginInfo:
    """Plugin information metadata."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str]
    config_schema: Optional[Dict[str, Any]] = None
    enabled: bool = True


class PluginInterface(ABC):
    """Abstract base class for all plugins."""

    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """Get plugin information."""
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin with configuration.

        Args:
            config: Plugin configuration dictionary
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        return True


class BasePlugin(PluginInterface):
    """Base plugin implementation with common functionality."""

    def __init__(self):
        """Initialize base plugin."""
        self._config: Dict[str, Any] = {}
        self._initialized = False

    @property
    def config(self) -> Dict[str, Any]:
        """Get plugin configuration."""
        return self._config.copy()

    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin.

        Args:
            config: Plugin configuration
        """
        if not self.validate_config(config):
            raise ValueError("Invalid plugin configuration")

        self._config = config.copy()
        self._on_initialize()
        self._initialized = True

    def _on_initialize(self) -> None:
        """Override for custom initialization logic."""
        pass

    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        self._on_cleanup()
        self._initialized = False
        self._config = {}

    def _on_cleanup(self) -> None:
        """Override for custom cleanup logic."""
        pass

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get(key, default)


class ValidatorPlugin(BasePlugin):
    """Base class for mesh validator plugins."""

    @abstractmethod
    def validate(self, mesh: Any, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate mesh.

        Args:
            mesh: Mesh object to validate
            settings: Validation settings

        Returns:
            Validation result dictionary
        """
        pass


class AnalyzerPlugin(BasePlugin):
    """Base class for mesh analyzer plugins."""

    @abstractmethod
    def analyze(self, mesh: Any, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze mesh.

        Args:
            mesh: Mesh object to analyze
            options: Analysis options

        Returns:
            Analysis result dictionary
        """
        pass


class ProcessorPlugin(BasePlugin):
    """Base class for mesh processor plugins."""

    @abstractmethod
    def process(self, mesh: Any, parameters: Dict[str, Any]) -> Any:
        """Process mesh.

        Args:
            mesh: Mesh object to process
            parameters: Processing parameters

        Returns:
            Processed mesh object
        """
        pass


class ExporterPlugin(BasePlugin):
    """Base class for mesh exporter plugins."""

    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """Get list of supported file formats."""
        pass

    @abstractmethod
    def export(self, mesh: Any, file_path: str, options: Dict[str, Any]) -> bool:
        """Export mesh to file.

        Args:
            mesh: Mesh object to export
            file_path: Output file path
            options: Export options

        Returns:
            True if successful, False otherwise
        """
        pass


class ImporterPlugin(BasePlugin):
    """Base class for mesh importer plugins."""

    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """Get list of supported file formats."""
        pass

    @abstractmethod
    def import_mesh(self, file_path: str, options: Dict[str, Any]) -> Any:
        """Import mesh from file.

        Args:
            file_path: Input file path
            options: Import options

        Returns:
            Loaded mesh object
        """
        pass


class SlicerPlugin(BasePlugin):
    """Base class for slicer plugins."""

    @abstractmethod
    def slice(self, mesh: Any, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Slice mesh for 3D printing.

        Args:
            mesh: Mesh object to slice
            settings: Slicing settings

        Returns:
            Slicing result dictionary
        """
        pass


class OptimizerPlugin(BasePlugin):
    """Base class for optimizer plugins."""

    @abstractmethod
    def optimize(self, mesh: Any, goals: List[str], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize mesh or settings.

        Args:
            mesh: Mesh object to optimize
            goals: Optimization goals
            constraints: Optimization constraints

        Returns:
            Optimization result dictionary
        """
        pass


class VisualizerPlugin(BasePlugin):
    """Base class for visualizer plugins."""

    @abstractmethod
    def visualize(self, mesh: Any, options: Dict[str, Any]) -> Any:
        """Create visualization of mesh.

        Args:
            mesh: Mesh object to visualize
            options: Visualization options

        Returns:
            Visualization result (image, scene, etc.)
        """
        pass


class PluginHookRegistry:
    """Registry for plugin hooks and callbacks."""

    def __init__(self):
        """Initialize hook registry."""
        self._hooks: Dict[str, List[callable]] = {}

    def register_hook(self, event: str, callback: callable) -> None:
        """Register a hook callback.

        Args:
            event: Event name
            callback: Callback function
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def unregister_hook(self, event: str, callback: callable) -> None:
        """Unregister a hook callback.

        Args:
            event: Event name
            callback: Callback function
        """
        if event in self._hooks and callback in self._hooks[event]:
            self._hooks[event].remove(callback)

    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger all callbacks for an event.

        Args:
            event: Event name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            List of callback results
        """
        results = []
        for callback in self._hooks.get(event, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                # Log error but continue with other callbacks
                print(f"Error in hook callback: {e}")
        return results

    def list_hooks(self) -> Dict[str, int]:
        """List all registered hooks.

        Returns:
            Dictionary of event names and callback counts
        """
        return {event: len(callbacks) for event, callbacks in self._hooks.items()}


def plugin_decorator(plugin_type: PluginType):
    """Decorator to mark classes as plugins.

    Args:
        plugin_type: Type of plugin

    Returns:
        Decorator function
    """
    def decorator(cls):
        cls._plugin_type = plugin_type
        cls._is_plugin = True
        return cls
    return decorator


def validate_plugin_interface(plugin_class: type) -> bool:
    """Validate that a class implements the required plugin interface.

    Args:
        plugin_class: Class to validate

    Returns:
        True if valid plugin interface
    """
    # Check if it's a subclass of BasePlugin
    if not issubclass(plugin_class, BasePlugin):
        return False

    # Check required methods are implemented
    required_methods = ['info', 'initialize', 'cleanup']
    for method_name in required_methods:
        if not hasattr(plugin_class, method_name):
            return False

        method = getattr(plugin_class, method_name)
        if not callable(method):
            return False

    return True


def get_plugin_metadata(plugin_class: type) -> Optional[Dict[str, Any]]:
    """Extract metadata from plugin class.

    Args:
        plugin_class: Plugin class

    Returns:
        Plugin metadata dictionary or None if invalid
    """
    if not validate_plugin_interface(plugin_class):
        return None

    # Try to get plugin info
    try:
        instance = plugin_class()
        info = instance.info
        return {
            'name': info.name,
            'version': info.version,
            'description': info.description,
            'author': info.author,
            'type': info.plugin_type.value,
            'dependencies': info.dependencies,
            'class': plugin_class
        }
    except Exception:
        return None