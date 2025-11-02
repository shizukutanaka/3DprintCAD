"""Material preset manager with default material definitions."""
from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime

from .models import (
    MaterialPreset, MaterialProperties, PrintSettings, CompatibilityInfo,
    MaterialType, MaterialCategory, PrinterType
)
from .database import MaterialDatabase, get_material_database
from ..logging import get_logger


class MaterialPresetManager:
    """Manager for material presets with default materials."""

    def __init__(self, database: Optional[MaterialDatabase] = None):
        """Initialize preset manager."""
        self.database = database or get_material_database()
        self.logger = get_logger(__name__)

    def initialize_default_materials(self) -> int:
        """Initialize database with default material presets."""
        defaults = self._get_default_materials()
        added_count = 0

        for material in defaults:
            if self.database.add_material(material, update_if_exists=False):
                added_count += 1

        if added_count > 0:
            self.logger.info(f"Initialized {added_count} default materials")

        return added_count

    def _get_default_materials(self) -> List[MaterialPreset]:
        """Get default material definitions."""
        materials = []

        # PLA Materials
        materials.extend(self._create_pla_materials())

        # ABS Materials
        materials.extend(self._create_abs_materials())

        # PETG Materials
        materials.extend(self._create_petg_materials())

        # Sustainable Materials
        materials.extend(self._create_sustainable_materials())

        # Engineering Materials
        materials.extend(self._create_engineering_materials())

        # Specialty Materials
        materials.extend(self._create_specialty_materials())

        return materials

    def _create_pla_materials(self) -> List[MaterialPreset]:
        """Create PLA material presets."""
        base_properties = MaterialProperties(
            glass_transition_temp=60.0,
            melting_point=180.0,
            print_temperature_min=190,
            print_temperature_max=220,
            bed_temperature=60.0,
            tensile_strength_mpa=50.0,
            flexural_strength_mpa=80.0,
            youngs_modulus_mpa=3500.0,
            density_g_cm3=1.24,
            shrinkage_percent=0.3,
            layer_adhesion="excellent",
            warping_tendency="low",
            support_required=False,
            heated_bed_required=False,
            enclosure_required=False,
            chemical_resistance="poor",
            uv_resistance="poor",
            food_safe=True,
            biodegradable=True,
            recyclable=True
        )

        base_settings = PrintSettings(
            nozzle_temperature=200,
            bed_temperature=60,
            print_speed=60,
            first_layer_speed=30,
            layer_height_recommended=0.2,
            layer_height_min=0.1,
            layer_height_max=0.3,
            flow_rate=100,
            retraction_distance=4.0,
            retraction_speed=40,
            fan_speed=100,
            fan_speed_first_layer=0,
            adhesion_type="none"
        )

        base_compatibility = CompatibilityInfo(
            compatible_printers={PrinterType.FDM},
            compatible_nozzle_materials={"brass", "steel", "hardened_steel"},
            minimum_nozzle_diameter=0.2,
            maximum_nozzle_diameter=1.0,
            requires_hardened_nozzle=False,
            requires_all_metal_hotend=False,
            ventilation_required=False
        )

        return [
            MaterialPreset(
                id="pla_standard",
                name="PLA Standard",
                material_type=MaterialType.THERMOPLASTIC,
                category=MaterialCategory.STANDARD,
                properties=base_properties,
                print_settings=base_settings,
                compatibility=base_compatibility,
                cost_per_kg=25.0,
                density_g_cm3=1.24,
                description="General-purpose PLA filament suitable for most printing applications",
                applications=["Prototyping", "Educational", "Decorative", "Toys"],
                advantages=["Easy to print", "Low odor", "Biodegradable", "Good surface finish"],
                disadvantages=["Low heat resistance", "Brittle", "UV sensitive"],
                tips=["Use cooling fan", "Print slowly for best quality"],
                quality_rating=4.0,
                availability="common",
                validated=True
            ),

            MaterialPreset(
                id="pla_plus",
                name="PLA+",
                material_type=MaterialType.THERMOPLASTIC,
                category=MaterialCategory.STANDARD,
                properties=MaterialProperties(
                    **{**base_properties.__dict__, **{
                        "tensile_strength_mpa": 65.0,
                        "impact_strength_j_m": 4.5,
                        "print_temperature_min": 205,
                        "print_temperature_max": 230
                    }}
                ),
                print_settings=PrintSettings(
                    **{**base_settings.__dict__, **{
                        "nozzle_temperature": 215
                    }}
                ),
                compatibility=base_compatibility,
                cost_per_kg=30.0,
                density_g_cm3=1.24,
                description="Enhanced PLA with improved strength and durability",
                applications=["Functional parts", "Tools", "Mechanical components"],
                advantages=["Stronger than PLA", "Better layer adhesion", "Less brittle"],
                disadvantages=["Slightly harder to print", "Higher temperature required"],
                quality_rating=4.5,
                availability="common",
                validated=True
            )
        ]

    def _create_abs_materials(self) -> List[MaterialPreset]:
        """Create ABS material presets."""
        base_properties = MaterialProperties(
            glass_transition_temp=105.0,
            melting_point=210.0,
            print_temperature_min=220,
            print_temperature_max=270,
            bed_temperature=100.0,
            tensile_strength_mpa=40.0,
            flexural_strength_mpa=60.0,
            impact_strength_j_m=10.0,
            youngs_modulus_mpa=2000.0,
            density_g_cm3=1.04,
            shrinkage_percent=0.8,
            layer_adhesion="good",
            warping_tendency="high",
            support_required=False,
            heated_bed_required=True,
            enclosure_required=True,
            chemical_resistance="good",
            uv_resistance="fair",
            food_safe=False,
            biodegradable=False,
            recyclable=True
        )

        base_settings = PrintSettings(
            nozzle_temperature=250,
            bed_temperature=100,
            print_speed=40,
            first_layer_speed=20,
            layer_height_recommended=0.2,
            layer_height_min=0.1,
            layer_height_max=0.4,
            flow_rate=100,
            retraction_distance=2.0,
            retraction_speed=30,
            fan_speed=0,
            fan_speed_first_layer=0,
            adhesion_type="brim"
        )

        base_compatibility = CompatibilityInfo(
            compatible_printers={PrinterType.FDM},
            compatible_nozzle_materials={"brass", "steel", "hardened_steel"},
            minimum_nozzle_diameter=0.3,
            maximum_nozzle_diameter=1.0,
            requires_hardened_nozzle=False,
            requires_all_metal_hotend=True,
            ventilation_required=True,
            safety_notes=["Use ventilation", "Heated enclosure recommended"]
        )

        return [
            MaterialPreset(
                id="abs_standard",
                name="ABS Standard",
                material_type=MaterialType.THERMOPLASTIC,
                category=MaterialCategory.ENGINEERING,
                properties=base_properties,
                print_settings=base_settings,
                compatibility=base_compatibility,
                cost_per_kg=28.0,
                density_g_cm3=1.04,
                description="Durable thermoplastic for functional parts",
                applications=["Automotive parts", "Electronic housings", "Tools"],
                advantages=["High impact strength", "Heat resistant", "Chemical resistant"],
                disadvantages=["Warping prone", "Requires enclosure", "Toxic fumes"],
                tips=["Use enclosure", "High bed temperature", "Avoid drafts"],
                quality_rating=4.0,
                availability="common",
                validated=True
            )
        ]

    def _create_petg_materials(self) -> List[MaterialPreset]:
        """Create PETG material presets."""
        return [
            MaterialPreset(
                id="petg_standard",
                name="PETG Standard",
                material_type=MaterialType.THERMOPLASTIC,
                category=MaterialCategory.ENGINEERING,
                properties=MaterialProperties(
                    glass_transition_temp=80.0,
                    print_temperature_min=220,
                    print_temperature_max=250,
                    bed_temperature=80.0,
                    tensile_strength_mpa=50.0,
                    flexural_strength_mpa=69.0,
                    impact_strength_j_m=8.0,
                    density_g_cm3=1.27,
                    shrinkage_percent=0.2,
                    layer_adhesion="excellent",
                    warping_tendency="low",
                    chemical_resistance="excellent",
                    food_safe=True,
                    recyclable=True
                ),
                print_settings=PrintSettings(
                    nozzle_temperature=235,
                    bed_temperature=80,
                    print_speed=50,
                    first_layer_speed=25,
                    layer_height_recommended=0.2,
                    retraction_distance=3.0,
                    fan_speed=50
                ),
                compatibility=CompatibilityInfo(
                    compatible_printers={PrinterType.FDM},
                    compatible_nozzle_materials={"brass", "steel", "hardened_steel"}
                ),
                cost_per_kg=35.0,
                description="Chemical resistant thermoplastic with excellent clarity",
                applications=["Food containers", "Chemical storage", "Medical devices"],
                advantages=["Chemical resistant", "Crystal clear", "Food safe"],
                disadvantages=["Stringing prone", "Slower printing"],
                validated=True
            )
        ]

    def _create_resin_materials(self) -> List[MaterialPreset]:
        """Create resin material presets."""
        return [
            MaterialPreset(
                id="resin_standard",
                name="Standard Resin",
                material_type=MaterialType.RESIN,
                category=MaterialCategory.STANDARD,
                properties=MaterialProperties(
                    tensile_strength_mpa=65.0,
                    flexural_strength_mpa=110.0,
                    density_g_cm3=1.15,
                    shrinkage_percent=2.0
                ),
                compatibility=CompatibilityInfo(
                    compatible_printers={PrinterType.SLA, PrinterType.MSLA, PrinterType.DLP},
                    ventilation_required=True,
                    safety_notes=["Wear gloves", "Use ventilation", "UV protection required"]
                ),
                cost_per_kg=80.0,
                description="General-purpose photopolymer resin",
                applications=["Miniatures", "Jewelry", "Dental models"],
                advantages=["High detail", "Smooth finish", "Fast printing"],
                disadvantages=["Toxic when uncured", "Requires post-processing"],
                validated=True
            )
        ]

    def _create_engineering_materials(self) -> List[MaterialPreset]:
        """Create engineering material presets."""
        return [
            MaterialPreset(
                id="nylon_pa12",
                name="Nylon PA12",
                material_type=MaterialType.THERMOPLASTIC,
                category=MaterialCategory.ENGINEERING,
                properties=MaterialProperties(
                    melting_point=180.0,
                    print_temperature_min=260,
                    print_temperature_max=290,
                    bed_temperature=120.0,
                    tensile_strength_mpa=48.0,
                    flexural_strength_mpa=60.0,
                    impact_strength_j_m=35.0,
                    density_g_cm3=1.01,
                    chemical_resistance="excellent"
                ),
                print_settings=PrintSettings(
                    nozzle_temperature=275,
                    bed_temperature=120,
                    print_speed=30,
                    fan_speed=0
                ),
                compatibility=CompatibilityInfo(
                    compatible_printers={PrinterType.FDM},
                    requires_hardened_nozzle=True,
                    requires_all_metal_hotend=True
                ),
                cost_per_kg=120.0,
                description="High-performance engineering thermoplastic",
                applications=["Gears", "Bearings", "Automotive components"],
                category=MaterialCategory.HIGH_PERFORMANCE,
                validated=True
            )
        ]

    def _create_specialty_materials(self) -> List[MaterialPreset]:
        """Create specialty material presets."""
        return [
            MaterialPreset(
                id="pva_support",
                name="PVA Support",
                material_type=MaterialType.SOLUBLE,
                category=MaterialCategory.SPECIALTY,
                properties=MaterialProperties(
                    print_temperature_min=190,
                    print_temperature_max=220,
                    bed_temperature=60.0,
                    density_g_cm3=1.23
                ),
                compatibility=CompatibilityInfo(
                    compatible_printers={PrinterType.FDM},
                    compatible_nozzle_materials={"steel", "hardened_steel"}
                ),
                cost_per_kg=150.0,
                description="Water-soluble support material",
                applications=["Support structures", "Complex geometries"],
                advantages=["Water soluble", "Clean removal"],
                disadvantages=["Expensive", "Hygroscopic"],
                validated=True
            ),

            MaterialPreset(
                id="tpu_flexible",
                name="TPU Flexible",
                material_type=MaterialType.FLEXIBLE,
                category=MaterialCategory.SPECIALTY,
                properties=MaterialProperties(
                    print_temperature_min=210,
                    print_temperature_max=240,
                    hardness_shore="95A",
                    elongation_at_break_percent=580.0,
                    density_g_cm3=1.20
                ),
                print_settings=PrintSettings(
                    nozzle_temperature=225,
                    print_speed=20,
                    retraction_distance=1.0,
                    retraction_speed=20
                ),
                compatibility=CompatibilityInfo(
                    compatible_printers={PrinterType.FDM},
                    minimum_nozzle_diameter=0.4
                ),
                cost_per_kg=85.0,
                description="Flexible thermoplastic polyurethane",
                applications=["Phone cases", "Gaskets", "Wearables"],
                advantages=["Flexible", "Impact resistant", "Chemical resistant"],
                disadvantages=["Slow printing", "Difficult to print"],
                validated=True
            )
        ]

    def get_recommended_materials_for_application(self, application: str) -> List[MaterialPreset]:
        """Get materials recommended for a specific application."""
        # This could be enhanced with ML or more sophisticated matching
        application_lower = application.lower()

        materials = self.database.list_all_materials()
        recommended = []

        for material in materials:
            for app in material.applications:
                if application_lower in app.lower():
                    recommended.append(material)
                    break

        # Sort by quality rating (highest first)
        recommended.sort(key=lambda m: m.quality_rating or 0, reverse=True)
        return recommended

    def get_materials_by_printer_type(self, printer_type: PrinterType) -> List[MaterialPreset]:
        """Get all materials compatible with a printer type."""
        return self.database.search_materials(compatible_with=printer_type)

    def backup_materials(self, backup_path: Optional[str] = None) -> bool:
        """Create backup of all materials."""
        from pathlib import Path
        from ..config import get_config

        if backup_path is None:
            config = get_config()
            backup_path = config.config_directory / f"materials_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            backup_path = Path(backup_path)

        return self.database.export_to_json(backup_path)

    def _create_sustainable_materials(self) -> List[MaterialPreset]:
        """Create sustainable and eco-friendly material presets."""
        materials = []

        # Recycled PLA
        recycled_pla = MaterialPreset(
            name="Recycled PLA",
            manufacturer="Generic",
            material_type=MaterialType.RECYCLED,
            category=MaterialCategory.SUSTAINABLE,
            description="PLA made from recycled materials",
            properties=MaterialProperties(
                density_g_cm3=1.24,
                melting_point=150.0,
                print_temperature_min=190,
                print_temperature_max=220,
                bed_temperature=60,
                tensile_strength_mpa=50.0,
                elongation_at_break_percent=5.0,
                biodegradable=True,
                recyclable=True,
                recycled_content_percent=100.0,
                carbon_footprint_kg_co2_per_kg=2.5,
                toxicity_rating="low",
                renewable_source=False,
                food_safe=True
            ),
            print_settings=PrintSettings(
                nozzle_temperature=200,
                bed_temperature=60,
                print_speed=50,
                first_layer_speed=25,
                layer_height=0.2,
                infill_density=20
            ),
            compatibility=CompatibilityInfo(
                printer_types=[PrinterType.FDM],
                nozzle_sizes_mm=[0.4, 0.6, 0.8],
                max_print_speed=60,
                requires_heated_bed=False,
                requires_enclosure=False
            ),
            version="1.0.0",
            last_updated=datetime.now()
        )
        materials.append(recycled_pla)

        # Biodegradable PET
        bio_pet = MaterialPreset(
            name="Bio-PET",
            manufacturer="Generic",
            material_type=MaterialType.BIODEGRADABLE,
            category=MaterialCategory.SUSTAINABLE,
            description="Biodegradable PET for eco-friendly printing",
            properties=MaterialProperties(
                density_g_cm3=1.38,
                melting_point=250.0,
                print_temperature_min=220,
                print_temperature_max=250,
                bed_temperature=80,
                tensile_strength_mpa=55.0,
                elongation_at_break_percent=300.0,
                biodegradable=True,
                recyclable=False,
                recycled_content_percent=0.0,
                carbon_footprint_kg_co2_per_kg=3.2,
                water_usage_liters_per_kg=50.0,
                toxicity_rating="low",
                renewable_source=True,
                food_safe=True,
                compostable=True
            ),
            print_settings=PrintSettings(
                nozzle_temperature=235,
                bed_temperature=80,
                print_speed=45,
                first_layer_speed=20,
                layer_height=0.15,
                infill_density=25
            ),
            compatibility=CompatibilityInfo(
                printer_types=[PrinterType.FDM],
                nozzle_sizes_mm=[0.4, 0.6],
                max_print_speed=50,
                requires_heated_bed=True,
                requires_enclosure=False
            ),
            version="1.0.0",
            last_updated=datetime.now()
        )
        materials.append(bio_pet)

        # Hemp-based PLA
        hemp_pla = MaterialPreset(
            name="Hemp PLA",
            manufacturer="Generic",
            material_type=MaterialType.BIODEGRADABLE,
            category=MaterialCategory.SUSTAINABLE,
            description="PLA composite with hemp fibers for sustainability",
            properties=MaterialProperties(
                density_g_cm3=1.3,
                melting_point=155.0,
                print_temperature_min=195,
                print_temperature_max=225,
                bed_temperature=65,
                tensile_strength_mpa=45.0,
                elongation_at_break_percent=4.0,
                biodegradable=True,
                recyclable=True,
                recycled_content_percent=20.0,
                carbon_footprint_kg_co2_per_kg=1.8,
                toxicity_rating="low",
                renewable_source=True,
                food_safe=False
            ),
            print_settings=PrintSettings(
                nozzle_temperature=210,
                bed_temperature=65,
                print_speed=40,
                first_layer_speed=20,
                layer_height=0.2,
                infill_density=30
            ),
            compatibility=CompatibilityInfo(
                printer_types=[PrinterType.FDM],
                nozzle_sizes_mm=[0.4, 0.6, 0.8],
                max_print_speed=45,
                requires_heated_bed=False,
                requires_enclosure=False
            ),
            version="1.0.0",
            last_updated=datetime.now()
        )
        materials.append(hemp_pla)

        return materials