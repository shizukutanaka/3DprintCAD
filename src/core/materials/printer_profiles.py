"""Comprehensive printer profiles for production 3D printing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from pathlib import Path


class PrinterTechnology(Enum):
    """3D printing technology types."""
    FDM = "fdm"  # Fused Deposition Modeling
    SLA = "sla"  # Stereolithography
    SLS = "sls"  # Selective Laser Sintering
    DLP = "dlp"  # Digital Light Processing
    MJF = "mjf"  # Multi Jet Fusion
    BINDER_JET = "binder_jet"
    METAL_FDM = "metal_fdm"
    DMLS = "dmls"  # Direct Metal Laser Sintering


class PrinterBrand(Enum):
    """Common 3D printer manufacturers."""
    PRUSA = "prusa"
    ULTIMAKER = "ultimaker"
    MAKERBOT = "makerbot"
    CREALITY = "creality"
    ANYCUBIC = "anycubic"
    FORMLABS = "formlabs"
    MARKFORGED = "markforged"
    STRATASYS = "stratasys"
    HP = "hp"
    EOS = "eos"
    RAISE3D = "raise3d"
    BAMBU_LAB = "bambu_lab"
    FLASHFORGE = "flashforge"
    QIDI = "qidi"
    CUSTOM = "custom"


@dataclass
class BuildVolume:
    """Build volume specifications."""
    x_mm: float
    y_mm: float
    z_mm: float
    shape: str = "rectangular"  # rectangular, cylindrical, delta
    heated_chamber: bool = False
    max_chamber_temp_c: Optional[float] = None

    @property
    def volume_cm3(self) -> float:
        """Calculate build volume in cm³."""
        if self.shape == "rectangular":
            return (self.x_mm * self.y_mm * self.z_mm) / 1000
        elif self.shape == "cylindrical":
            # For cylindrical, x_mm is diameter
            radius = self.x_mm / 2
            return (3.14159 * radius * radius * self.z_mm) / 1000
        else:
            # Delta approximation
            return (self.x_mm * self.y_mm * self.z_mm * 0.7) / 1000


@dataclass
class ExtruderConfig:
    """Extruder configuration."""
    nozzle_diameter_mm: float = 0.4
    min_nozzle_temp_c: float = 170
    max_nozzle_temp_c: float = 300
    direct_drive: bool = True
    bowden_tube_length_mm: Optional[float] = None
    dual_extruder: bool = False
    mixing_extruder: bool = False
    all_metal_hotend: bool = False
    max_flow_rate_mm3_s: float = 15.0
    available_nozzles_mm: List[float] = field(default_factory=lambda: [0.2, 0.4, 0.6, 0.8])


@dataclass
class BedConfig:
    """Print bed configuration."""
    heated: bool = True
    min_bed_temp_c: float = 0
    max_bed_temp_c: float = 110
    auto_leveling: bool = True
    leveling_type: str = "mesh"  # manual, mesh, 3-point, 5-point
    surface_type: str = "pei"  # pei, glass, magnetic, textured
    removable: bool = True


@dataclass
class MotionSystem:
    """Motion system specifications."""
    kinematics: str = "cartesian"  # cartesian, corexy, delta, scara
    max_print_speed_mm_s: float = 200
    max_travel_speed_mm_s: float = 300
    max_acceleration_mm_s2: float = 3000
    max_jerk_mm_s: float = 10
    z_hop_height_mm: float = 0.2
    silent_steppers: bool = True
    closed_loop: bool = False


@dataclass
class QualitySettings:
    """Print quality presets."""
    name: str
    layer_height_mm: float
    initial_layer_height_mm: float
    line_width_mm: float
    top_layers: int
    bottom_layers: int
    wall_count: int
    infill_density_percent: float
    infill_pattern: str
    print_speed_mm_s: float
    retraction_distance_mm: float
    retraction_speed_mm_s: float


@dataclass
class CalibrationData:
    """Printer calibration data."""
    e_steps_per_mm: float = 415
    x_steps_per_mm: float = 100
    y_steps_per_mm: float = 100
    z_steps_per_mm: float = 400
    pid_hotend: Dict[str, float] = field(default_factory=lambda: {"p": 22.2, "i": 1.08, "d": 114})
    pid_bed: Dict[str, float] = field(default_factory=lambda: {"p": 10.0, "i": 0.023, "d": 305})
    z_offset: float = 0.0
    linear_advance_k: float = 0.0
    pressure_advance: float = 0.0
    input_shaper_freq_x: Optional[float] = None
    input_shaper_freq_y: Optional[float] = None


@dataclass
class PrinterProfile:
    """Comprehensive 3D printer profile."""
    # Basic info
    brand: PrinterBrand
    model: str
    technology: PrinterTechnology
    firmware: str = "Marlin"

    # Hardware specs
    build_volume: BuildVolume
    extruder: ExtruderConfig
    bed: BedConfig
    motion: MotionSystem

    # Features
    features: Dict[str, bool] = field(default_factory=dict)

    # Quality presets
    quality_presets: List[QualitySettings] = field(default_factory=list)

    # Calibration
    calibration: CalibrationData = field(default_factory=CalibrationData)

    # Material compatibility
    compatible_materials: List[str] = field(default_factory=list)

    # Maintenance
    maintenance_schedule: Dict[str, int] = field(default_factory=dict)

    # Custom settings
    custom_start_gcode: str = ""
    custom_end_gcode: str = ""

    # Validation
    validated: bool = False
    validation_date: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "brand": self.brand.value,
            "model": self.model,
            "technology": self.technology.value,
            "firmware": self.firmware,
            "build_volume": {
                "x_mm": self.build_volume.x_mm,
                "y_mm": self.build_volume.y_mm,
                "z_mm": self.build_volume.z_mm,
                "shape": self.build_volume.shape,
                "heated_chamber": self.build_volume.heated_chamber,
                "max_chamber_temp_c": self.build_volume.max_chamber_temp_c
            },
            "extruder": {
                "nozzle_diameter_mm": self.extruder.nozzle_diameter_mm,
                "min_nozzle_temp_c": self.extruder.min_nozzle_temp_c,
                "max_nozzle_temp_c": self.extruder.max_nozzle_temp_c,
                "direct_drive": self.extruder.direct_drive,
                "dual_extruder": self.extruder.dual_extruder,
                "all_metal_hotend": self.extruder.all_metal_hotend,
                "max_flow_rate_mm3_s": self.extruder.max_flow_rate_mm3_s
            },
            "bed": {
                "heated": self.bed.heated,
                "max_bed_temp_c": self.bed.max_bed_temp_c,
                "auto_leveling": self.bed.auto_leveling,
                "surface_type": self.bed.surface_type
            },
            "motion": {
                "kinematics": self.motion.kinematics,
                "max_print_speed_mm_s": self.motion.max_print_speed_mm_s,
                "max_acceleration_mm_s2": self.motion.max_acceleration_mm_s2
            },
            "features": self.features,
            "quality_presets": [
                {
                    "name": q.name,
                    "layer_height_mm": q.layer_height_mm,
                    "infill_density_percent": q.infill_density_percent,
                    "print_speed_mm_s": q.print_speed_mm_s
                } for q in self.quality_presets
            ],
            "compatible_materials": self.compatible_materials,
            "validated": self.validated,
            "notes": self.notes
        }


class PrinterDatabase:
    """Database of printer profiles."""

    def __init__(self):
        self.profiles: Dict[str, PrinterProfile] = {}
        self._load_default_profiles()

    def _load_default_profiles(self):
        """Load default printer profiles."""

        # Prusa MK3S+
        self.profiles["prusa_mk3s"] = PrinterProfile(
            brand=PrinterBrand.PRUSA,
            model="i3 MK3S+",
            technology=PrinterTechnology.FDM,
            firmware="Prusa-Firmware",
            build_volume=BuildVolume(250, 210, 210),
            extruder=ExtruderConfig(
                nozzle_diameter_mm=0.4,
                max_nozzle_temp_c=300,
                direct_drive=True,
                all_metal_hotend=True,
                max_flow_rate_mm3_s=15
            ),
            bed=BedConfig(
                heated=True,
                max_bed_temp_c=120,
                auto_leveling=True,
                leveling_type="mesh",
                surface_type="pei"
            ),
            motion=MotionSystem(
                kinematics="cartesian",
                max_print_speed_mm_s=200,
                max_travel_speed_mm_s=250,
                max_acceleration_mm_s2=1000,
                silent_steppers=True
            ),
            features={
                "filament_sensor": True,
                "power_recovery": True,
                "silent_mode": True,
                "mesh_bed_leveling": True,
                "crash_detection": True
            },
            quality_presets=[
                QualitySettings(
                    name="Draft",
                    layer_height_mm=0.3,
                    initial_layer_height_mm=0.2,
                    line_width_mm=0.45,
                    top_layers=3,
                    bottom_layers=3,
                    wall_count=2,
                    infill_density_percent=20,
                    infill_pattern="gyroid",
                    print_speed_mm_s=80,
                    retraction_distance_mm=0.8,
                    retraction_speed_mm_s=35
                ),
                QualitySettings(
                    name="Quality",
                    layer_height_mm=0.15,
                    initial_layer_height_mm=0.2,
                    line_width_mm=0.45,
                    top_layers=5,
                    bottom_layers=4,
                    wall_count=3,
                    infill_density_percent=20,
                    infill_pattern="gyroid",
                    print_speed_mm_s=60,
                    retraction_distance_mm=0.8,
                    retraction_speed_mm_s=35
                )
            ],
            compatible_materials=["PLA", "PETG", "ASA", "ABS", "PC", "TPU", "Nylon"],
            maintenance_schedule={
                "lubricate_rods_hours": 200,
                "check_belt_tension_hours": 500,
                "replace_nozzle_kg": 5,
                "clean_extruder_gears_kg": 2
            },
            validated=True,
            validation_date="2024-01-15"
        )

        # Bambu Lab X1 Carbon
        self.profiles["bambu_x1c"] = PrinterProfile(
            brand=PrinterBrand.BAMBU_LAB,
            model="X1 Carbon",
            technology=PrinterTechnology.FDM,
            firmware="Bambu Studio",
            build_volume=BuildVolume(256, 256, 256, heated_chamber=True, max_chamber_temp_c=60),
            extruder=ExtruderConfig(
                nozzle_diameter_mm=0.4,
                max_nozzle_temp_c=300,
                direct_drive=True,
                all_metal_hotend=True,
                max_flow_rate_mm3_s=28
            ),
            bed=BedConfig(
                heated=True,
                max_bed_temp_c=110,
                auto_leveling=True,
                leveling_type="mesh",
                surface_type="textured"
            ),
            motion=MotionSystem(
                kinematics="corexy",
                max_print_speed_mm_s=500,
                max_travel_speed_mm_s=500,
                max_acceleration_mm_s2=20000,
                closed_loop=True
            ),
            features={
                "ai_detection": True,
                "auto_calibration": True,
                "lidar_scanning": True,
                "ams_support": True,
                "camera_monitoring": True,
                "vibration_compensation": True,
                "flow_calibration": True
            },
            quality_presets=[
                QualitySettings(
                    name="Speed",
                    layer_height_mm=0.24,
                    initial_layer_height_mm=0.2,
                    line_width_mm=0.42,
                    top_layers=3,
                    bottom_layers=3,
                    wall_count=2,
                    infill_density_percent=15,
                    infill_pattern="gyroid",
                    print_speed_mm_s=300,
                    retraction_distance_mm=0.4,
                    retraction_speed_mm_s=30
                ),
                QualitySettings(
                    name="Standard",
                    layer_height_mm=0.16,
                    initial_layer_height_mm=0.2,
                    line_width_mm=0.42,
                    top_layers=4,
                    bottom_layers=3,
                    wall_count=3,
                    infill_density_percent=15,
                    infill_pattern="gyroid",
                    print_speed_mm_s=200,
                    retraction_distance_mm=0.4,
                    retraction_speed_mm_s=30
                )
            ],
            compatible_materials=["PLA", "PETG", "TPU", "ABS", "ASA", "PC", "PA", "PVA", "HIPS"],
            validated=True,
            validation_date="2024-02-20"
        )

        # Creality Ender 3 V3 SE
        self.profiles["ender3_v3se"] = PrinterProfile(
            brand=PrinterBrand.CREALITY,
            model="Ender 3 V3 SE",
            technology=PrinterTechnology.FDM,
            firmware="Marlin",
            build_volume=BuildVolume(220, 220, 250),
            extruder=ExtruderConfig(
                nozzle_diameter_mm=0.4,
                max_nozzle_temp_c=260,
                direct_drive=False,
                bowden_tube_length_mm=400,
                all_metal_hotend=False
            ),
            bed=BedConfig(
                heated=True,
                max_bed_temp_c=100,
                auto_leveling=True,
                leveling_type="mesh",
                surface_type="magnetic"
            ),
            motion=MotionSystem(
                kinematics="cartesian",
                max_print_speed_mm_s=180,
                max_travel_speed_mm_s=180,
                max_acceleration_mm_s2=2500
            ),
            features={
                "auto_leveling": True,
                "dual_z_motors": False,
                "filament_sensor": False,
                "power_recovery": True
            },
            compatible_materials=["PLA", "PETG", "TPU"],
            validated=True
        )

        # Formlabs Form 3+
        self.profiles["formlabs_form3"] = PrinterProfile(
            brand=PrinterBrand.FORMLABS,
            model="Form 3+",
            technology=PrinterTechnology.SLA,
            firmware="PreForm",
            build_volume=BuildVolume(145, 145, 185, shape="rectangular"),
            extruder=ExtruderConfig(  # Resin settings
                nozzle_diameter_mm=0.085,  # Laser spot size
                min_nozzle_temp_c=20,  # Min resin temp
                max_nozzle_temp_c=35,  # Max resin temp
                max_flow_rate_mm3_s=100  # Resin flow
            ),
            bed=BedConfig(
                heated=True,
                max_bed_temp_c=35,
                auto_leveling=True,
                surface_type="tank"
            ),
            motion=MotionSystem(
                kinematics="cartesian",
                max_print_speed_mm_s=100,
                max_travel_speed_mm_s=150
            ),
            features={
                "low_force_stereolithography": True,
                "automatic_resin_dispensing": True,
                "heated_resin_tank": True,
                "optical_sensor": True,
                "cartridge_system": True
            },
            compatible_materials=["Standard", "Tough", "Durable", "Flexible", "Castable", "Dental"],
            validated=True
        )

    def add_profile(self, profile_id: str, profile: PrinterProfile):
        """Add a printer profile."""
        self.profiles[profile_id] = profile

    def get_profile(self, profile_id: str) -> Optional[PrinterProfile]:
        """Get a printer profile by ID."""
        return self.profiles.get(profile_id)

    def get_profiles_by_technology(self, technology: PrinterTechnology) -> List[PrinterProfile]:
        """Get all profiles for a specific technology."""
        return [p for p in self.profiles.values() if p.technology == technology]

    def get_profiles_by_material(self, material: str) -> List[PrinterProfile]:
        """Get profiles compatible with a specific material."""
        return [p for p in self.profiles.values() if material in p.compatible_materials]

    def get_profiles_by_build_volume(self, min_volume_cm3: float) -> List[PrinterProfile]:
        """Get profiles with minimum build volume."""
        return [p for p in self.profiles.values()
                if p.build_volume.volume_cm3 >= min_volume_cm3]

    def export_profile(self, profile_id: str, filepath: Path):
        """Export a profile to JSON."""
        profile = self.get_profile(profile_id)
        if profile:
            with open(filepath, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2)

    def import_profile(self, filepath: Path) -> Optional[str]:
        """Import a profile from JSON."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Create profile from data
            profile = self._create_profile_from_dict(data)
            profile_id = f"{data['brand']}_{data['model'].lower().replace(' ', '_')}"
            self.add_profile(profile_id, profile)
            return profile_id
        except Exception as e:
            print(f"Error importing profile: {e}")
            return None

    def _create_profile_from_dict(self, data: Dict[str, Any]) -> PrinterProfile:
        """Create a PrinterProfile from dictionary data."""
        return PrinterProfile(
            brand=PrinterBrand(data["brand"]),
            model=data["model"],
            technology=PrinterTechnology(data["technology"]),
            firmware=data.get("firmware", "Unknown"),
            build_volume=BuildVolume(**data["build_volume"]),
            extruder=ExtruderConfig(**data["extruder"]),
            bed=BedConfig(**data["bed"]),
            motion=MotionSystem(**data["motion"]),
            features=data.get("features", {}),
            compatible_materials=data.get("compatible_materials", []),
            validated=data.get("validated", False),
            notes=data.get("notes", "")
        )

    def recommend_printer(self, material: str, min_quality: str = "draft",
                          min_volume_cm3: float = 0) -> List[str]:
        """Recommend printers based on requirements."""
        recommendations = []

        for profile_id, profile in self.profiles.items():
            # Check material compatibility
            if material not in profile.compatible_materials:
                continue

            # Check build volume
            if profile.build_volume.volume_cm3 < min_volume_cm3:
                continue

            # Check quality capability
            has_quality = any(q.name.lower() == min_quality.lower()
                            for q in profile.quality_presets)
            if not has_quality and profile.quality_presets:
                continue

            recommendations.append(profile_id)

        return recommendations


# Global printer database instance
printer_database = PrinterDatabase()