"""Plugin manager for loading, managing, and executing plugins."""
import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Union
from dataclasses import dataclass
import json
import yaml
import threading
from collections import defaultdict

from .base import (
    BasePlugin, PluginInterface, PluginInfo, PluginType,
    validate_plugin_interface, get_plugin_metadata, PluginHookRegistry
)


@dataclass
class Plugin:
    """Plugin container with metadata and instance."""
    info: PluginInfo
    plugin_class: Type[BasePlugin]
    instance: Optional[BasePlugin] = None
    config: Dict[str, Any] = None


class PluginManager:
    """Manage plugins for the 3D print CAD assistant."""

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        """Initialize plugin manager.

        Args:
            plugin_dirs: List of directories to search for plugins
        """
        self.plugin_dirs = plugin_dirs or [Path("plugins")]
        self.plugins: Dict[str, Plugin] = {}
        self.active_plugins: Dict[str, Plugin] = {}
        self.hook_registry = PluginHookRegistry()
        self._lock = threading.RLock()

        # Create plugin directories if they don't exist
        for plugin_dir in self.plugin_dirs:
            plugin_dir.mkdir(exist_ok=True, parents=True)

    def discover_plugins(self) -> List[str]:
        """Discover available plugins in plugin directories.

        Returns:
            List of discovered plugin names
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue

            # Look for Python files and packages
            for item in plugin_dir.iterdir():
                if item.is_file() and item.suffix == '.py' and not item.name.startswith('_'):
                    # Single file plugin
                    plugin_name = item.stem
                    if self._load_plugin_from_file(item, plugin_name):
                        discovered.append(plugin_name)

                elif item.is_dir() and not item.name.startswith('_'):
                    # Plugin package
                    init_file = item / '__init__.py'
                    if init_file.exists():
                        plugin_name = item.name
                        if self._load_plugin_from_package(item, plugin_name):
                            discovered.append(plugin_name)

        return discovered

    def _load_plugin_from_file(self, file_path: Path, plugin_name: str) -> bool:
        """Load plugin from a single Python file.

        Args:
            file_path: Path to Python file
            plugin_name: Name for the plugin

        Returns:
            True if loaded successfully
        """
        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location(plugin_name, file_path)
            if spec is None or spec.loader is None:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin classes in module
            plugin_classes = self._find_plugin_classes(module)

            for plugin_class in plugin_classes:
                metadata = get_plugin_metadata(plugin_class)
                if metadata:
                    plugin_info = self._create_plugin_info(plugin_class)
                    if plugin_info:
                        plugin = Plugin(
                            info=plugin_info,
                            plugin_class=plugin_class
                        )
                        self.plugins[plugin_info.name] = plugin

            return len(plugin_classes) > 0

        except Exception as e:
            print(f"Error loading plugin from {file_path}: {e}")
            return False

    def _load_plugin_from_package(self, package_path: Path, plugin_name: str) -> bool:
        """Load plugin from a Python package.

        Args:
            package_path: Path to package directory
            plugin_name: Name for the plugin

        Returns:
            True if loaded successfully
        """
        try:
            # Add package parent to sys.path temporarily
            parent_path = str(package_path.parent)
            if parent_path not in sys.path:
                sys.path.insert(0, parent_path)

            try:
                # Import the package
                module = importlib.import_module(plugin_name)
                importlib.reload(module)  # Ensure fresh import

                # Find plugin classes
                plugin_classes = self._find_plugin_classes(module)

                for plugin_class in plugin_classes:
                    plugin_info = self._create_plugin_info(plugin_class)
                    if plugin_info:
                        plugin = Plugin(
                            info=plugin_info,
                            plugin_class=plugin_class
                        )
                        self.plugins[plugin_info.name] = plugin

                return len(plugin_classes) > 0

            finally:
                # Remove from sys.path
                if parent_path in sys.path:
                    sys.path.remove(parent_path)

        except Exception as e:
            print(f"Error loading plugin package {package_path}: {e}")
            return False

    def _find_plugin_classes(self, module) -> List[Type[BasePlugin]]:
        """Find plugin classes in a module.

        Args:
            module: Python module

        Returns:
            List of plugin classes
        """
        plugin_classes = []

        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip imported classes
            if obj.__module__ != module.__name__:
                continue

            # Check if it's a valid plugin
            if (hasattr(obj, '_is_plugin') and obj._is_plugin and
                validate_plugin_interface(obj)):
                plugin_classes.append(obj)

        return plugin_classes

    def _create_plugin_info(self, plugin_class: Type[BasePlugin]) -> Optional[PluginInfo]:
        """Create PluginInfo from plugin class.

        Args:
            plugin_class: Plugin class

        Returns:
            PluginInfo object or None if invalid
        """
        try:
            instance = plugin_class()
            return instance.info
        except Exception as e:
            print(f"Error creating plugin info for {plugin_class}: {e}")
            return None

    def load_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Load and initialize a specific plugin.

        Args:
            plugin_name: Name of plugin to load
            config: Plugin configuration

        Returns:
            True if loaded successfully
        """
        with self._lock:
            if plugin_name not in self.plugins:
                print(f"Plugin '{plugin_name}' not found")
                return False

            plugin = self.plugins[plugin_name]

            try:
                # Create plugin instance
                instance = plugin.plugin_class()

                # Initialize with config
                config = config or {}
                instance.initialize(config)

                # Update plugin
                plugin.instance = instance
                plugin.config = config
                self.active_plugins[plugin_name] = plugin

                # Register hooks if plugin supports them
                self._register_plugin_hooks(plugin)

                print(f"Plugin '{plugin_name}' loaded successfully")
                return True

            except Exception as e:
                print(f"Error loading plugin '{plugin_name}': {e}")
                return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin.

        Args:
            plugin_name: Name of plugin to unload

        Returns:
            True if unloaded successfully
        """
        with self._lock:
            if plugin_name not in self.active_plugins:
                return False

            plugin = self.active_plugins[plugin_name]

            try:
                # Cleanup plugin
                if plugin.instance:
                    plugin.instance.cleanup()

                # Unregister hooks
                self._unregister_plugin_hooks(plugin)

                # Remove from active plugins
                del self.active_plugins[plugin_name]

                # Reset instance in plugins registry
                self.plugins[plugin_name].instance = None

                print(f"Plugin '{plugin_name}' unloaded successfully")
                return True

            except Exception as e:
                print(f"Error unloading plugin '{plugin_name}': {e}")
                return False

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get active plugin instance.

        Args:
            plugin_name: Plugin name

        Returns:
            Plugin instance or None if not active
        """
        with self._lock:
            plugin = self.active_plugins.get(plugin_name)
            return plugin.instance if plugin else None

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[BasePlugin]:
        """Get all active plugins of a specific type.

        Args:
            plugin_type: Type of plugins to get

        Returns:
            List of plugin instances
        """
        with self._lock:
            plugins = []
            for plugin in self.active_plugins.values():
                if plugin.info.plugin_type == plugin_type and plugin.instance:
                    plugins.append(plugin.instance)
            return plugins

    def list_plugins(self, active_only: bool = False) -> Dict[str, Dict[str, Any]]:
        """List all plugins with their information.

        Args:
            active_only: Only return active plugins

        Returns:
            Dictionary of plugin information
        """
        with self._lock:
            result = {}
            plugins_dict = self.active_plugins if active_only else self.plugins

            for name, plugin in plugins_dict.items():
                result[name] = {
                    'name': plugin.info.name,
                    'version': plugin.info.version,
                    'description': plugin.info.description,
                    'author': plugin.info.author,
                    'type': plugin.info.plugin_type.value,
                    'dependencies': plugin.info.dependencies,
                    'enabled': plugin.info.enabled,
                    'active': plugin.instance is not None
                }

            return result

    def execute_plugin(
        self,
        plugin_name: str,
        method: str,
        *args,
        **kwargs
    ) -> Any:
        """Execute a method on a plugin.

        Args:
            plugin_name: Name of plugin
            method: Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Method result

        Raises:
            ValueError: If plugin not found or method doesn't exist
        """
        plugin_instance = self.get_plugin(plugin_name)
        if not plugin_instance:
            raise ValueError(f"Plugin '{plugin_name}' not active")

        if not hasattr(plugin_instance, method):
            raise ValueError(f"Method '{method}' not found in plugin '{plugin_name}'")

        method_func = getattr(plugin_instance, method)
        if not callable(method_func):
            raise ValueError(f"'{method}' is not callable in plugin '{plugin_name}'")

        return method_func(*args, **kwargs)

    def execute_plugins_by_type(
        self,
        plugin_type: PluginType,
        method: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a method on all plugins of a specific type.

        Args:
            plugin_type: Type of plugins to execute
            method: Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Dictionary of plugin name to result
        """
        results = {}
        plugins = self.get_plugins_by_type(plugin_type)

        for plugin in plugins:
            if hasattr(plugin, method):
                try:
                    method_func = getattr(plugin, method)
                    result = method_func(*args, **kwargs)
                    results[plugin.info.name] = result
                except Exception as e:
                    results[plugin.info.name] = {'error': str(e)}

        return results

    def _register_plugin_hooks(self, plugin: Plugin) -> None:
        """Register hooks for a plugin.

        Args:
            plugin: Plugin to register hooks for
        """
        if not plugin.instance:
            return

        # Look for methods that start with 'on_' as hooks
        for name, method in inspect.getmembers(plugin.instance, inspect.ismethod):
            if name.startswith('on_') and callable(method):
                event_name = name[3:]  # Remove 'on_' prefix
                self.hook_registry.register_hook(event_name, method)

    def _unregister_plugin_hooks(self, plugin: Plugin) -> None:
        """Unregister hooks for a plugin.

        Args:
            plugin: Plugin to unregister hooks for
        """
        if not plugin.instance:
            return

        # Unregister all hooks for this plugin
        for name, method in inspect.getmembers(plugin.instance, inspect.ismethod):
            if name.startswith('on_') and callable(method):
                event_name = name[3:]
                self.hook_registry.unregister_hook(event_name, method)

    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger a hook event.

        Args:
            event: Event name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            List of hook results
        """
        return self.hook_registry.trigger_hook(event, *args, **kwargs)

    def save_plugin_config(self, config_file: Path) -> None:
        """Save plugin configuration to file.

        Args:
            config_file: Path to save configuration
        """
        config = {
            'plugins': {
                name: {
                    'enabled': plugin.info.enabled,
                    'config': plugin.config or {}
                }
                for name, plugin in self.plugins.items()
            }
        }

        if config_file.suffix.lower() == '.json':
            with config_file.open('w') as f:
                json.dump(config, f, indent=2)
        else:
            with config_file.open('w') as f:
                yaml.dump(config, f, default_flow_style=False)

    def load_plugin_config(self, config_file: Path) -> None:
        """Load plugin configuration from file.

        Args:
            config_file: Path to configuration file
        """
        if not config_file.exists():
            return

        if config_file.suffix.lower() == '.json':
            with config_file.open('r') as f:
                config = json.load(f)
        else:
            with config_file.open('r') as f:
                config = yaml.safe_load(f)

        # Apply configuration
        for plugin_name, plugin_config in config.get('plugins', {}).items():
            if plugin_name in self.plugins:
                self.plugins[plugin_name].info.enabled = plugin_config.get('enabled', True)

                # Load plugin if enabled
                if plugin_config.get('enabled', True):
                    self.load_plugin(plugin_name, plugin_config.get('config', {}))

    def install_plugin(self, plugin_path: Path) -> bool:
        """Install a plugin from a file or directory.

        Args:
            plugin_path: Path to plugin file or directory

        Returns:
            True if installed successfully
        """
        # Copy plugin to first plugin directory
        target_dir = self.plugin_dirs[0]
        target_dir.mkdir(exist_ok=True, parents=True)

        try:
            if plugin_path.is_file():
                # Copy file
                target_file = target_dir / plugin_path.name
                target_file.write_bytes(plugin_path.read_bytes())
            else:
                # Copy directory
                import shutil
                target_path = target_dir / plugin_path.name
                if target_path.exists():
                    shutil.rmtree(target_path)
                shutil.copytree(plugin_path, target_path)

            # Rediscover plugins
            self.discover_plugins()
            return True

        except Exception as e:
            print(f"Error installing plugin: {e}")
            return False

    def uninstall_plugin(self, plugin_name: str) -> bool:
        """Uninstall a plugin.

        Args:
            plugin_name: Name of plugin to uninstall

        Returns:
            True if uninstalled successfully
        """
        # First unload if active
        if plugin_name in self.active_plugins:
            self.unload_plugin(plugin_name)

        # Remove from plugins registry
        if plugin_name in self.plugins:
            del self.plugins[plugin_name]

        # TODO: Remove plugin files from disk
        # This would require tracking where plugins were loaded from

        return True