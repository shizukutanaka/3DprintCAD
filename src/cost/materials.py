"""Material database and properties for cost estimation."""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class MaterialType(Enum):
    """Material type categories."""
    THERMOPLASTIC = "thermoplastic"
    RESIN = "resin"
    METAL = "metal"
    CERAMIC = "ceramic"
    COMPOSITE = "composite"


@dataclass
class Material:
    """Material properties and pricing information."""
    name: str
    type: MaterialType
    density: float  # g/cm³
    price_per_kg: float  # USD per kg
    description: str = ""

    # Printing properties
    nozzle_temp: Optional[float] = None  # °C
    bed_temp: Optional[float] = None  # °C
    print_speed: Optional[float] = None  # mm/s

    # Physical properties
    tensile_strength: Optional[float] = None  # MPa
    flexural_strength: Optional[float] = None  # MPa
    impact_strength: Optional[float] = None  # kJ/m²
    glass_transition_temp: Optional[float] = None  # °C

    # Additional properties
    color_options: List[str] = None
    supplier: str = ""
    part_number: str = ""
    shrinkage: float = 0.0  # %

    # Cost factors
    waste_factor: float = 1.1  # 10% waste
    difficulty_multiplier: float = 1.0  # Printing difficulty

    def __post_init__(self):
        """Initialize default values."""
        if self.color_options is None:
            self.color_options = ["Natural"]


