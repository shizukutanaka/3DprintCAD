"""Unit tests for configuration management."""
import json
import tempfile
from pathlib import Path

import pytest
import yaml

from src.core.config import (
    Config,
    ConfigManager,
    ApplicationConfig,
    ValidationConfig,
    PrinterProfile,
    get_config_manager,
    get_config
)


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def test_application_config_defaults():
    """Test ApplicationConfig default values."""
    config = ApplicationConfig()

    assert config.default_output_format == "json"
    assert config.auto_backup_reports is True
    assert config.max_file_size_mb == 500
    assert config.log_level == "INFO"
    assert config.log_to_file is True
    assert config.use_multiprocessing is False


def test_application_config_serialization():
    """Test ApplicationConfig serialization."""
    config = ApplicationConfig(
        default_output_format="yaml",
        max_file_size_mb=1000,
        log_level="DEBUG"
    )

    config_dict = config.to_dict()
    assert config_dict["default_output_format"] == "yaml"
    assert config_dict["max_file_size_mb"] == 1000
    assert config_dict["log_level"] == "DEBUG"

    # Test round-trip
    restored_config = ApplicationConfig.from_dict(config_dict)
    assert restored_config.default_output_format == "yaml"
    assert restored_config.max_file_size_mb == 1000
    assert restored_config.log_level == "DEBUG"


def test_validation_config_defaults():
    """Test ValidationConfig default values."""
    config = ValidationConfig()

    assert config.min_wall_thickness_mm == 0.8
    assert config.min_feature_size_mm == 0.4
    assert config.support_overhang_angle_deg == 60.0
    assert config.enable_wall_thickness_check is True
    assert config.parallel_processing is False


def test_validation_config_serialization():
    """Test ValidationConfig serialization."""
    config = ValidationConfig(
        min_wall_thickness_mm=1.0,
        support_overhang_angle_deg=45.0,
        parallel_processing=True
    )

    config_dict = config.to_dict()
    assert config_dict["min_wall_thickness_mm"] == 1.0
    assert config_dict["support_overhang_angle_deg"] == 45.0
    assert config_dict["parallel_processing"] is True

    # Test round-trip
    restored_config = ValidationConfig.from_dict(config_dict)
    assert restored_config.min_wall_thickness_mm == 1.0
    assert restored_config.support_overhang_angle_deg == 45.0
    assert restored_config.parallel_processing is True


def test_printer_profile_creation():
    """Test PrinterProfile creation and serialization."""
    profile = PrinterProfile(
        name="Test Printer",
        manufacturer="Test Corp",
        model="Test Model",
        build_volume_x=200.0,
        build_volume_y=200.0,
        build_volume_z=180.0,
        nozzle_diameter=0.4,
        max_nozzle_temp=250,
        heated_bed=True,
        max_bed_temp=80,
        enclosed=False
    )

    assert profile.name == "Test Printer"
    assert profile.build_volume_x == 200.0
    assert profile.heated_bed is True
    assert profile.enclosed is False

    # Test serialization
    profile_dict = profile.to_dict()
    assert profile_dict["name"] == "Test Printer"
    assert profile_dict["build_volume_x"] == 200.0

    # Test round-trip
    restored_profile = PrinterProfile.from_dict(profile_dict)
    assert restored_profile.name == "Test Printer"
    assert restored_profile.build_volume_x == 200.0


def test_config_creation():
    """Test Config creation and manipulation."""
    config = Config()

    assert isinstance(config.application, ApplicationConfig)
    assert isinstance(config.validation, ValidationConfig)
    assert isinstance(config.printer_profiles, dict)
    assert config.active_printer is None

    # Test adding printer profile
    profile = PrinterProfile(
        name="Test Printer",
        manufacturer="Test Corp",
        model="Test Model",
        build_volume_x=200.0,
        build_volume_y=200.0,
        build_volume_z=180.0
    )
    config.printer_profiles["test_printer"] = profile
    config.active_printer = "test_printer"

    active = config.get_active_printer()
    assert active is not None
    assert active.name == "Test Printer"


def test_config_serialization():
    """Test Config serialization."""
    config = Config()
    config.application.log_level = "DEBUG"
    config.validation.min_wall_thickness_mm = 1.2

    profile = PrinterProfile(
        name="Test Printer",
        manufacturer="Test Corp",
        model="Test Model",
        build_volume_x=200.0,
        build_volume_y=200.0,
        build_volume_z=180.0
    )
    config.printer_profiles["test"] = profile
    config.active_printer = "test"

    # Test to_dict
    config_dict = config.to_dict()
    assert config_dict["application"]["log_level"] == "DEBUG"
    assert config_dict["validation"]["min_wall_thickness_mm"] == 1.2
    assert "test" in config_dict["printer_profiles"]
    assert config_dict["active_printer"] == "test"

    # Test round-trip
    restored_config = Config.from_dict(config_dict)
    assert restored_config.application.log_level == "DEBUG"
    assert restored_config.validation.min_wall_thickness_mm == 1.2
    assert "test" in restored_config.printer_profiles
    assert restored_config.active_printer == "test"


def test_config_active_printer_management():
    """Test active printer management."""
    config = Config()

    # Test with no printers
    assert config.get_active_printer() is None

    # Add printer
    profile = PrinterProfile(
        name="Printer 1",
        manufacturer="Test Corp",
        model="Model 1",
        build_volume_x=200.0,
        build_volume_y=200.0,
        build_volume_z=180.0
    )
    config.printer_profiles["printer1"] = profile

    # Set active printer
    config.set_active_printer("printer1")
    assert config.active_printer == "printer1"
    assert config.get_active_printer() == profile

    # Test invalid printer
    with pytest.raises(ValueError):
        config.set_active_printer("nonexistent")


