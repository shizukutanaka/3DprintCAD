"""Material data models and structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Union
import json


class MaterialType(Enum):
    """Types of 3D printing materials."""
    THERMOPLASTIC = "thermoplastic"
    RESIN = "resin"
    METAL = "metal"
    CERAMIC = "ceramic"
    COMPOSITE = "composite"
    FLEXIBLE = "flexible"
    SUPPORT = "support"
    SOLUBLE = "soluble"
    BIODEGRADABLE = "biodegradable"  # New sustainable material type
    RECYCLED = "recycled"           # New sustainable material type


class PrinterType(Enum):
    """Types of 3D printers."""
    FDM = "fdm"  # Fused Deposition Modeling
    SLA = "sla"  # Stereolithography
    SLS = "sls"  # Selective Laser Sintering
    MSLA = "msla"  # Masked Stereolithography
    DLP = "dlp"  # Digital Light Processing
    POLYJET = "polyjet"
    MULTIJET = "multijet"


class MaterialCategory(Enum):
    """Material categories for organization."""
    STANDARD = "standard"
    ENGINEERING = "engineering"
    HIGH_PERFORMANCE = "high_performance"
    SPECIALTY = "specialty"
    EXPERIMENTAL = "experimental"
    FOOD_SAFE = "food_safe"
    MEDICAL = "medical"
    PROTOTYPE = "prototype"
    PRODUCTION = "production"
    SUSTAINABLE = "sustainable"  # New category for eco-friendly materials


@dataclass
class MaterialProperties:
    """Physical and chemical properties of a material."""
    # Thermal properties (°C)
    glass_transition_temp: Optional[float] = None
    melting_point: Optional[float] = None
    print_temperature_min: Optional[float] = None
    print_temperature_max: Optional[float] = None
    bed_temperature: Optional[float] = None

    # Mechanical properties
    tensile_strength_mpa: Optional[float] = None
    flexural_strength_mpa: Optional[float] = None
    impact_strength_j_m: Optional[float] = None
    elongation_at_break_percent: Optional[float] = None
    youngs_modulus_mpa: Optional[float] = None
    hardness_shore: Optional[str] = None

    # Physical properties
    density_g_cm3: Optional[float] = None
    shrinkage_percent: Optional[float] = None
    layer_adhesion: Optional[str] = None  # excellent, good, fair, poor

    # Print characteristics
    warping_tendency: Optional[str] = None  # low, medium, high
    support_required: Optional[bool] = None
    heated_bed_required: Optional[bool] = None
    enclosure_required: Optional[bool] = None

    # Chemical properties
    chemical_resistance: Optional[str] = None
    uv_resistance: Optional[str] = None
    food_safe: Optional[bool] = None
    biocompatible: Optional[bool] = None

    # Environmental
    biodegradable: Optional[bool] = None
    recyclable: Optional[bool] = None
    recycled_content_percent: Optional[float] = None
    carbon_footprint_kg_co2_per_kg: Optional[float] = None
    water_usage_liters_per_kg: Optional[float] = None
    toxicity_rating: Optional[str] = None  # low, medium, high
    renewable_source: Optional[bool] = None
    compostable: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class PrintSettings:
    """Recommended print settings for a material."""
    # Temperature settings
    nozzle_temperature: Optional[int] = None
    bed_temperature: Optional[int] = None
    chamber_temperature: Optional[int] = None

    # Speed settings (mm/s)
    print_speed: Optional[int] = None
    first_layer_speed: Optional[int] = None
    outer_wall_speed: Optional[int] = None
    inner_wall_speed: Optional[int] = None
    infill_speed: Optional[int] = None
    support_speed: Optional[int] = None

    # Layer settings
    layer_height_min: Optional[float] = None
    layer_height_max: Optional[float] = None
    layer_height_recommended: Optional[float] = None
    first_layer_height: Optional[float] = None

    # Extrusion settings
    flow_rate: Optional[float] = None  # Percentage
    linear_advance: Optional[float] = None
    retraction_distance: Optional[float] = None
    retraction_speed: Optional[int] = None

    # Support settings
    support_density: Optional[int] = None  # Percentage
    support_overhang_angle: Optional[int] = None
    support_interface_layers: Optional[int] = None

    # Infill settings
    infill_density_min: Optional[int] = None
    infill_density_max: Optional[int] = None
    infill_pattern: Optional[str] = None

    # Cooling
    fan_speed: Optional[int] = None  # Percentage
    fan_speed_first_layer: Optional[int] = None

    # Special settings
    adhesion_type: Optional[str] = None  # none, brim, raft, skirt
    z_hop: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class CompatibilityInfo:
    """Material compatibility information."""
    compatible_printers: Set[PrinterType] = field(default_factory=set)
    incompatible_printers: Set[PrinterType] = field(default_factory=set)
    compatible_nozzle_materials: Set[str] = field(default_factory=set)
    minimum_nozzle_diameter: Optional[float] = None  # mm
    maximum_nozzle_diameter: Optional[float] = None  # mm
    requires_hardened_nozzle: bool = False
    requires_all_metal_hotend: bool = False
    ventilation_required: bool = False
    safety_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "compatible_printers": [p.value for p in self.compatible_printers],
            "incompatible_printers": [p.value for p in self.incompatible_printers],
            "compatible_nozzle_materials": list(self.compatible_nozzle_materials),
            "minimum_nozzle_diameter": self.minimum_nozzle_diameter,
            "maximum_nozzle_diameter": self.maximum_nozzle_diameter,
            "requires_hardened_nozzle": self.requires_hardened_nozzle,
            "requires_all_metal_hotend": self.requires_all_metal_hotend,
            "ventilation_required": self.ventilation_required,
            "safety_notes": self.safety_notes
        }


@dataclass
class MaterialPreset:
    """Complete material preset definition."""
    # Basic identification
    id: str
    name: str
    manufacturer: Optional[str] = None
    product_line: Optional[str] = None
    color: Optional[str] = None

    # Classification
    material_type: MaterialType = MaterialType.THERMOPLASTIC
    category: MaterialCategory = MaterialCategory.STANDARD

    # Properties and settings
    properties: MaterialProperties = field(default_factory=MaterialProperties)
    print_settings: PrintSettings = field(default_factory=PrintSettings)
    compatibility: CompatibilityInfo = field(default_factory=CompatibilityInfo)

    # Cost information
    cost_per_kg: Optional[float] = None
    density_g_cm3: Optional[float] = None  # For volume to weight calculation

    # Metadata
    description: Optional[str] = None
    applications: List[str] = field(default_factory=list)
    advantages: List[str] = field(default_factory=list)
    disadvantages: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)

    # Quality and availability
    quality_rating: Optional[float] = None  # 1-5 stars
    availability: Optional[str] = None  # common, uncommon, rare, discontinued
    last_updated: Optional[str] = None

    # Validation
    validated: bool = False
    validation_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "product_line": self.product_line,
            "color": self.color,
            "material_type": self.material_type.value,
            "category": self.category.value,
            "properties": self.properties.to_dict(),
            "print_settings": self.print_settings.to_dict(),
            "compatibility": self.compatibility.to_dict(),
            "cost_per_kg": self.cost_per_kg,
            "density_g_cm3": self.density_g_cm3,
            "description": self.description,
            "applications": self.applications,
            "advantages": self.advantages,
            "disadvantages": self.disadvantages,
            "tips": self.tips,
            "quality_rating": self.quality_rating,
            "availability": self.availability,
            "last_updated": self.last_updated,
            "validated": self.validated,
            "validation_notes": self.validation_notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MaterialPreset:
        """Create MaterialPreset from dictionary."""
        # Handle enum conversions
        material_type = MaterialType(data.get("material_type", "thermoplastic"))
        category = MaterialCategory(data.get("category", "standard"))

        # Reconstruct properties
        properties_data = data.get("properties", {})
        properties = MaterialProperties(**properties_data)

        # Reconstruct print settings
        settings_data = data.get("print_settings", {})
        print_settings = PrintSettings(**settings_data)

        # Reconstruct compatibility
        compat_data = data.get("compatibility", {})
        compatibility = CompatibilityInfo(
            compatible_printers={PrinterType(p) for p in compat_data.get("compatible_printers", [])},
            incompatible_printers={PrinterType(p) for p in compat_data.get("incompatible_printers", [])},
            compatible_nozzle_materials=set(compat_data.get("compatible_nozzle_materials", [])),
            minimum_nozzle_diameter=compat_data.get("minimum_nozzle_diameter"),
            maximum_nozzle_diameter=compat_data.get("maximum_nozzle_diameter"),
            requires_hardened_nozzle=compat_data.get("requires_hardened_nozzle", False),
            requires_all_metal_hotend=compat_data.get("requires_all_metal_hotend", False),
            ventilation_required=compat_data.get("ventilation_required", False),
            safety_notes=compat_data.get("safety_notes", [])
        )

        return cls(
            id=data["id"],
            name=data["name"],
            manufacturer=data.get("manufacturer"),
            product_line=data.get("product_line"),
            color=data.get("color"),
            material_type=material_type,
            category=category,
            properties=properties,
            print_settings=print_settings,
            compatibility=compatibility,
            cost_per_kg=data.get("cost_per_kg"),
            density_g_cm3=data.get("density_g_cm3"),
            description=data.get("description"),
            applications=data.get("applications", []),
            advantages=data.get("advantages", []),
            disadvantages=data.get("disadvantages", []),
            tips=data.get("tips", []),
            quality_rating=data.get("quality_rating"),
            availability=data.get("availability"),
            last_updated=data.get("last_updated"),
            validated=data.get("validated", False),
            validation_notes=data.get("validation_notes", [])
        )