class MaterialDatabase:
    """Database of materials with properties and pricing."""

    def __init__(self, db_file: Optional[Path] = None):
        """Initialize material database.

        Args:
            db_file: Path to material database file
        """
        self.materials: Dict[str, Material] = {}
        self.db_file = db_file

        # Load default materials
        self._load_default_materials()

        # Load from file if provided
        if db_file and db_file.exists():
            self.load_from_file(db_file)

    def _load_default_materials(self):
        """Load default material database."""
        default_materials = [
            # PLA variants
            Material(
                name="PLA",
                type=MaterialType.THERMOPLASTIC,
                density=1.25,
                price_per_kg=25.0,
                description="Polylactic Acid - Easy to print, biodegradable",
                nozzle_temp=210,
                bed_temp=60,
                print_speed=60,
                tensile_strength=50,
                flexural_strength=80,
                glass_transition_temp=60,
                color_options=["White", "Black", "Red", "Blue", "Green", "Yellow", "Orange", "Purple"],
                shrinkage=0.3
            ),

            Material(
                name="PLA+",
                type=MaterialType.THERMOPLASTIC,
                density=1.25,
                price_per_kg=30.0,
                description="Enhanced PLA with improved strength and durability",
                nozzle_temp=215,
                bed_temp=65,
                print_speed=55,
                tensile_strength=65,
                flexural_strength=90,
                glass_transition_temp=65,
                color_options=["White", "Black", "Red", "Blue", "Green", "Yellow"],
                shrinkage=0.2
            ),

            # ABS variants
            Material(
                name="ABS",
                type=MaterialType.THERMOPLASTIC,
                density=1.05,
                price_per_kg=28.0,
                description="Acrylonitrile Butadiene Styrene - Strong, heat resistant",
                nozzle_temp=245,
                bed_temp=100,
                print_speed=50,
                tensile_strength=40,
                flexural_strength=65,
                glass_transition_temp=105,
                color_options=["White", "Black", "Red", "Blue", "Green"],
                shrinkage=0.8,
                difficulty_multiplier=1.3
            ),

            # PETG
            Material(
                name="PETG",
                type=MaterialType.THERMOPLASTIC,
                density=1.27,
                price_per_kg=35.0,
                description="Polyethylene Terephthalate Glycol - Chemical resistant, clear",
                nozzle_temp=235,
                bed_temp=80,
                print_speed=45,
                tensile_strength=50,
                flexural_strength=75,
                glass_transition_temp=80,
                color_options=["Clear", "White", "Black", "Red", "Blue"],
                shrinkage=0.2
            ),

            # TPU (Flexible)
            Material(
                name="TPU",
                type=MaterialType.THERMOPLASTIC,
                density=1.20,
                price_per_kg=55.0,
                description="Thermoplastic Polyurethane - Flexible, rubber-like",
                nozzle_temp=220,
                bed_temp=50,
                print_speed=30,
                tensile_strength=35,
                flexural_strength=None,
                glass_transition_temp=-30,
                color_options=["Natural", "Black", "Red", "Blue"],
                shrinkage=0.5,
                difficulty_multiplier=2.0,
                waste_factor=1.2
            ),

            # Nylon
            Material(
                name="Nylon",
                type=MaterialType.THERMOPLASTIC,
                density=1.15,
                price_per_kg=65.0,
                description="Polyamide - Very strong, wear resistant",
                nozzle_temp=260,
                bed_temp=90,
                print_speed=40,
                tensile_strength=85,
                flexural_strength=120,
                glass_transition_temp=50,
                color_options=["Natural", "Black", "White"],
                shrinkage=1.5,
                difficulty_multiplier=2.5,
                waste_factor=1.3
            ),

            # Wood-filled PLA
            Material(
                name="Wood PLA",
                type=MaterialType.COMPOSITE,
                density=1.28,
                price_per_kg=45.0,
                description="PLA with wood fibers - Can be sanded and stained",
                nozzle_temp=205,
                bed_temp=60,
                print_speed=45,
                tensile_strength=35,
                flexural_strength=55,
                glass_transition_temp=60,
                color_options=["Wood", "Bamboo", "Cherry", "Walnut"],
                shrinkage=0.4,
                difficulty_multiplier=1.2
            ),

            # Carbon Fiber PLA
            Material(
                name="Carbon Fiber PLA",
                type=MaterialType.COMPOSITE,
                density=1.3,
                price_per_kg=75.0,
                description="PLA reinforced with carbon fiber - Very strong",
                nozzle_temp=210,
                bed_temp=65,
                print_speed=50,
                tensile_strength=90,
                flexural_strength=140,
                glass_transition_temp=65,
                color_options=["Black", "Dark Gray"],
                shrinkage=0.1,
                difficulty_multiplier=1.5
            ),

            # Metal-filled PLA
            Material(
                name="Metal PLA",
                type=MaterialType.COMPOSITE,
                density=3.9,
                price_per_kg=85.0,
                description="PLA with metal powder - Can be polished",
                nozzle_temp=215,
                bed_temp=65,
                print_speed=40,
                tensile_strength=45,
                flexural_strength=70,
                glass_transition_temp=65,
                color_options=["Steel", "Copper", "Bronze", "Aluminum"],
                shrinkage=0.3,
                difficulty_multiplier=1.8
            ),

            # HIPS
            Material(
                name="HIPS",
                type=MaterialType.THERMOPLASTIC,
                density=1.04,
                price_per_kg=32.0,
                description="High Impact Polystyrene - Good support material",
                nozzle_temp=230,
                bed_temp=100,
                print_speed=50,
                tensile_strength=32,
                flexural_strength=50,
                glass_transition_temp=100,
                color_options=["White", "Black", "Natural"],
                shrinkage=0.6,
                difficulty_multiplier=1.4
            ),

            # PC (Polycarbonate)
            Material(
                name="PC",
                type=MaterialType.THERMOPLASTIC,
                density=1.20,
                price_per_kg=80.0,
                description="Polycarbonate - Very strong, high temperature resistance",
                nozzle_temp=280,
                bed_temp=110,
                print_speed=35,
                tensile_strength=65,
                flexural_strength=95,
                glass_transition_temp=145,
                color_options=["Clear", "Black", "White"],
                shrinkage=0.7,
                difficulty_multiplier=3.0,
                waste_factor=1.4
            ),

            # Standard Resin
            Material(
                name="Standard Resin",
                type=MaterialType.RESIN,
                density=1.2,
                price_per_kg=45.0,
                description="Standard photopolymer resin",
                nozzle_temp=None,
                bed_temp=None,
                print_speed=None,
                tensile_strength=50,
                flexural_strength=80,
                color_options=["Clear", "Gray", "Black", "White", "Red", "Blue"],
                waste_factor=1.15
            ),

            # Tough Resin
            Material(
                name="Tough Resin",
                type=MaterialType.RESIN,
                density=1.15,
                price_per_kg=65.0,
                description="High-strength photopolymer resin",
                nozzle_temp=None,
                bed_temp=None,
                print_speed=None,
                tensile_strength=70,
                flexural_strength=110,
                impact_strength=30,
                color_options=["Clear", "Black", "White"],
                waste_factor=1.2
            )
        ]

        for material in default_materials:
            self.materials[material.name] = material

    def add_material(self, material: Material) -> None:
        """Add material to database.

        Args:
            material: Material to add
        """
        self.materials[material.name] = material

    def get_material(self, name: str) -> Optional[Material]:
        """Get material by name.

        Args:
            name: Material name

        Returns:
            Material object or None if not found
        """
        return self.materials.get(name)

    def get_materials_by_type(self, material_type: MaterialType) -> List[Material]:
        """Get all materials of a specific type.

        Args:
            material_type: Type of material

        Returns:
            List of materials
        """
        return [
            material for material in self.materials.values()
            if material.type == material_type
        ]

    def list_materials(self) -> List[str]:
        """Get list of all material names.

        Returns:
            List of material names
        """
        return list(self.materials.keys())

    def search_materials(
        self,
        query: str = "",
        max_price: Optional[float] = None,
        material_type: Optional[MaterialType] = None,
        min_strength: Optional[float] = None
    ) -> List[Material]:
        """Search materials by criteria.

        Args:
            query: Search query for name/description
            max_price: Maximum price per kg
            material_type: Material type filter
            min_strength: Minimum tensile strength

        Returns:
            List of matching materials
        """
        results = []

        for material in self.materials.values():
            # Text search
            if query and query.lower() not in material.name.lower() and query.lower() not in material.description.lower():
                continue

            # Price filter
            if max_price and material.price_per_kg > max_price:
                continue

            # Type filter
            if material_type and material.type != material_type:
                continue

            # Strength filter
            if min_strength and (not material.tensile_strength or material.tensile_strength < min_strength):
                continue

            results.append(material)

        return results

    def get_cheapest_materials(self, count: int = 5) -> List[Material]:
        """Get cheapest materials.

        Args:
            count: Number of materials to return

        Returns:
            List of cheapest materials
        """
        sorted_materials = sorted(
            self.materials.values(),
            key=lambda m: m.price_per_kg
        )
        return sorted_materials[:count]

    def get_strongest_materials(self, count: int = 5) -> List[Material]:
        """Get strongest materials by tensile strength.

        Args:
            count: Number of materials to return

        Returns:
            List of strongest materials
        """
        materials_with_strength = [
            m for m in self.materials.values()
            if m.tensile_strength is not None
        ]

        sorted_materials = sorted(
            materials_with_strength,
            key=lambda m: m.tensile_strength,
            reverse=True
        )
        return sorted_materials[:count]

    def get_default_material(self) -> Material:
        """Get default material (PLA).

        Returns:
            Default material
        """
        return self.materials.get("PLA", list(self.materials.values())[0])

    def update_prices(self, price_updates: Dict[str, float]) -> None:
        """Update material prices.

        Args:
            price_updates: Dictionary of material name to new price
        """
        for name, price in price_updates.items():
            if name in self.materials:
                self.materials[name].price_per_kg = price

    def save_to_file(self, file_path: Path) -> None:
        """Save material database to file.

        Args:
            file_path: File path to save to
        """
        data = {
            'materials': {
                name: self._material_to_dict(material)
                for name, material in self.materials.items()
            }
        }

        with file_path.open('w') as f:
            json.dump(data, f, indent=2, default=str)

    def load_from_file(self, file_path: Path) -> None:
        """Load material database from file.

        Args:
            file_path: File path to load from
        """
        with file_path.open('r') as f:
            data = json.load(f)

        for name, material_data in data.get('materials', {}).items():
            material = self._dict_to_material(material_data)
            self.materials[name] = material

    def _material_to_dict(self, material: Material) -> Dict[str, Any]:
        """Convert material to dictionary.

        Args:
            material: Material object

        Returns:
            Material dictionary
        """
        return {
            'name': material.name,
            'type': material.type.value,
            'density': material.density,
            'price_per_kg': material.price_per_kg,
            'description': material.description,
            'nozzle_temp': material.nozzle_temp,
            'bed_temp': material.bed_temp,
            'print_speed': material.print_speed,
            'tensile_strength': material.tensile_strength,
            'flexural_strength': material.flexural_strength,
            'impact_strength': material.impact_strength,
            'glass_transition_temp': material.glass_transition_temp,
            'color_options': material.color_options,
            'supplier': material.supplier,
            'part_number': material.part_number,
            'shrinkage': material.shrinkage,
            'waste_factor': material.waste_factor,
            'difficulty_multiplier': material.difficulty_multiplier
        }

    def _dict_to_material(self, data: Dict[str, Any]) -> Material:
        """Convert dictionary to material.

        Args:
            data: Material dictionary

        Returns:
            Material object
        """
        return Material(
            name=data['name'],
            type=MaterialType(data['type']),
            density=data['density'],
            price_per_kg=data['price_per_kg'],
            description=data.get('description', ''),
            nozzle_temp=data.get('nozzle_temp'),
            bed_temp=data.get('bed_temp'),
            print_speed=data.get('print_speed'),
            tensile_strength=data.get('tensile_strength'),
            flexural_strength=data.get('flexural_strength'),
            impact_strength=data.get('impact_strength'),
            glass_transition_temp=data.get('glass_transition_temp'),
            color_options=data.get('color_options', ['Natural']),
            supplier=data.get('supplier', ''),
            part_number=data.get('part_number', ''),
            shrinkage=data.get('shrinkage', 0.0),
            waste_factor=data.get('waste_factor', 1.1),
            difficulty_multiplier=data.get('difficulty_multiplier', 1.0)
        )

    def get_material_comparison(self, material_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Compare multiple materials.

        Args:
            material_names: List of material names to compare

        Returns:
            Comparison dictionary
        """
        comparison = {}

        for name in material_names:
            material = self.get_material(name)
            if material:
                comparison[name] = {
                    'price_per_kg': material.price_per_kg,
                    'density': material.density,
                    'tensile_strength': material.tensile_strength,
                    'print_temp': material.nozzle_temp,
                    'difficulty': material.difficulty_multiplier,
                    'colors': len(material.color_options)
                }

        return comparison