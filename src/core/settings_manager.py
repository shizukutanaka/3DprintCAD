"""Comprehensive print settings and configuration management."""

import json
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import configparser
from enum import Enum

class PrinterType(Enum):
    """3D printer categories."""
    FDM = "FDM"
    RESIN = "Resin"
    POWDER = "Powder"
    HYBRID = "Hybrid"

class NozzleMaterial(Enum):
    """Nozzle material types."""
    BRASS = "Brass"
    STEEL = "Steel"
    HARDENED_STEEL = "Hardened Steel"
    RUBY = "Ruby"
    TUNGSTEN = "Tungsten"

@dataclass
class PrinterProfile:
    """Comprehensive printer configuration."""
    name: str
    manufacturer: str
    model: str
    type: PrinterType

    # Build volume
    build_volume_x: float  # mm
    build_volume_y: float  # mm
    build_volume_z: float  # mm

    # Extruder configuration
    extruder_count: int = 1
    nozzle_diameter: float = 0.4  # mm
    nozzle_material: NozzleMaterial = NozzleMaterial.BRASS
    max_temp_nozzle: float = 300.0  # °C
    max_temp_bed: float = 120.0  # °C
    max_temp_chamber: Optional[float] = None  # °C

    # Movement capabilities
    max_speed_x: float = 200.0  # mm/s
    max_speed_y: float = 200.0  # mm/s
    max_speed_z: float = 20.0  # mm/s
    max_acceleration: float = 3000.0  # mm/s²
    max_jerk: float = 10.0  # mm/s

    # Features
    has_heated_bed: bool = True
    has_heated_chamber: bool = False
    has_auto_leveling: bool = False
    has_filament_sensor: bool = False
    has_power_recovery: bool = False
    has_dual_z: bool = False

    # Firmware and connectivity
    firmware: str = "Marlin"
    connectivity: List[str] = None  # USB, WiFi, Ethernet, SD
    supports_octoprint: bool = True

    # Bed configuration
    bed_shape: str = "rectangular"  # rectangular, circular
    bed_material: str = "glass"  # glass, PEI, BuildTak
    bed_center_x: float = 0
    bed_center_y: float = 0

    # Advanced features
    supports_multi_material: bool = False
    supports_mmu: bool = False
    linear_advance_factor: float = 0.0
    pressure_advance: float = 0.0

    def __post_init__(self):
        if self.connectivity is None:
            self.connectivity = ["USB", "SD"]

@dataclass
class QualityProfile:
    """Print quality configuration."""
    name: str
    description: str

    # Layer settings
    layer_height: float
    first_layer_height: float
    adaptive_layers: bool = False

    # Print speeds
    print_speed: float
    infill_speed: float
    perimeter_speed: float
    small_perimeter_speed: float
    external_perimeter_speed: float
    bridge_speed: float
    gap_fill_speed: float
    travel_speed: float
    first_layer_speed: float

    # Acceleration
    default_acceleration: float = 1000.0
    perimeter_acceleration: float = 800.0
    infill_acceleration: float = 1000.0
    bridge_acceleration: float = 300.0
    first_layer_acceleration: float = 500.0

    # Precision
    resolution: float = 0.1  # mm
    curve_smoothing: float = 0.1

    # Quality vs speed balance
    quality_score: float = 0.5  # 0=fast, 1=quality
    estimated_time_factor: float = 1.0

