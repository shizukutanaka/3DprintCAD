"""Configuration management system with validation and environment support."""
from __future__ import annotations

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
import logging
from copy import deepcopy
@dataclass
class PrinterProfile:
    """3D printer configuration profile."""
    name: str
    manufacturer: str
    model: str

    # Build volume (mm)
    build_volume_x: float
    build_volume_y: float
    build_volume_z: float

    # Nozzle specifications
    nozzle_diameter: float = 0.4
    max_nozzle_temp: int = 260

    # Bed specifications
    heated_bed: bool = True
    max_bed_temp: int = 100
    bed_shape: str = "rectangular"  # "rectangular", "circular"

    # Machine capabilities
    enclosed: bool = False
    auto_bed_leveling: bool = False
    filament_runout_sensor: bool = False

    # Speed limits (mm/min)
    max_print_speed: int = 4800
    max_travel_speed: int = 12000

    # Support specifications
    supports_dual_extrusion: bool = False
    supports_soluble_supports: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PrinterProfile:
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ValidationConfig:
    """Mesh validation configuration."""

    # Geometric thresholds
    min_wall_thickness_mm: float = 0.8
    min_feature_size_mm: float = 0.4
    support_overhang_angle_deg: float = 60.0
    min_hole_diameter_mm: float = 1.0
    max_surface_roughness_score: float = 1.7
    min_bed_contact_area_mm2: float = 150.0
    min_model_extent_mm: float = 0.2
    max_model_extent_mm: float = 2000.0
    max_flatness_deviation_mm: float = 0.1

    # Analysis options
    enable_wall_thickness_check: bool = True
    enable_overhang_detection: bool = True
    enable_feature_size_check: bool = True
    enable_self_intersection_check: bool = True
    enable_manifold_check: bool = True
    enable_surface_quality_check: bool = True

    # Performance settings
    max_ray_samples: int = 400
    parallel_processing: bool = False
    cache_results: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ValidationConfig:
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ApplicationConfig:
    """Main application configuration."""

    # File handling
    default_output_format: str = "json"
    auto_backup_reports: bool = True
    max_file_size_mb: int = 500
    max_manifest_bytes: int = 5 * 1024 * 1024
    max_manifest_entries: int = 2000

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "printcad.log"

    # UI preferences
    show_progress_bars: bool = True
    colored_output: bool = True
    verbose_errors: bool = True

    # Performance
    use_multiprocessing: bool = False
    max_worker_processes: int = 4
    memory_limit_mb: int = 2048

    # ROI heuristics for CLI analytics
    manual_review_base_minutes: float = 8.0
    manual_review_per_issue_minutes: float = 4.0
    manual_repair_overhead_minutes: float = 6.0
    manual_slicing_setup_minutes: float = 7.0
    manual_review_cost_rate_usd: float = 32.0

    # Security defaults
    enforce_hash_manifest: bool = True
    allowed_input_roots: List[str] = field(default_factory=list)
    allowed_output_root: Optional[str] = None
    default_read_only_output: bool = False
    default_language_mode: str = "bilingual"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApplicationConfig:
        """Create from dictionary with defensive type coercion."""

        sanitized: Dict[str, Any] = dict(data or {})
        defaults = cls()
        sanitized["allowed_input_roots"] = _coerce_str_list(sanitized.get("allowed_input_roots"))

        allowed_output = sanitized.get("allowed_output_root")
        if isinstance(allowed_output, str):
            sanitized["allowed_output_root"] = allowed_output.strip() or None
        elif allowed_output is None:
            sanitized["allowed_output_root"] = None
        else:
            sanitized["allowed_output_root"] = str(allowed_output)

        sanitized["enforce_hash_manifest"] = bool(sanitized.get("enforce_hash_manifest", False))
        sanitized["default_read_only_output"] = bool(sanitized.get("default_read_only_output", False))

        language_mode = str(sanitized.get("default_language_mode", "bilingual"))
        if language_mode not in {"en", "ja", "bilingual"}:
            language_mode = "bilingual"
        sanitized["default_language_mode"] = language_mode

        sanitized["max_manifest_bytes"] = _coerce_positive_int(
            sanitized.get("max_manifest_bytes"),
            defaults.max_manifest_bytes,
        )
        sanitized["max_manifest_entries"] = _coerce_positive_int(
            sanitized.get("max_manifest_entries"),
            defaults.max_manifest_entries,
        )

        return cls(**sanitized)