def test_config_manager_initialization(temp_config_dir):
    """Test ConfigManager initialization."""
    manager = ConfigManager(temp_config_dir)
    assert manager.config_dir == temp_config_dir
    assert manager.config_file == temp_config_dir / "config.yaml"


def test_config_manager_create_default_config(temp_config_dir):
    """Test default config creation."""
    manager = ConfigManager(temp_config_dir)
    config = manager._create_default_config()

    assert isinstance(config, Config)
    assert len(config.printer_profiles) > 0
    assert "prusa_i3_mk3" in config.printer_profiles
    assert "ender_3" in config.printer_profiles
    assert config.active_printer is not None


def test_config_manager_load_save(temp_config_dir):
    """Test config loading and saving."""
    manager = ConfigManager(temp_config_dir)

    # Load config (should create default)
    config = manager.load()
    assert isinstance(config, Config)
    assert manager.config_file.exists()

    # Modify config
    config.application.log_level = "DEBUG"
    config.validation.min_wall_thickness_mm = 1.5

    # Save modified config
    manager.save(config)

    # Create new manager and load
    manager2 = ConfigManager(temp_config_dir)
    config2 = manager2.load()

    assert config2.application.log_level == "DEBUG"
    assert config2.validation.min_wall_thickness_mm == 1.5


def test_config_manager_add_remove_printer(temp_config_dir):
    """Test adding and removing printer profiles."""
    manager = ConfigManager(temp_config_dir)

    # Add new printer profile
    new_profile = PrinterProfile(
        name="New Printer",
        manufacturer="New Corp",
        model="New Model",
        build_volume_x=300.0,
        build_volume_y=300.0,
        build_volume_z=400.0
    )

    manager.add_printer_profile(new_profile)

    # Verify it was added
    profiles = manager.get_printer_profiles()
    assert "new_printer" in profiles
    assert profiles["new_printer"].name == "New Printer"

    # Remove printer profile
    manager.remove_printer_profile("new_printer")

    # Verify it was removed
    profiles = manager.get_printer_profiles()
    assert "new_printer" not in profiles


def test_config_manager_update_validation(temp_config_dir):
    """Test updating validation configuration."""
    manager = ConfigManager(temp_config_dir)

    # Update validation parameters
    manager.update_validation_config(
        min_wall_thickness_mm=1.2,
        support_overhang_angle_deg=45.0
    )

    # Verify changes
    config = manager.load()
    assert config.validation.min_wall_thickness_mm == 1.2
    assert config.validation.support_overhang_angle_deg == 45.0

    # Test invalid parameter
    with pytest.raises(ValueError):
        manager.update_validation_config(invalid_parameter=123)


def test_config_manager_reset_to_defaults(temp_config_dir):
    """Test resetting configuration to defaults."""
    manager = ConfigManager(temp_config_dir)

    # Load and modify config
    config = manager.load()
    config.application.log_level = "DEBUG"
    manager.save(config)

    # Reset to defaults
    manager.reset_to_defaults()

    # Verify reset
    config = manager.load()
    assert config.application.log_level == "INFO"  # Default value


def test_config_manager_export_import(temp_config_dir):
    """Test config export and import."""
    manager = ConfigManager(temp_config_dir)

    # Load and modify config
    config = manager.load()
    config.application.log_level = "DEBUG"
    manager.save(config)

    # Export to YAML
    yaml_file = temp_config_dir / "exported.yaml"
    manager.export_config(yaml_file, format="yaml")
    assert yaml_file.exists()

    # Export to JSON
    json_file = temp_config_dir / "exported.json"
    manager.export_config(json_file, format="json")
    assert json_file.exists()

    # Reset config
    manager.reset_to_defaults()
    original_log_level = manager.load().application.log_level

    # Import from YAML
    manager.import_config(yaml_file)
    imported_config = manager.load()
    assert imported_config.application.log_level == "DEBUG"

    # Test invalid format
    with pytest.raises(ValueError):
        manager.export_config(temp_config_dir / "test.xyz", format="invalid")


def test_config_manager_import_nonexistent(temp_config_dir):
    """Test importing from non-existent file."""
    manager = ConfigManager(temp_config_dir)

    with pytest.raises(FileNotFoundError):
        manager.import_config(Path("nonexistent.yaml"))


def test_global_config_functions():
    """Test global config convenience functions."""
    # These should not raise exceptions
    config_manager = get_config_manager()
    assert isinstance(config_manager, ConfigManager)

    config = get_config()
    assert isinstance(config, Config)


def test_config_manager_corrupted_file(temp_config_dir):
    """Test handling of corrupted config file."""
    manager = ConfigManager(temp_config_dir)

    # Create corrupted config file
    with open(manager.config_file, 'w') as f:
        f.write("invalid: yaml: content:")

    # Should fallback to default config
    config = manager.load()
    assert isinstance(config, Config)
    assert len(config.printer_profiles) > 0  # Should have defaults


def test_config_file_permissions(temp_config_dir):
    """Test config file creation and permissions."""
    manager = ConfigManager(temp_config_dir)

    # Load config (creates file)
    config = manager.load()

    # File should exist and be readable
    assert manager.config_file.exists()
    assert manager.config_file.is_file()

    # Should be able to read the file
    with open(manager.config_file) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)