@dataclass
class SlicingSettings:
    """Comprehensive slicing configuration."""

    # Basic settings
    layer_height: float = 0.2
    first_layer_height: float = 0.3
    nozzle_diameter: float = 0.4
    filament_diameter: float = 1.75

    # Walls and surfaces
    perimeters: int = 3
    solid_layers: int = 4
    fill_density: float = 20.0  # %
    fill_pattern: str = "cubic"
    top_fill_pattern: str = "rectilinear"
    bottom_fill_pattern: str = "rectilinear"

    # Supports
    support_material: bool = False
    support_threshold: float = 45.0  # degrees
    support_pattern: str = "rectilinear"
    support_density: float = 15.0  # %
    support_interface: bool = True
    support_interface_layers: int = 3
    support_interface_spacing: float = 0.2

    # Speed settings
    perimeter_speed: float = 50.0
    small_perimeter_speed: float = 30.0
    external_perimeter_speed: float = 40.0
    infill_speed: float = 80.0
    solid_infill_speed: float = 60.0
    top_solid_infill_speed: float = 40.0
    bridge_speed: float = 30.0
    gap_fill_speed: float = 40.0
    travel_speed: float = 150.0
    first_layer_speed: float = 20.0

    # Temperature
    nozzle_temperature: int = 210
    bed_temperature: int = 60
    chamber_temperature: Optional[int] = None

    # Cooling
    fan_speed: float = 100.0  # %
    bridge_fan_speed: float = 100.0
    disable_fan_first_layers: int = 1
    fan_below_layer_time: float = 60.0
    slowdown_below_layer_time: float = 15.0
    min_print_speed: float = 10.0

    # Retraction
    retract_length: float = 5.0
    retract_speed: float = 45.0
    retract_restart_extra: float = 0.0
    retract_before_travel: float = 2.0
    retract_lift: float = 0.0
    retract_lift_above: float = 0.0
    retract_lift_below: float = 0.0

    # Skirt and brim
    skirts: int = 1
    skirt_distance: float = 6.0
    skirt_height: int = 1
    brim_width: float = 0.0

    # Sequential printing
    complete_objects: bool = False
    extruder_clearance_radius: float = 20.0
    extruder_clearance_height: float = 20.0

    # Output options
    gcode_comments: bool = True
    gcode_label_objects: bool = False
    output_filename_format: str = "[input_filename_base].gcode"

    # Advanced
    avoid_crossing_perimeters: bool = False
    thin_walls: bool = True
    overhangs: bool = True
    spiral_vase: bool = False
    only_retract_when_crossing_perimeters: bool = True
    infill_only_where_needed: bool = False
    infill_every_layers: int = 1
    fill_angle: float = 45.0
    bridge_angle: float = 0.0
    solid_infill_below_area: float = 70.0
    only_one_perimeter_top: bool = False
    extra_perimeters: bool = True
    gap_fill_enabled: bool = True

    # Multi-material
    interface_shells: bool = False
    infill_first: bool = False
    wipe_tower: bool = False
    wipe_tower_x: float = 180.0
    wipe_tower_y: float = 140.0
    wipe_tower_width: float = 60.0
    wipe_tower_rotation_angle: float = 0.0

