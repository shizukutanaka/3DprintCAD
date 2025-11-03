"""Unified configuration management using Pydantic v2.

Replaces scattered config from env vars, YAML files, and hard-coded values
with a single source of truth.

Provides:
- Type validation
- Environment variable override
- YAML/JSON file support
- Default values
- Runtime modification tracking
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, validator
import yaml
import json

logger = logging.getLogger(__name__)


class ApplicationConfig(BaseModel):
    """Application-level settings."""
    environment: str = Field(
        default="development",
        description="Execution environment (development, staging, production)"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    max_workers: int = Field(default=4, description="Maximum worker processes")
    worker_timeout_seconds: int = Field(default=120, description="Worker timeout")
    enable_analytics: bool = Field(default=False, description="Enable usage analytics")

    class Config:
        env_prefix = "PRINTCAD_"


class ValidationConfig(BaseModel):
    """Mesh validation parameters."""
    min_wall_thickness: float = Field(default=0.8, description="Minimum wall thickness (mm)")
    max_overhang_angle: float = Field(default=45.0, description="Maximum overhang angle")
    min_feature_size: float = Field(default=0.25, description="Minimum feature size (mm)")
    check_manifold: bool = Field(default=True, description="Check for manifold geometry")
    check_watertight: bool = Field(default=True, description="Check if mesh is watertight")
    detect_self_intersections: bool = Field(default=True, description="Detect self-intersecting faces")

    class Config:
        env_prefix = "PRINTCAD_VALIDATION_"

    @validator('min_wall_thickness')
    def validate_thickness(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("min_wall_thickness must be positive")
        if v > 50:
            logger.warning("min_wall_thickness > 50mm is unusual")
        return v

    @validator('max_overhang_angle')
    def validate_angle(cls, v: float) -> float:
        if not 0 <= v <= 90:
            raise ValueError("max_overhang_angle must be 0-90 degrees")
        return v


class ProcessingConfig(BaseModel):
    """Mesh processing parameters."""
    enable_repair: bool = Field(default=True, description="Enable automatic mesh repair")
    simplify_mesh: bool = Field(default=False, description="Simplify mesh geometry")
    simplification_target: float = Field(default=0.9, description="Target ratio for simplification")
    enable_smoothing: bool = Field(default=True, description="Enable surface smoothing")
    smoothing_iterations: int = Field(default=3, description="Smoothing iterations")

    class Config:
        env_prefix = "PRINTCAD_PROCESSING_"


class SecurityConfig(BaseModel):
    """Security-related settings."""
    encryption_key: Optional[str] = Field(
        default=None,
        description="Encryption key (from PRINTCAD_ENCRYPTION_KEY env var)"
    )
    enforce_hash_manifest: bool = Field(
        default=False,
        description="Require hash manifest for all files"
    )
    enable_rate_limiting: bool = Field(default=True, description="Enable API rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per minute")
    rate_limit_window_seconds: int = Field(default=60, description="Rate limit window")
    require_authentication: bool = Field(default=False, description="Require user authentication")
    allowed_upload_roots: List[str] = Field(
        default_factory=list,
        description="Allowed upload directory roots"
    )
    allowed_output_root: Optional[str] = Field(
        default=None,
        description="Allowed output directory"
    )

    class Config:
        env_prefix = "PRINTCAD_SECURITY_"

    @validator('rate_limit_requests')
    def validate_rate_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("rate_limit_requests must be positive")
        return v


class CacheConfig(BaseModel):
    """Caching configuration."""
    enable_caching: bool = Field(default=True, description="Enable result caching")
    cache_max_entries: int = Field(default=100, description="Maximum cache entries")
    cache_ttl_minutes: int = Field(default=60, description="Cache TTL in minutes")
    cache_location: str = Field(default=".cache", description="Cache directory")

    class Config:
        env_prefix = "PRINTCAD_CACHE_"


class DatabaseConfig(BaseModel):
    """Database configuration."""
    enabled: bool = Field(default=False, description="Enable database")
    url: Optional[str] = Field(default=None, description="Database URL")
    connection_pool_size: int = Field(default=10, description="Connection pool size")
    echo_queries: bool = Field(default=False, description="Log SQL queries")

    class Config:
        env_prefix = "PRINTCAD_DB_"


class PrintConfig(BaseModel):
    """Print-specific settings."""
    default_material: str = Field(default="PLA", description="Default print material")
    default_temperature: int = Field(default=200, description="Default print temperature (°C)")
    default_bed_temperature: int = Field(default=60, description="Default bed temperature (°C)")
    default_nozzle_diameter: float = Field(default=0.4, description="Default nozzle diameter (mm)")
    default_layer_height: float = Field(default=0.2, description="Default layer height (mm)")
    default_infill_density: float = Field(default=0.2, description="Default infill density (0-1)")

    class Config:
        env_prefix = "PRINTCAD_PRINT_"

    @validator('default_infill_density')
    def validate_infill(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("infill_density must be 0-1")
        return v


class Configuration(BaseModel):
    """Root configuration combining all subsystems."""
    application: ApplicationConfig = Field(default_factory=ApplicationConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    print_settings: PrintConfig = Field(default_factory=PrintConfig)

    class Config:
        env_prefix = "PRINTCAD_"

    @classmethod
    def from_env(cls) -> Configuration:
        """Load configuration from environment variables."""
        return cls(
            application=ApplicationConfig(),
            validation=ValidationConfig(),
            processing=ProcessingConfig(),
            security=SecurityConfig(),
            cache=CacheConfig(),
            database=DatabaseConfig(),
            print_settings=PrintConfig()
        )

    @classmethod
    def from_yaml(cls, filepath: str | Path) -> Configuration:
        """Load configuration from YAML file."""
        path = Path(filepath)
        if not path.exists():
            logger.warning("Config file not found: %s, using defaults", path)
            return cls()

        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except Exception as exc:
            logger.error("Failed to load config from %s: %s", path, exc)
            return cls()

    @classmethod
    def from_json(cls, filepath: str | Path) -> Configuration:
        """Load configuration from JSON file."""
        path = Path(filepath)
        if not path.exists():
            logger.warning("Config file not found: %s, using defaults", path)
            return cls()

        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except Exception as exc:
            logger.error("Failed to load config from %s: %s", path, exc)
            return cls()

    def to_yaml(self, filepath: str | Path) -> None:
        """Write configuration to YAML file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, 'w') as f:
                yaml.dump(self.dict(), f, default_flow_style=False)
            logger.info("Config written to %s", path)
        except Exception as exc:
            logger.error("Failed to write config to %s: %s", path, exc)

    def to_json(self, filepath: str | Path) -> None:
        """Write configuration to JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, 'w') as f:
                json.dump(self.dict(), f, indent=2)
            logger.info("Config written to %s", path)
        except Exception as exc:
            logger.error("Failed to write config to %s: %s", path, exc)

    def validate_production(self) -> List[str]:
        """Validate configuration for production use."""
        issues = []

        if self.application.environment != "production":
            issues.append("Application environment is not 'production'")

        if self.application.debug:
            issues.append("Debug mode is enabled (should be disabled)")

        if not self.security.encryption_key:
            issues.append("Encryption key not configured (set PRINTCAD_ENCRYPTION_KEY)")

        if not self.security.enforce_hash_manifest:
            issues.append("Hash manifest enforcement disabled (enable for compliance)")

        if not self.security.allowed_output_root:
            issues.append("Output root not restricted")

        if self.database.enabled and not self.database.url:
            issues.append("Database enabled but URL not configured")

        return issues


# Global configuration instance
_global_config: Optional[Configuration] = None


def load_config(
    env_only: bool = False,
    config_file: Optional[str] = None
) -> Configuration:
    """Load application configuration.

    Priority order:
    1. Environment variables (PRINTCAD_*)
    2. Config file (YAML/JSON)
    3. Built-in defaults
    """
    global _global_config

    if env_only:
        _global_config = Configuration.from_env()
    elif config_file:
        if config_file.endswith('.yaml') or config_file.endswith('.yml'):
            _global_config = Configuration.from_yaml(config_file)
        elif config_file.endswith('.json'):
            _global_config = Configuration.from_json(config_file)
        else:
            logger.warning("Unknown config file format: %s", config_file)
            _global_config = Configuration.from_env()
    else:
        # Try default locations
        for path in [
            'config/production.yaml',
            'config/development.yaml',
            'config.yaml',
            'config.json'
        ]:
            if Path(path).exists():
                logger.info("Loading config from %s", path)
                if path.endswith('.json'):
                    _global_config = Configuration.from_json(path)
                else:
                    _global_config = Configuration.from_yaml(path)
                break

        if _global_config is None:
            _global_config = Configuration.from_env()

    logger.info(
        "Configuration loaded (environment=%s, debug=%s)",
        _global_config.application.environment,
        _global_config.application.debug
    )

    return _global_config


def get_config() -> Configuration:
    """Get current global configuration."""
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def reload_config(config_file: Optional[str] = None) -> Configuration:
    """Reload configuration (useful for testing)."""
    global _global_config
    _global_config = load_config(config_file=config_file)
    return _global_config


__all__ = [
    'Configuration',
    'ApplicationConfig',
    'ValidationConfig',
    'ProcessingConfig',
    'SecurityConfig',
    'CacheConfig',
    'DatabaseConfig',
    'PrintConfig',
    'load_config',
    'get_config',
    'reload_config'
]