@dataclass
class Config:
    """Main configuration container."""

    application: ApplicationConfig = field(default_factory=ApplicationConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    printer_profiles: Dict[str, PrinterProfile] = field(default_factory=dict)
    active_printer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "application": self.application.to_dict(),
            "validation": self.validation.to_dict(),
            "printer_profiles": {name: profile.to_dict() for name, profile in self.printer_profiles.items()},
            "active_printer": self.active_printer
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Config:
        """Create from dictionary."""
        return cls(
            application=ApplicationConfig.from_dict(data.get("application", {})),
            validation=ValidationConfig.from_dict(data.get("validation", {})),
            printer_profiles={
                name: PrinterProfile.from_dict(profile_data)
                for name, profile_data in data.get("printer_profiles", {}).items()
            },
            active_printer=data.get("active_printer")
        )

    def get_active_printer(self) -> Optional[PrinterProfile]:
        """Get currently active printer profile."""
        if self.active_printer and self.active_printer in self.printer_profiles:
            return self.printer_profiles[self.active_printer]
        return None

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        config = self.load()
        return {
            "level": config.application.log_level,
            "to_file": config.application.log_to_file,
            "file_path": config.application.log_file_path
        }

    def set_active_printer(self, profile_name: str):
        """Set active printer profile."""
        if profile_name not in self.printer_profiles:
            raise ValueError(f"Printer profile '{profile_name}' not found")
        self.active_printer = profile_name


class ConfigManager:
    """Centralized configuration management with validation and environment support."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.config_dir.mkdir(exist_ok=True)

        self._config: Dict[str, Any] = {}
        self._schema: Dict[str, ConfigSchema] = {}
        self._config_files: List[Path] = []
        self._config_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = 60  # seconds

        self._setup_default_schema()
        self._load_configurations()

    def _setup_default_schema(self):
        """Setup default configuration schema."""
        schemas = [
            # Application settings
            ConfigSchema(
                key="app.name",
                default="3D Print CAD Assistant",
                type_hint=str,
                description="Application name",
                env_var="APP_NAME"
            ),
            ConfigSchema(
                key="app.version",
                default="2.0.0",
                type_hint=str,
                description="Application version",
                env_var="APP_VERSION"
            ),
            ConfigSchema(
                key="app.debug",
                default=False,
                type_hint=bool,
                description="Enable debug mode",
                env_var="DEBUG"
            ),
            ConfigSchema(
                key="app.environment",
                default="development",
                type_hint=str,
                description="Application environment",
                env_var="ENVIRONMENT",
                choices=["development", "staging", "production"]
            ),

            # Security settings
            ConfigSchema(
                key="security.secret_key",
                default=None,
                type_hint=str,
                description="Secret key for encryption",
                required=True,
                env_var="SECRET_KEY"
            ),
            ConfigSchema(
                key="security.allowed_origins",
                default=["http://localhost:*"],
                type_hint=list,
                description="Allowed CORS origins",
                env_var="ALLOWED_ORIGINS"
            ),
            ConfigSchema(
                key="security.allowed_extensions",
                default=[".stl", ".obj", ".ply", ".3mf", ".amf"],
                type_hint=list,
                description="Allowed file extensions",
                env_var="ALLOWED_EXTENSIONS"
            ),
            ConfigSchema(
                key="security.block_suspicious_files",
                default=True,
                type_hint=bool,
                description="Block files with suspicious patterns",
                env_var="BLOCK_SUSPICIOUS_FILES"
            ),

            # Cache settings
            ConfigSchema(
                key="cache.enabled",
                default=True,
                type_hint=bool,
                description="Enable caching",
                env_var="CACHE_ENABLED"
            ),
            ConfigSchema(
                key="cache.ttl_seconds",
                default=3600,
                type_hint=int,
                description="Cache TTL in seconds",
                env_var="CACHE_TTL_SECONDS",
                validator=lambda x: x > 0
            ),
            ConfigSchema(
                key="cache.max_size_mb",
                default=1024,
                type_hint=int,
                description="Maximum cache size in MB",
                env_var="CACHE_MAX_SIZE_MB",
                validator=lambda x: x > 0
            ),

            # Performance settings
            ConfigSchema(
                key="performance.max_workers",
                default=None,
                type_hint=int,
                description="Maximum number of worker processes",
                env_var="MAX_WORKERS"
            ),
            ConfigSchema(
                key="performance.timeout_seconds",
                default=300,
                type_hint=int,
                description="Default timeout for operations in seconds",
                env_var="OPERATION_TIMEOUT_SECONDS",
                validator=lambda x: x > 0
            ),

            # Database settings
            ConfigSchema(
                key="database.url",
                default="sqlite:///app.db",
                type_hint=str,
                description="Database connection URL",
                env_var="DATABASE_URL"
            ),
            ConfigSchema(
                key="database.pool_size",
                default=10,
                type_hint=int,
                description="Database connection pool size",
                env_var="DB_POOL_SIZE",
                validator=lambda x: x > 0 and x <= 100
            ),

            # Cache settings
            ConfigSchema(
                key="cache.enabled",
                default=True,
                type_hint=bool,
                description="Enable caching",
                env_var="CACHE_ENABLED"
            ),
            ConfigSchema(
                key="cache.size_mb",
                default=512,
                type_hint=int,
                description="Cache size in MB",
                env_var="CACHE_SIZE_MB",
                validator=lambda x: x > 0 and x <= 4096
            ),
            ConfigSchema(
                key="cache.ttl_seconds",
                default=3600,
                type_hint=int,
                description="Cache TTL in seconds",
                env_var="CACHE_TTL",
                validator=lambda x: x > 0
            ),

            # Processing settings
            ConfigSchema(
                key="processing.max_workers",
                default=4,
                type_hint=int,
                description="Maximum worker threads",
                env_var="MAX_WORKERS",
                validator=lambda x: x > 0 and x <= 64
            ),
            ConfigSchema(
                key="processing.timeout_seconds",
                default=300,
                type_hint=int,
                description="Processing timeout in seconds",
                env_var="PROCESSING_TIMEOUT",
                validator=lambda x: x > 0
            ),

            # Mesh validation settings
            ConfigSchema(
                key="validation.min_wall_thickness",
                default=0.4,
                type_hint=float,
                description="Minimum wall thickness in mm",
                env_var="MIN_WALL_THICKNESS",
                validator=lambda x: x >= 0.1 and x <= 10.0
            ),
            ConfigSchema(
                key="validation.min_feature_size",
                default=0.2,
                type_hint=float,
                description="Minimum feature size in mm",
                env_var="MIN_FEATURE_SIZE",
                validator=lambda x: x >= 0.05 and x <= 5.0
            ),
            ConfigSchema(
                key="validation.max_overhang_angle",
                default=45.0,
                type_hint=float,
                description="Maximum overhang angle in degrees",
                env_var="MAX_OVERHANG_ANGLE",
                validator=lambda x: x >= 0 and x <= 90
            ),

            # Logging settings
            ConfigSchema(
                key="logging.level",
                default="INFO",
                type_hint=str,
                description="Logging level",
                env_var="LOG_LEVEL",
                choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            ),
            ConfigSchema(
                key="logging.file_enabled",
                default=True,
                type_hint=bool,
                description="Enable file logging",
                env_var="LOG_FILE_ENABLED"
            ),
            ConfigSchema(
                key="logging.max_file_size_mb",
                default=10,
                type_hint=int,
                description="Maximum log file size in MB",
                env_var="LOG_MAX_FILE_SIZE",
                validator=lambda x: x > 0 and x <= 100
            ),

            # Web server settings
            ConfigSchema(
                key="web.host",
                default="localhost",
                type_hint=str,
                description="Web server host",
                env_var="WEB_HOST"
            ),
            ConfigSchema(
                key="web.port",
                default=5000,
                type_hint=int,
                description="Web server port",
                env_var="WEB_PORT",
                validator=lambda x: x > 0 and x <= 65535
            ),
            ConfigSchema(
                key="web.workers",
                default=1,
                type_hint=int,
                description="Number of web workers",
                env_var="WEB_WORKERS",
                validator=lambda x: x > 0 and x <= 16
            ),

            # Feature flags
            ConfigSchema(
                key="features.ai_analysis",
                default=False,
                type_hint=bool,
                description="Enable AI-powered analysis",
                env_var="ENABLE_AI_ANALYSIS"
            ),
            ConfigSchema(
                key="features.blockchain_integration",
                default=False,
                type_hint=bool,
                description="Enable blockchain features",
                env_var="ENABLE_BLOCKCHAIN"
            ),
            ConfigSchema(
                key="features.cloud_storage",
                default=False,
                type_hint=bool,
                description="Enable cloud storage",
                env_var="ENABLE_CLOUD_STORAGE"
            ),
        ]

        for schema in schemas:
            self._schema[schema.key] = schema

    def _load_configurations(self):
        """Load configuration from various sources."""
        # Load default values
        for key, schema in self._schema.items():
            self._set_nested(self._config, key, schema.default)

        # Load from config files
        config_files = [
            self.config_dir / "default.yaml",
            self.config_dir / "default.json",
            self.config_dir / f"{self.get('app.environment', 'development')}.yaml",
            self.config_dir / f"{self.get('app.environment', 'development')}.json",
            self.config_dir / "local.yaml",
            self.config_dir / "local.json",
        ]

        for config_file in config_files:
            if config_file.exists():
                self._load_config_file(config_file)

        # Override with environment variables
        self._load_from_environment()

        # Validate configuration
        self._validate_configuration()

    def _load_config_file(self, config_file: Path):
        """Load configuration from a file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix.lower() == '.yaml' or config_file.suffix.lower() == '.yml':
                    file_config = yaml.safe_load(f)
                elif config_file.suffix.lower() == '.json':
                    file_config = json.load(f)
                else:
                    logger.warning(f"Unsupported config file format: {config_file}")
                    return

            if file_config:
                self._merge_config(self._config, file_config)
                self._config_files.append(config_file)
                logger.info(f"Loaded configuration from {config_file}")

        except Exception as e:
            logger.error(f"Failed to load config file {config_file}: {e}")

    def _load_from_environment(self):
        """Load configuration from environment variables."""
        for key, schema in self._schema.items():
            if schema.env_var:
                env_value = os.environ.get(schema.env_var)
                if env_value is not None:
                    # Convert to appropriate type
                    try:
                        converted_value = self._convert_env_value(env_value, schema.type_hint)
                        self._set_nested(self._config, key, converted_value)
                        logger.debug(f"Set {key} from environment variable {schema.env_var}")
                    except Exception as e:
                        logger.error(f"Failed to convert environment variable {schema.env_var}: {e}")

    def _convert_env_value(self, value: str, target_type: type) -> Any:
        """Convert environment variable string to target type."""
        if target_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == list:
            # Split by comma and strip whitespace
            return [item.strip() for item in value.split(',') if item.strip()]
        else:
            return value

    def _validate_configuration(self):
        """Validate configuration against schema."""
        errors = []

        for key, schema in self._schema.items():
            value = self.get(key)

            # Check required fields
            if schema.required and value is None:
                errors.append(f"Required configuration '{key}' is missing")
                continue

            if value is not None:
                # Type validation
                if not isinstance(value, schema.type_hint):
                    try:
                        # Try conversion
                        if schema.type_hint == bool and isinstance(value, str):
                            value = value.lower() in ('true', '1', 'yes', 'on')
                        else:
                            value = schema.type_hint(value)
                        self._set_nested(self._config, key, value)
                    except (ValueError, TypeError):
                        errors.append(f"Configuration '{key}' has invalid type. Expected {schema.type_hint.__name__}")
                        continue

                # Choice validation
                if schema.choices and value not in schema.choices:
                    errors.append(f"Configuration '{key}' has invalid value '{value}'. Must be one of: {schema.choices}")

                # Custom validator
                if schema.validator and not schema.validator(value):
                    errors.append(f"Configuration '{key}' failed validation")

        if errors:
            raise ConfigurationError(f"Configuration validation failed:\n" + "\n".join(errors))

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Recursively merge configuration dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _set_nested(self, config: Dict[str, Any], key: str, value: Any):
        """Set nested configuration value using dot notation."""
        keys = key.split('.')
        current = config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

    def _get_nested(self, config: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Get nested configuration value using dot notation."""
        keys = key.split('.')
        current = config

        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with caching."""
        import time

        # Check cache first
        if (self._config_cache is not None and
            self._cache_timestamp is not None and
            time.time() - self._cache_timestamp < self._cache_ttl):
            return self._get_nested(self._config_cache, key, default)

        # Load fresh config if cache is stale
        return self._get_nested(self._config, key, default)

    def refresh_cache(self) -> None:
        """Refresh configuration cache."""
        import time
        self._config_cache = deepcopy(self._config)
        self._cache_timestamp = time.time()

    def update(self, updates: Dict[str, Any], persist: bool = False):
        """Update multiple configuration values."""
        for key, value in updates.items():
            self.set(key, value, persist=False)

        if persist:
            self._save_local_config()

    def set(self, key: str, value: Any, persist: bool = False):
        """Set configuration value."""
        self._set_nested(self._config, key, value)
        if persist:
            self._save_local_config()
            self.refresh_cache()
            self.backup_config()

    def _save_local_config(self):
        """Save current configuration to local config file."""
        local_config_file = self.config_dir / "local.yaml"

        try:
            with open(local_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False)
            logger.info(f"Saved configuration to {local_config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def export_detailed_config(self, file_path: Path, include_sensitive: bool = False) -> None:
        """Export detailed configuration including schema information."""
        export_data = {
            'config': self._config,
            'schema': self.get_schema_info(),
            'summary': self.get_config_summary(),
            'export_time': datetime.now(timezone.utc).isoformat()
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Exported detailed configuration to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export detailed configuration: {e}")
            raise

    def backup_config(self, backup_path: Optional[Path] = None) -> Path:
        """Create a backup of current configuration."""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.config_dir / f"config_backup_{timestamp}.json"

        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'config': self._config,
                    'schema': {k: v.__dict__ for k, v in self._schema.items()},
                    'backup_time': datetime.now(timezone.utc).isoformat()
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration backed up to {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to backup configuration: {e}")
            raise

    def get_schema_info(self) -> Dict[str, Dict[str, Any]]:
        """Get schema information for all configuration keys."""
        schema_info = {}

        for key, schema in self._schema.items():
            schema_info[key] = {
                'type': schema.type_hint.__name__,
                'default': schema.default,
                'description': schema.description,
                'required': schema.required,
                'env_var': schema.env_var,
                'choices': schema.choices,
                'current_value': self.get(key)
            }

    def validate_current_config(self) -> Dict[str, List[str]]:
        """Validate current configuration against schema."""
        errors = {}

        for key, schema in self._schema.items():
            value = self.get(key)

            if schema.required and value is None:
                errors.setdefault(key, []).append("Required field is missing")
                continue

            if value is not None:
                if not isinstance(value, schema.type_hint):
                    errors.setdefault(key, []).append(f"Invalid type: expected {schema.type_hint.__name__}")

                if schema.choices and value not in schema.choices:
                    errors.setdefault(key, []).append(f"Invalid value: must be one of {schema.choices}")

                if schema.validator and not schema.validator(value):
                    errors.setdefault(key, []).append("Failed custom validation")

        return errors

    def validate_key(self, key: str, value: Any) -> bool:
        """Validate a specific key-value pair."""
        if key not in self._schema:
            return True  # Unknown keys are allowed

        schema = self._schema[key]

        # Type validation
        if not isinstance(value, schema.type_hint):
            return False

        # Choice validation
        if schema.choices and value not in schema.choices:
            return False

        # Custom validator
        if schema.validator and not schema.validator(value):
            return False

        return True

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging."""
        return {
            'config_files_loaded': [str(f) for f in self._config_files],
            'environment': self.get('app.environment'),
            'debug_mode': self.get('app.debug'),
            'total_config_keys': len(self._config),
            'schema_keys': len(self._schema)
        }


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value using global manager."""
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any, persist: bool = False):
    """Set configuration value using global manager."""
    return get_config_manager().set(key, value, persist)


def init_config(config_dir: Optional[Path] = None) -> ConfigManager:
    """Initialize global configuration manager."""
    global _config_manager
    _config_manager = ConfigManager(config_dir)
    return _config_manager