class SettingsManager:
    """Comprehensive settings and configuration management."""

    def __init__(self, settings_dir: str = "settings"):
        self.settings_dir = Path(settings_dir)
        self.settings_dir.mkdir(exist_ok=True)

        self.printers_file = self.settings_dir / "printers.json"
        self.qualities_file = self.settings_dir / "qualities.json"
        self.slicing_file = self.settings_dir / "slicing.json"
        self.preferences_file = self.settings_dir / "preferences.ini"

        self._init_default_settings()

    def _init_default_settings(self):
        """Initialize default settings if not present."""

        # Default printers
        if not self.printers_file.exists():
            default_printers = [
                PrinterProfile(
                    name="Prusa i3 MK3S+",
                    manufacturer="Prusa Research",
                    model="i3 MK3S+",
                    type=PrinterType.FDM,
                    build_volume_x=250,
                    build_volume_y=210,
                    build_volume_z=210,
                    nozzle_diameter=0.4,
                    max_temp_nozzle=300,
                    max_temp_bed=120,
                    has_auto_leveling=True,
                    has_filament_sensor=True,
                    has_power_recovery=True,
                    firmware="Prusa",
                    connectivity=["USB", "Ethernet", "SD"],
                    supports_octoprint=True
                ),
                PrinterProfile(
                    name="Ender 3 V2",
                    manufacturer="Creality",
                    model="Ender 3 V2",
                    type=PrinterType.FDM,
                    build_volume_x=220,
                    build_volume_y=220,
                    build_volume_z=250,
                    nozzle_diameter=0.4,
                    max_temp_nozzle=260,
                    max_temp_bed=100,
                    has_auto_leveling=False,
                    firmware="Marlin",
                    connectivity=["USB", "SD"]
                ),
                PrinterProfile(
                    name="Bambu Lab X1 Carbon",
                    manufacturer="Bambu Lab",
                    model="X1 Carbon",
                    type=PrinterType.FDM,
                    build_volume_x=256,
                    build_volume_y=256,
                    build_volume_z=256,
                    nozzle_diameter=0.4,
                    max_temp_nozzle=300,
                    max_temp_bed=120,
                    max_temp_chamber=60,
                    has_heated_chamber=True,
                    has_auto_leveling=True,
                    has_filament_sensor=True,
                    has_power_recovery=True,
                    supports_multi_material=True,
                    supports_mmu=True,
                    firmware="Bambu",
                    connectivity=["WiFi", "USB", "SD"]
                ),
                PrinterProfile(
                    name="Ultimaker S3",
                    manufacturer="Ultimaker",
                    model="S3",
                    type=PrinterType.FDM,
                    build_volume_x=230,
                    build_volume_y=190,
                    build_volume_z=200,
                    extruder_count=2,
                    nozzle_diameter=0.4,
                    max_temp_nozzle=280,
                    max_temp_bed=100,
                    has_auto_leveling=True,
                    has_filament_sensor=True,
                    supports_multi_material=True,
                    firmware="UltiMaker",
                    connectivity=["WiFi", "Ethernet", "USB"]
                )
            ]
            self.save_printers(default_printers)

        # Default quality profiles
        if not self.qualities_file.exists():
            default_qualities = [
                QualityProfile(
                    name="Draft",
                    description="Fast printing with lower quality",
                    layer_height=0.3,
                    first_layer_height=0.3,
                    print_speed=80,
                    infill_speed=100,
                    perimeter_speed=60,
                    small_perimeter_speed=40,
                    external_perimeter_speed=50,
                    bridge_speed=40,
                    gap_fill_speed=50,
                    travel_speed=150,
                    first_layer_speed=20,
                    quality_score=0.2,
                    estimated_time_factor=0.7
                ),
                QualityProfile(
                    name="Standard",
                    description="Balanced quality and speed",
                    layer_height=0.2,
                    first_layer_height=0.3,
                    print_speed=50,
                    infill_speed=80,
                    perimeter_speed=45,
                    small_perimeter_speed=30,
                    external_perimeter_speed=40,
                    bridge_speed=30,
                    gap_fill_speed=40,
                    travel_speed=150,
                    first_layer_speed=20,
                    quality_score=0.5,
                    estimated_time_factor=1.0
                ),
                QualityProfile(
                    name="Fine",
                    description="High quality with detailed features",
                    layer_height=0.15,
                    first_layer_height=0.2,
                    print_speed=40,
                    infill_speed=60,
                    perimeter_speed=35,
                    small_perimeter_speed=25,
                    external_perimeter_speed=30,
                    bridge_speed=25,
                    gap_fill_speed=30,
                    travel_speed=150,
                    first_layer_speed=15,
                    quality_score=0.7,
                    estimated_time_factor=1.4
                ),
                QualityProfile(
                    name="Ultra Fine",
                    description="Maximum quality for detailed prints",
                    layer_height=0.1,
                    first_layer_height=0.15,
                    print_speed=30,
                    infill_speed=40,
                    perimeter_speed=25,
                    small_perimeter_speed=20,
                    external_perimeter_speed=22,
                    bridge_speed=20,
                    gap_fill_speed=25,
                    travel_speed=120,
                    first_layer_speed=10,
                    quality_score=0.9,
                    estimated_time_factor=2.0
                )
            ]
            self.save_qualities(default_qualities)

        # Default slicing settings
        if not self.slicing_file.exists():
            default_slicing = SlicingSettings()
            self.save_slicing_settings(default_slicing)

        # Default preferences
        if not self.preferences_file.exists():
            self._init_default_preferences()

    def _init_default_preferences(self):
        """Initialize default user preferences."""
        config = configparser.ConfigParser()

        config['UI'] = {
            'theme': 'dark',
            'language': 'en',
            'auto_save': 'true',
            'show_tooltips': 'true',
            'animation_speed': 'normal'
        }

        config['Workflow'] = {
            'auto_repair': 'true',
            'auto_orient': 'false',
            'auto_support': 'true',
            'auto_slice': 'false',
            'backup_gcode': 'true'
        }

        config['Performance'] = {
            'max_threads': '0',  # 0 = auto-detect
            'gpu_acceleration': 'true',
            'memory_limit_mb': '4096',
            'cache_size_mb': '512'
        }

        config['Quality'] = {
            'default_layer_height': '0.2',
            'default_infill': '20',
            'default_support_angle': '45',
            'preview_quality': 'medium'
        }

        config['Files'] = {
            'auto_import_settings': 'true',
            'remember_last_directory': 'true',
            'export_format': 'gcode',
            'backup_projects': 'true'
        }

        with open(self.preferences_file, 'w') as f:
            config.write(f)

    # Printer management
    def load_printers(self) -> List[PrinterProfile]:
        """Load printer profiles."""
        if not self.printers_file.exists():
            return []

        with open(self.printers_file, 'r') as f:
            data = json.load(f)

        printers = []
        for printer_data in data:
            # Convert string enums back to enum objects
            if 'type' in printer_data:
                printer_data['type'] = PrinterType(printer_data['type'])
            if 'nozzle_material' in printer_data:
                printer_data['nozzle_material'] = NozzleMaterial(printer_data['nozzle_material'])

            printers.append(PrinterProfile(**printer_data))

        return printers

    def save_printers(self, printers: List[PrinterProfile]):
        """Save printer profiles."""
        data = []
        for printer in printers:
            printer_dict = asdict(printer)
            # Convert enums to strings for JSON serialization
            if 'type' in printer_dict:
                printer_dict['type'] = printer_dict['type'].value
            if 'nozzle_material' in printer_dict:
                printer_dict['nozzle_material'] = printer_dict['nozzle_material'].value
            data.append(printer_dict)

        with open(self.printers_file, 'w') as f:
            json.dump(data, f, indent=2)

    def add_printer(self, printer: PrinterProfile):
        """Add new printer profile."""
        printers = self.load_printers()
        printers.append(printer)
        self.save_printers(printers)

    def get_printer(self, name: str) -> Optional[PrinterProfile]:
        """Get printer by name."""
        printers = self.load_printers()
        for printer in printers:
            if printer.name == name:
                return printer
        return None

    # Quality management
    def load_qualities(self) -> List[QualityProfile]:
        """Load quality profiles."""
        if not self.qualities_file.exists():
            return []

        with open(self.qualities_file, 'r') as f:
            data = json.load(f)

        return [QualityProfile(**quality_data) for quality_data in data]

    def save_qualities(self, qualities: List[QualityProfile]):
        """Save quality profiles."""
        data = [asdict(quality) for quality in qualities]
        with open(self.qualities_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_quality(self, name: str) -> Optional[QualityProfile]:
        """Get quality profile by name."""
        qualities = self.load_qualities()
        for quality in qualities:
            if quality.name == name:
                return quality
        return None

    # Slicing settings
    def load_slicing_settings(self) -> SlicingSettings:
        """Load slicing settings."""
        if not self.slicing_file.exists():
            return SlicingSettings()

        with open(self.slicing_file, 'r') as f:
            data = json.load(f)

        return SlicingSettings(**data)

    def save_slicing_settings(self, settings: SlicingSettings):
        """Save slicing settings."""
        with open(self.slicing_file, 'w') as f:
            json.dump(asdict(settings), f, indent=2)

    # Preferences
    def load_preferences(self) -> configparser.ConfigParser:
        """Load user preferences."""
        config = configparser.ConfigParser()
        if self.preferences_file.exists():
            config.read(self.preferences_file)
        return config

    def save_preferences(self, config: configparser.ConfigParser):
        """Save user preferences."""
        with open(self.preferences_file, 'w') as f:
            config.write(f)

    def get_preference(self, section: str, key: str, fallback: str = None) -> str:
        """Get specific preference value."""
        config = self.load_preferences()
        return config.get(section, key, fallback=fallback)

    def set_preference(self, section: str, key: str, value: str):
        """Set specific preference value."""
        config = self.load_preferences()
        if section not in config:
            config.add_section(section)
        config.set(section, key, value)
        self.save_preferences(config)

    # Profile generation
    def generate_profile_for_printer_material(self, printer_name: str, material_id: str, quality_name: str = "Standard") -> Dict:
        """Generate optimized settings for specific printer-material combination."""
        printer = self.get_printer(printer_name)
        quality = self.get_quality(quality_name)
        base_settings = self.load_slicing_settings()

        if not printer or not quality:
            return asdict(base_settings)

        # Optimize settings based on printer capabilities
        optimized = asdict(base_settings)

        # Update basic settings
        optimized['nozzle_diameter'] = printer.nozzle_diameter
        optimized['layer_height'] = quality.layer_height
        optimized['first_layer_height'] = quality.first_layer_height

        # Speed optimization
        optimized['perimeter_speed'] = quality.perimeter_speed
        optimized['infill_speed'] = quality.infill_speed
        optimized['travel_speed'] = quality.travel_speed
        optimized['first_layer_speed'] = quality.first_layer_speed

        # Printer-specific optimizations
        if printer.has_auto_leveling:
            optimized['first_layer_height'] = quality.layer_height  # Can use thinner first layer

        if printer.extruder_count > 1:
            optimized['wipe_tower'] = True
            optimized['interface_shells'] = True

        if printer.has_heated_chamber:
            optimized['fan_speed'] = max(0, optimized['fan_speed'] - 20)  # Reduce fan speed

        # Build volume constraints
        optimized['extruder_clearance_radius'] = min(20.0, printer.build_volume_x * 0.1)

        return optimized

    def export_settings(self, export_path: str):
        """Export all settings to a bundle."""
        bundle = {
            'printers': [asdict(p) for p in self.load_printers()],
            'qualities': [asdict(q) for q in self.load_qualities()],
            'slicing': asdict(self.load_slicing_settings()),
            'preferences': dict(self.load_preferences())
        }

        with open(export_path, 'w') as f:
            json.dump(bundle, f, indent=2)

    def import_settings(self, import_path: str):
        """Import settings from a bundle."""
        with open(import_path, 'r') as f:
            bundle = json.load(f)

        # Import printers
        if 'printers' in bundle:
            printers = []
            for printer_data in bundle['printers']:
                if 'type' in printer_data:
                    printer_data['type'] = PrinterType(printer_data['type'])
                if 'nozzle_material' in printer_data:
                    printer_data['nozzle_material'] = NozzleMaterial(printer_data['nozzle_material'])
                printers.append(PrinterProfile(**printer_data))
            self.save_printers(printers)

        # Import qualities
        if 'qualities' in bundle:
            qualities = [QualityProfile(**q) for q in bundle['qualities']]
            self.save_qualities(qualities)

        # Import slicing settings
        if 'slicing' in bundle:
            settings = SlicingSettings(**bundle['slicing'])
            self.save_slicing_settings(settings)

        # Import preferences
        if 'preferences' in bundle:
            config = configparser.ConfigParser()
            config.read_dict(bundle['preferences'])
            self.save_preferences(config)