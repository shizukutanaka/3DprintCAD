"""Unified configuration management system for all 3D Print CAD Assistant modules."""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from contextlib import contextmanager


class ConfigSource(Enum):
    """Configuration source types."""
    ENVIRONMENT = "environment"
    YAML_FILE = "yaml_file"
    JSON_FILE = "json_file"
    DATABASE = "database"
    DEFAULT = "default"


@dataclass
class ConfigValue:
    """Configuration value with metadata."""
    value: Any
    source: ConfigSource
    description: str = ""
    sensitive: bool = False
    validation_rules: Dict[str, Any] = field(default_factory=dict)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class UnifiedConfigManager:
    """Unified configuration management system with multi-source support."""

    def __init__(self, config_name: str = "3d_print_cad"):
        """Initialize configuration manager.

        Args:
            config_name: Name of the configuration (used for environment variables)
        """
        self.logger = logging.getLogger(__name__)
        self.config_name = config_name.upper()
        self._config: Dict[str, ConfigValue] = {}
        self._config_files: List[Path] = []
        self._lock = threading.RLock()

        # Default configuration values
        self._default_config = self._get_default_configuration()

        # Register configuration files
        self._register_default_config_files()

    def _get_default_configuration(self) -> Dict[str, ConfigValue]:
        """Get default configuration values."""
        return {
            # Security settings
            'security.file_upload.max_size_mb': ConfigValue(
                value=500,
                source=ConfigSource.DEFAULT,
                description="Maximum file size for uploads in MB",
                validation_rules={'type': 'int', 'min': 1, 'max': 5000}
            ),
            'security.file_upload.allowed_extensions': ConfigValue(
                value=['.stl', '.obj', '.3mf', '.gcode', '.ply'],
                source=ConfigSource.DEFAULT,
                description="Allowed file extensions for uploads"
            ),
            'security.hash_algorithms': ConfigValue(
                value=['sha256', 'sha512', 'blake2b'],
                source=ConfigSource.DEFAULT,
                description="Allowed hash algorithms"
            ),

            # Performance settings
            'performance.max_workers': ConfigValue(
                value=min(os.cpu_count() or 1, 8),
                source=ConfigSource.DEFAULT,
                description="Maximum number of worker processes/threads"
            ),
            'performance.memory_limit_percent': ConfigValue(
                value=80.0,
                source=ConfigSource.DEFAULT,
                description="Memory usage limit percentage before cleanup"
            ),
            'performance.cleanup_interval_seconds': ConfigValue(
                value=60.0,
                source=ConfigSource.DEFAULT,
                description="Interval between automatic memory cleanup"
            ),

            # Watchdog settings
            'watchdog.base_timeout_seconds': ConfigValue(
                value=30.0,
                source=ConfigSource.DEFAULT,
                description="Base timeout for operations"
            ),
            'watchdog.file_size_multiplier': ConfigValue(
                value=2.0,
                source=ConfigSource.DEFAULT,
                description="Timeout multiplier based on file size"
            ),

            # Error recovery settings
            'error_recovery.max_retries': ConfigValue(
                value=3,
                source=ConfigSource.DEFAULT,
                description="Maximum retry attempts for failed operations"
            ),
            'error_recovery.base_delay_seconds': ConfigValue(
                value=1.0,
                source=ConfigSource.DEFAULT,
                description="Base delay between retry attempts"
            ),

            # API settings
            'api.rate_limit.requests_per_minute': ConfigValue(
                value=60,
                source=ConfigSource.DEFAULT,
                description="API rate limit requests per minute"
            ),
            'api.timeout_seconds': ConfigValue(
                value=30.0,
                source=ConfigSource.DEFAULT,
                description="API request timeout"
            ),

            # Logging settings
            'logging.level': ConfigValue(
                value='INFO',
                source=ConfigSource.DEFAULT,
                description="Logging level (DEBUG, INFO, WARNING, ERROR)"
            ),
            'logging.max_file_size_mb': ConfigValue(
                value=100,
                source=ConfigSource.DEFAULT,
                description="Maximum log file size in MB"
            ),

            # Database settings
            'database.url': ConfigValue(
                value='sqlite:///3d_print_cad.db',
                source=ConfigSource.DEFAULT,
                description="Database connection URL",
                sensitive=True
            ),
            'database.pool_size': ConfigValue(
                value=10,
                source=ConfigSource.DEFAULT,
                description="Database connection pool size"
            ),

            # Cache settings
            'cache.enabled': ConfigValue(
                value=True,
                source=ConfigSource.DEFAULT,
                description="Enable caching"
            ),
            'cache.ttl_seconds': ConfigValue(
                value=3600,
                source=ConfigSource.DEFAULT,
                description="Cache time-to-live in seconds"
            ),
            'cache.max_size_mb': ConfigValue(
                value=1000,
                source=ConfigSource.DEFAULT,
                description="Maximum cache size in MB"
            ),

            # UI settings
            'ui.theme': ConfigValue(
                value='auto',
                source=ConfigSource.DEFAULT,
                description="UI theme (light, dark, auto)"
            ),
            'ui.language': ConfigValue(
                value='ja',
                source=ConfigSource.DEFAULT,
                description="UI language"
            ),

            # Development settings
            'development.debug_mode': ConfigValue(
                value=False,
                source=ConfigSource.DEFAULT,
                description="Enable debug mode"
            ),
            'development.enable_profiling': ConfigValue(
                value=False,
                source=ConfigSource.DEFAULT,
                description="Enable performance profiling"
            )
        }

    def _register_default_config_files(self):
        """Register default configuration file locations."""
        # Look for config files in standard locations
        search_paths = [
            Path.cwd() / 'config.yaml',
            Path.cwd() / 'config.json',
            Path.cwd() / '.3d_print_cad.yaml',
            Path.cwd() / '.3d_print_cad.json',
            Path.home() / '.3d_print_cad' / 'config.yaml',
            Path.home() / '.3d_print_cad' / 'config.json',
        ]

        for config_path in search_paths:
            if config_path.exists():
                self._config_files.append(config_path)
                self.logger.info(f"Found configuration file: {config_path}")

    def load_configuration(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load configuration from all sources.

        Args:
            force_reload: Force reload even if already loaded

        Returns:
            Dictionary of all configuration values
        """
        with self._lock:
            if self._config and not force_reload:
                return self._get_config_values()

            self.logger.info("Loading configuration from all sources...")

            # Start with defaults
            self._config = self._default_config.copy()

            # Load from environment variables
            self._load_from_environment()

            # Load from configuration files
            for config_file in self._config_files:
                self._load_from_file(config_file)

            # Validate configuration
            self._validate_configuration()

            self.logger.info(f"Configuration loaded successfully ({len(self._config)} settings)")
            return self._get_config_values()

    def _load_from_environment(self):
        """Load configuration from environment variables."""
        for key, config_value in self._config.items():
            # Convert config key to environment variable name
            env_var = f"{self.config_name}_{key.replace('.', '_').upper()}"

            if env_var in os.environ:
                env_value = os.environ[env_var]
                parsed_value = self._parse_env_value(env_value, config_value.value)

                if parsed_value is not None:
                    self._config[key] = ConfigValue(
                        value=parsed_value,
                        source=ConfigSource.ENVIRONMENT,
                        description=config_value.description,
                        sensitive=config_value.sensitive,
                        validation_rules=config_value.validation_rules
                    )
                    self.logger.debug(f"Loaded {key} from environment: {env_var}")

    def _load_from_file(self, file_path: Path):
        """Load configuration from a file.

        Args:
            file_path: Path to configuration file
        """
        try:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
            else:
                self.logger.warning(f"Unsupported config file format: {file_path}")
                return

            if not isinstance(file_config, dict):
                self.logger.warning(f"Invalid config file format: {file_path}")
                return

            # Flatten nested configuration
            flat_config = self._flatten_config(file_config)

            # Update configuration values
            for key, value in flat_config.items():
                if key in self._config:
                    self._config[key] = ConfigValue(
                        value=value,
                        source=ConfigSource.YAML_FILE if file_path.suffix.lower() in ['.yaml', '.yml'] else ConfigSource.JSON_FILE,
                        description=self._config[key].description,
                        sensitive=self._config[key].sensitive,
                        validation_rules=self._config[key].validation_rules
                    )
                    self.logger.debug(f"Loaded {key} from file: {file_path}")

        except Exception as e:
            self.logger.error(f"Failed to load config file {file_path}: {e}")

    def _flatten_config(self, config: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """Flatten nested configuration dictionary.

        Args:
            config: Nested configuration dictionary
            prefix: Key prefix for nested keys

        Returns:
            Flattened configuration dictionary
        """
        flattened = {}

        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                flattened.update(self._flatten_config(value, full_key))
            else:
                flattened[full_key] = value

        return flattened

    def _parse_env_value(self, env_value: str, default_value: Any) -> Any:
        """Parse environment variable value based on default value type.

        Args:
            env_value: Environment variable value as string
            default_value: Default value to determine type

        Returns:
            Parsed value
        """
        if isinstance(default_value, bool):
            return env_value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(default_value, int):
            try:
                return int(env_value)
            except ValueError:
                self.logger.warning(f"Invalid integer value for environment variable: {env_value}")
                return default_value
        elif isinstance(default_value, float):
            try:
                return float(env_value)
            except ValueError:
                self.logger.warning(f"Invalid float value for environment variable: {env_value}")
                return default_value
        elif isinstance(default_value, list):
            # Split comma-separated values
            if env_value.strip():
                return [item.strip() for item in env_value.split(',') if item.strip()]
            return default_value
        else:
            return env_value

    def _validate_configuration(self):
        """Validate configuration values against their rules."""
        for key, config_value in self._config.items():
            rules = config_value.validation_rules

            if not rules:
                continue

            # Type validation
            if 'type' in rules:
                expected_type = rules['type']
                actual_type = type(config_value.value).__name__

                if expected_type == 'int' and not isinstance(config_value.value, int):
                    raise ConfigurationError(f"Configuration {key}: expected int, got {actual_type}")
                elif expected_type == 'float' and not isinstance(config_value.value, (int, float)):
                    raise ConfigurationError(f"Configuration {key}: expected float, got {actual_type}")
                elif expected_type == 'bool' and not isinstance(config_value.value, bool):
                    raise ConfigurationError(f"Configuration {key}: expected bool, got {actual_type}")

            # Range validation
            if 'min' in rules and isinstance(config_value.value, (int, float)):
                if config_value.value < rules['min']:
                    raise ConfigurationError(f"Configuration {key}: value {config_value.value} below minimum {rules['min']}")

            if 'max' in rules and isinstance(config_value.value, (int, float)):
                if config_value.value > rules['max']:
                    raise ConfigurationError(f"Configuration {key}: value {config_value.value} above maximum {rules['max']}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key (dot notation)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        with self._lock:
            if key in self._config:
                return self._config[key].value
            return default

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values.

        Returns:
            Dictionary of all configuration values
        """
        return self._get_config_values()

    def get_sensitive(self, key: str) -> str:
        """Get sensitive configuration value (masked for logging).

        Args:
            key: Configuration key

        Returns:
            Configuration value (masked if sensitive)
        """
        value = self.get(key)
        if key in self._config and self._config[key].sensitive:
            if isinstance(value, str) and len(value) > 4:
                return f"{value[:2]}***{value[-2:]}"
        return str(value)

    def _get_config_values(self) -> Dict[str, Any]:
        """Get configuration values dictionary."""
        return {key: config_value.value for key, config_value in self._config.items()}

    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.DEFAULT):
        """Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
            source: Source of the configuration
        """
        with self._lock:
            if key in self._config:
                self._config[key] = ConfigValue(
                    value=value,
                    source=source,
                    description=self._config[key].description,
                    sensitive=self._config[key].sensitive,
                    validation_rules=self._config[key].validation_rules
                )
            else:
                self._config[key] = ConfigValue(
                    value=value,
                    source=source,
                    description=""
                )

    def add_config_file(self, file_path: Union[str, Path]):
        """Add a configuration file to load from.

        Args:
            file_path: Path to configuration file
        """
        config_path = Path(file_path)

        if config_path not in self._config_files and config_path.exists():
            self._config_files.append(config_path)
            self.logger.info(f"Added configuration file: {config_path}")
            # Reload configuration
            self.load_configuration(force_reload=True)

    def save_to_file(self, file_path: Union[str, Path], format: str = 'yaml') -> bool:
        """Save current configuration to file.

        Args:
            file_path: Path to save configuration
            format: File format ('yaml' or 'json')

        Returns:
            True if saved successfully
        """
        try:
            config_path = Path(file_path)
            config_data = self._get_config_values()

            if format.lower() in ['yaml', 'yml']:
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
            elif format.lower() == 'json':
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")

            self.logger.info(f"Configuration saved to {config_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False

    def get_config_sources(self) -> Dict[str, ConfigSource]:
        """Get the source of each configuration value.

        Returns:
            Dictionary mapping keys to their sources
        """
        return {key: config_value.source for key, config_value in self._config.items()}

    def get_config_info(self, key: str) -> Optional[ConfigValue]:
        """Get full configuration information for a key.

        Args:
            key: Configuration key

        Returns:
            ConfigValue object or None if not found
        """
        return self._config.get(key)

    def validate_current_config(self) -> List[str]:
        """Validate current configuration and return any errors.

        Returns:
            List of validation error messages
        """
        errors = []

        try:
            self._validate_configuration()
        except ConfigurationError as e:
            errors.append(str(e))

        return errors


# Global configuration manager instance
config_manager = UnifiedConfigManager()


@contextmanager
def config_context(**overrides):
    """Context manager for temporarily overriding configuration values.

    Args:
        **overrides: Configuration key-value pairs to override

    Example:
        with config_context('performance.max_workers': 4, 'logging.level': 'DEBUG'):
            # Configuration is temporarily overridden
            pass
        # Configuration is restored to previous values
    """
    # Store original values
    original_values = {}

    try:
        for key, value in overrides.items():
            original_values[key] = config_manager.get(key)
            config_manager.set(key, value)

        yield

    finally:
        # Restore original values
        for key, value in original_values.items():
            config_manager.set(key, value)


def get_config(key: str, default: Any = None) -> Any:
    """Convenience function to get configuration value."""
    return config_manager.get(key, default)


def set_config(key: str, value: Any):
    """Convenience function to set configuration value."""
    config_manager.set(key, value)


def init_configuration():
    """Initialize configuration system."""
    try:
        config_manager.load_configuration()
        config_manager.logger.info("Configuration system initialized")
    except Exception as e:
        config_manager.logger.error(f"Failed to initialize configuration: {e}")
        raise
