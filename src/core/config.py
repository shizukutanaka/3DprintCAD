"""Configuration management for 3D print validation and recommendations."""
from __future__ import annotations

import json
import logging
import os
import stat
import copy
import hashlib
import hmac
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Iterable

import yaml

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration payload fails schema validation."""


class ConfigSignatureError(ConfigValidationError):
    """Raised when configuration signature verification fails."""


def _coerce_str_list(value: Optional[Union[str, Iterable[Any]]]) -> List[str]:
    """Normalize configuration values that are expected to be lists of strings."""

    if value is None:
        return []

    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, dict):
        candidates = [key for key in value.keys() if key]
    elif isinstance(value, Iterable):
        candidates = list(value)
    else:
        return []

    normalized: List[str] = []
    for candidate in candidates:
        candidate_str = str(candidate).strip()
        if candidate_str:
            normalized.append(candidate_str)
    return normalized


def _coerce_positive_int(value: Any, fallback: Optional[int]) -> Optional[int]:
    """Convert value to positive integer, returning fallback when invalid."""

    if value is None:
        return fallback

    try:
        candidate = int(value)
    except (TypeError, ValueError):
        return fallback

    if candidate <= 0:
        return fallback

    return candidate


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

    def set_active_printer(self, profile_name: str):
        """Set active printer profile."""
        if profile_name not in self.printer_profiles:
            raise ValueError(f"Printer profile '{profile_name}' not found")
        self.active_printer = profile_name


class ConfigManager:
    """Manages configuration loading, saving, and validation."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or self._get_default_config_dir()
        self.config_file = self.config_dir / "config.yaml"
        self._config: Optional[Config] = None
        self._ensure_config_dir()

    def _get_default_config_dir(self) -> Path:
        """Get default configuration directory."""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', '~')) / 'printcad'
        else:  # Unix-like
            config_dir = Path.home() / '.config' / 'printcad'

        return config_dir.expanduser()

    def _ensure_config_dir(self):
        """Ensure configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._harden_config_dir()

    def _harden_config_dir(self):
        """Apply restrictive permissions to the configuration directory on POSIX."""

        if os.name == "nt":  # Windows manages ACLs differently
            return

        try:
            current_mode = stat.S_IMODE(self.config_dir.stat().st_mode)
            if current_mode != 0o700:
                self.config_dir.chmod(0o700)
        except OSError as exc:
            logger.warning("Failed to harden configuration directory permissions: %s", exc)

    def _harden_config_file(self):
        """Ensure the configuration file is only readable by the owner."""

        if os.name == "nt" or not self.config_file.exists():
            return

        try:
            current_mode = stat.S_IMODE(self.config_file.stat().st_mode)
            if current_mode != 0o600:
                self.config_file.chmod(0o600)
        except OSError as exc:
            logger.warning("Failed to harden configuration file permissions: %s", exc)

    def _assert_secure_permissions(self):
        """Warn and remediate overly permissive configuration file modes."""

        if os.name == "nt" or not self.config_file.exists():
            return

        try:
            current_mode = stat.S_IMODE(self.config_file.stat().st_mode)
            if current_mode & 0o077:
                logger.warning(
                    "Configuration file %s has overly permissive permissions (%s). "
                    "Resetting to 0600 for safety.",
                    self.config_file,
                    oct(current_mode),
                )
                self._harden_config_file()
        except OSError as exc:
            logger.warning("Unable to inspect configuration file permissions: %s", exc)

    def load(self) -> Config:
        """Load configuration from file."""
        if self._config is not None:
            return self._config

        if self.config_file.exists():
            try:
                self._assert_secure_permissions()
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    raw_payload = f.read()

                data = yaml.safe_load(raw_payload)
                payload = data or {}
                _validate_config_schema(payload)
                self._verify_config_signature(payload)

                self._config = Config.from_dict(payload)
                logger.info("Loaded configuration from %s", self.config_file)

            except ConfigSignatureError:
                logger.error("Configuration signature validation failed for %s", self.config_file)
                raise
            except ConfigValidationError as exc:
                logger.warning("Config schema validation failed for %s: %s", self.config_file, exc)
                self._config = self._create_default_config()
            except Exception as e:
                logger.warning("Failed to load config from %s: %s", self.config_file, e)
                self._config = self._create_default_config()
        else:
            self._config = self._create_default_config()
            self.save()  # Save default configuration

        return self._config

    def save(self, config: Optional[Config] = None):
        """Save configuration to file."""
        config = config or self._config or self._create_default_config()

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)

            self._config = config
            self._harden_config_dir()
            self._harden_config_file()
            logger.info(f"Saved configuration to {self.config_file}")

        except Exception as e:
            logger.error(f"Failed to save config to {self.config_file}: {e}")
            raise

    def _create_default_config(self) -> Config:
        """Create default configuration with common printer profiles."""
        config = Config()

        # Add common printer profiles
        config.printer_profiles["prusa_i3_mk3"] = PrinterProfile(
            name="Prusa i3 MK3S",
            manufacturer="Prusa Research",
            model="i3 MK3S",
            build_volume_x=250,
            build_volume_y=210,
            build_volume_z=210,
            nozzle_diameter=0.4,
            max_nozzle_temp=300,
            heated_bed=True,
            max_bed_temp=120,
            bed_shape="rectangular",
            enclosed=False,
            auto_bed_leveling=True,
            filament_runout_sensor=True,
            max_print_speed=4800,
            max_travel_speed=12000
        )

        config.printer_profiles["ender_3"] = PrinterProfile(
            name="Creality Ender 3",
            manufacturer="Creality",
            model="Ender 3",
            build_volume_x=220,
            build_volume_y=220,
            build_volume_z=250,
            nozzle_diameter=0.4,
            max_nozzle_temp=260,
            heated_bed=True,
            max_bed_temp=100,
            bed_shape="rectangular",
            enclosed=False,
            auto_bed_leveling=False,
            filament_runout_sensor=False,
            max_print_speed=3600,
            max_travel_speed=9000
        )

        config.printer_profiles["ultimaker_s3"] = PrinterProfile(
            name="Ultimaker S3",
            manufacturer="Ultimaker",
            model="S3",
            build_volume_x=230,
            build_volume_y=190,
            build_volume_z=200,
            nozzle_diameter=0.4,
            max_nozzle_temp=280,
            heated_bed=True,
            max_bed_temp=100,
            bed_shape="rectangular",
            enclosed=True,
            auto_bed_leveling=True,
            filament_runout_sensor=True,
            max_print_speed=4800,
            max_travel_speed=15000,
            supports_dual_extrusion=True,
            supports_soluble_supports=True
        )

        # Set default active printer
        config.active_printer = "prusa_i3_mk3"

        return config

    def _verify_config_signature(self, payload: Dict[str, Any]) -> None:
        auth_block = payload.get("config_auth")
        if not auth_block:
            return

        if not isinstance(auth_block, dict):
            raise ConfigValidationError("'config_auth' section must be a mapping when present")

        algorithm = auth_block.get("algorithm") or "hmac-sha256"
        signature = auth_block.get("signature")

        if not isinstance(algorithm, str):
            raise ConfigSignatureError("Config signature algorithm must be a string")

        if algorithm.lower() != "hmac-sha256":
            raise ConfigSignatureError(f"Unsupported config signature algorithm: {algorithm}")

        if not isinstance(signature, str) or not signature:
            raise ConfigSignatureError("Config signature is missing or invalid")

        shared_key = os.environ.get("PRINTCAD_CONFIG_HMAC_KEY")
        if not shared_key:
            raise ConfigSignatureError(
                "Signed configurations require PRINTCAD_CONFIG_HMAC_KEY environment variable"
            )

        expected = compute_config_signature(payload, shared_key)
        if not hmac.compare_digest(expected, signature):
            raise ConfigSignatureError("Config signature verification failed")

    def add_printer_profile(self, profile: PrinterProfile):
        """Add a new printer profile."""
        config = self.load()
        config.printer_profiles[profile.name.lower().replace(" ", "_")] = profile
        self.save(config)

    def remove_printer_profile(self, profile_name: str):
        """Remove a printer profile."""
        config = self.load()

        if profile_name not in config.printer_profiles:
            raise ValueError(f"Printer profile '{profile_name}' not found")

        if config.active_printer == profile_name:
            # Set another profile as active, or None if no others exist
            remaining = [name for name in config.printer_profiles if name != profile_name]
            config.active_printer = remaining[0] if remaining else None

        del config.printer_profiles[profile_name]
        self.save(config)

    def get_printer_profiles(self) -> Dict[str, PrinterProfile]:
        """Get all printer profiles."""
        return self.load().printer_profiles

    def update_validation_config(self, **kwargs):
        """Update validation configuration parameters."""
        config = self.load()

        for key, value in kwargs.items():
            if hasattr(config.validation, key):
                setattr(config.validation, key, value)
            else:
                raise ValueError(f"Unknown validation parameter: {key}")

        self.save(config)

    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self._config = None
        if self.config_file.exists():
            self.config_file.unlink()

        self._config = self._create_default_config()
        self.save()
        logger.info("Configuration reset to defaults")

    def export_config(self, output_path: Path, format: str = "yaml"):
        """Export configuration to file."""
        config = self.load()

        if format.lower() == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        elif format.lower() == "yaml":
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        logger.info(f"Configuration exported to {output_path}")

    def import_config(self, input_path: Path):
        """Import configuration from file."""
        if not input_path.exists():
            raise FileNotFoundError(f"Config file not found: {input_path}")

        try:
            if input_path.suffix.lower() == '.json':
                with open(input_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:  # Assume YAML
                with open(input_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

            config = Config.from_dict(data)
            self.save(config)
            logger.info(f"Configuration imported from {input_path}")

        except Exception as e:
            logger.error(f"Failed to import config from {input_path}: {e}")
            raise


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> Config:
    """Get current configuration."""
    return get_config_manager().load()


def save_config(config: Optional[Config] = None):
    """Save configuration."""
    get_config_manager().save(config)


def _validate_config_schema(payload: Dict[str, Any]) -> None:
    """Validate configuration schema for required fields and types."""
    if not isinstance(payload, dict):
        raise ConfigValidationError("Configuration must be a dictionary")

    # Validate application section if present
    if "application" in payload:
        app_config = payload["application"]
        if not isinstance(app_config, dict):
            raise ConfigValidationError("'application' section must be a dictionary")

        # Validate critical fields
        if "log_level" in app_config:
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if app_config["log_level"] not in valid_levels:
                raise ConfigValidationError(f"Invalid log_level. Must be one of {valid_levels}")

    # Validate validation section if present
    if "validation" in payload:
        validation_config = payload["validation"]
        if not isinstance(validation_config, dict):
            raise ConfigValidationError("'validation' section must be a dictionary")

        # Validate numeric thresholds
        numeric_fields = [
            "min_wall_thickness_mm", "min_feature_size_mm", "support_overhang_angle_deg"
        ]
        for field in numeric_fields:
            if field in validation_config:
                value = validation_config[field]
                if not isinstance(value, (int, float)) or value < 0:
                    raise ConfigValidationError(f"'{field}' must be a non-negative number")

    # Validate printer profiles if present
    if "printer_profiles" in payload:
        profiles = payload["printer_profiles"]
        if not isinstance(profiles, dict):
            raise ConfigValidationError("'printer_profiles' section must be a dictionary")


def compute_config_signature(payload: Dict[str, Any], shared_key: str) -> str:
    """Compute HMAC-SHA256 signature for configuration payload."""
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")

    if not shared_key:
        raise ValueError("Shared key is required for signature computation")

    # Create a copy without the signature field
    payload_copy = copy.deepcopy(payload)
    if "config_auth" in payload_copy:
        auth_block = payload_copy["config_auth"]
        if isinstance(auth_block, dict) and "signature" in auth_block:
            auth_block = dict(auth_block)
            auth_block.pop("signature", None)
            payload_copy["config_auth"] = auth_block

    # Serialize payload in a deterministic way
    serialized = json.dumps(payload_copy, sort_keys=True, separators=(',', ':'))

    # Compute HMAC-SHA256
    signature_bytes = hmac.new(
        shared_key.encode('utf-8'),
        serialized.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature_bytes